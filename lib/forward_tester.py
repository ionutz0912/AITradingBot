import logging
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


class MockPosition:
    """Minimal position object for forward testing compatibility."""
    def __init__(self, side: str, symbol: str, qty: float, entry_price: float):
        self.side = side
        self.symbol = symbol
        self.qty = qty
        self.avgOpenPrice = entry_price
        self.positionId = "SIMULATED"


class ForwardTester:
    """
    Forward testing client that simulates trading without real execution.
    Maintains the same public API as BitunixFutures for compatibility.
    """

    def __init__(self, config: dict[str, Any]):
        self.initial_capital = config["initial_capital"]
        self.fees = config["fees"]
        self.run_name = config.get("run_name", "default_run")
        self.current_capital = self.initial_capital
        self.locked_capital = 0.0
        self._current_position: dict[str, Any] | None = None

        self._csv_dir = Path("forward_testing_results")
        self._csv_dir.mkdir(exist_ok=True)
        self._csv_file = self._csv_dir / f"{self.run_name}.csv"

        self._initialize_csv()
        self._load_state_from_csv()

    def _initialize_csv(self) -> None:
        """Create CSV file with headers if it doesn't exist."""
        if not self._csv_file.exists():
            with open(self._csv_file, "w", newline="", encoding="utf-8") as f:
                import csv
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "interpretation", "action", "symbol",
                    "qty", "price", "fees", "pnl", "capital"
                ])

    def _load_state_from_csv(self) -> None:
        """Load current state (position and capital) from CSV history."""
        if not self._csv_file.exists() or self._csv_file.stat().st_size == 0:
            return

        try:
            import csv
            rows = self._read_csv_rows()
            if not rows:
                return

            self.current_capital = float(rows[-1]["capital"])
            self._current_position = _find_last_position(rows)

            if self._current_position:
                self.locked_capital = self._current_position["qty"] * self._current_position["entry_price"]
            else:
                self.locked_capital = 0.0

            logging.info(f"Loaded state: capital={self.current_capital}, locked={self.locked_capital}, position={self._current_position}")

        except Exception as e:
            logging.error(f"Failed to load state from CSV: {e}")

    def _read_csv_rows(self) -> list[dict[str, str]]:
        """Read all rows from CSV file."""
        import csv
        with open(self._csv_file, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _append_to_csv(self, row: dict[str, Any]) -> None:
        """Append a row to the CSV file."""
        try:
            import csv
            with open(self._csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "interpretation", "action", "symbol",
                    "qty", "price", "fees", "pnl", "capital"
                ])
                writer.writerow(row)
        except Exception as e:
            logging.error(f"Failed to append to CSV: {e}")

    def get_current_price(self, symbol: str) -> float:
        """Get current market price for a symbol from Bitunix public API."""
        return _fetch_market_price(symbol)

    def get_account_balance(self, margin_coin: str) -> float:
        """Get total account balance (free + locked capital)."""
        return self.current_capital

    def get_pending_positions(self, symbol: str, position_id: str | None = None) -> MockPosition | None:
        """Get current simulated position."""
        if not self._current_position:
            return None

        return MockPosition(
            side=self._current_position["side"],
            symbol=self._current_position["symbol"],
            qty=self._current_position["qty"],
            entry_price=self._current_position["entry_price"]
        )

    def set_margin_mode(self, symbol: str, margin_mode: str = "ISOLATION", margin_coin: str = "USDT") -> dict[str, Any]:
        """Simulate setting margin mode (no-op for forward testing)."""
        return {}

    def set_leverage(self, symbol: str, leverage: int, margin_coin: str = "USDT") -> dict[str, Any]:
        """Simulate setting leverage (no-op for forward testing)."""
        return {}

    def place_order(
            self,
            symbol: str,
            qty: float,
            side: str,
            trade_side: str,
            order_type: str,
            interpretation: str = "",
            stop_loss_percent: float | None = None,  # Accepted but ignored in forward testing
            **kwargs
    ) -> dict[str, str]:
        """Simulate placing an order. Stop-loss not tracked in forward testing."""
        price = _fetch_market_price(symbol)
        action = self._determine_action(side, trade_side)
        trade_fees = _calculate_trade_fees(qty, price, self.fees)

        pnl = self._execute_trade(action, symbol, qty, price, trade_fees)
        self._log_trade(interpretation, action, symbol, qty, price, trade_fees, pnl)

        return {"orderId": f"SIM_{datetime.now(timezone.utc).timestamp()}"}

    def _determine_action(self, side: str, trade_side: str) -> str:
        """Determine action type from side and trade_side."""
        if trade_side == "OPEN":
            return "OPEN_LONG" if side == "BUY" else "OPEN_SHORT"
        else:
            if self._current_position:
                return f"CLOSE_{self._current_position['side']}"
            return "CLOSE"

    def _execute_trade(self, action: str, symbol: str, qty: float, price: float, trade_fees: float) -> float:
        """Execute trade, update position and capital. Returns PnL."""
        pnl = 0

        if action in ["CLOSE_LONG", "CLOSE_SHORT"] and self._current_position:
            pnl = _calculate_pnl(
                self._current_position["side"],
                self._current_position["entry_price"],
                price,
                qty
            )
            entry_position_value = self._current_position["qty"] * self._current_position["entry_price"]
            self.locked_capital -= entry_position_value
            self.current_capital += pnl - trade_fees
            self._current_position = None

        elif action in ["OPEN_LONG", "OPEN_SHORT"]:
            position_value = qty * price
            self.locked_capital += position_value
            self.current_capital -= trade_fees
            self._current_position = {
                "side": "BUY" if action == "OPEN_LONG" else "SELL",
                "symbol": symbol,
                "qty": qty,
                "entry_price": price,
            }

        return pnl

    def _log_trade(self, interpretation: str, action: str, symbol: str,
                   qty: float, price: float, fees: float, pnl: float) -> None:
        """Log trade to CSV."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self._append_to_csv({
            "timestamp": timestamp,
            "interpretation": interpretation,
            "action": action,
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "fees": round(fees, 2),
            "pnl": round(pnl, 2),
            "capital": round(self.current_capital, 2)
        })

    def flash_close_position(self, position_id: str, interpretation: str = "") -> dict[str, str]:
        """Simulate flash closing a position."""
        if not self._current_position:
            logging.warning("No position to close")
            return {"orderId": "NONE"}

        symbol = self._current_position["symbol"]
        qty = self._current_position["qty"]
        entry_price = self._current_position["entry_price"]
        side = self._current_position["side"]

        price = _fetch_market_price(symbol)
        pnl = _calculate_pnl(side, entry_price, price, qty)
        trade_fees = _calculate_trade_fees(qty, price, self.fees)
        position_value = qty * price

        self.locked_capital -= position_value
        self.current_capital += pnl - trade_fees

        action = f"CLOSE_{side}"
        self._log_trade(interpretation, action, symbol, qty, price, trade_fees, pnl)
        self._current_position = None

        return {"orderId": f"SIM_CLOSE_{datetime.now(timezone.utc).timestamp()}"}


def _fetch_market_price(symbol: str) -> float:
    """Fetch current market price from Bitunix public API."""
    url = "https://fapi.bitunix.com/api/v1/futures/market/tickers"
    response = requests.get(url, params={"symbols": symbol}, timeout=10)
    response.raise_for_status()

    data = response.json()
    if data.get("code") != 0:
        raise Exception(f"API error: {data.get('msg')}")

    tickers = data.get("data", [])
    for ticker in tickers:
        if ticker["symbol"] == symbol:
            return float(ticker["lastPrice"])

    raise Exception(f"Symbol {symbol} not found in API response")


def _calculate_pnl(side: str, entry_price: float, exit_price: float, qty: float) -> float:
    """Calculate PnL for a position."""
    if side == "BUY":
        return (exit_price - entry_price) * qty
    else:
        return (entry_price - exit_price) * qty


def _calculate_trade_fees(qty: float, price: float, fee_rate: float) -> float:
    """Calculate trading fees."""
    return qty * price * fee_rate


def _reconstruct_position_from_row(row: dict[str, str]) -> dict[str, Any]:
    """Reconstruct position dict from CSV row."""
    return {
        "side": "BUY" if row["action"] == "OPEN_LONG" else "SELL",
        "symbol": row["symbol"],
        "qty": float(row["qty"]),
        "entry_price": float(row["price"]),
    }


def _find_last_position(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    """Find the last open position from CSV rows."""
    for row in reversed(rows):
        if row["action"] in ["OPEN_LONG", "OPEN_SHORT"]:
            return _reconstruct_position_from_row(row)
        elif row["action"] in ["CLOSE_LONG", "CLOSE_SHORT"]:
            return None
    return None
