from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime, timezone


def get_timestamp() -> str:
    """Get current UTC timestamp in simple format: YYYY-MM-DD HH:MM:SS"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def configure_logger(run_name: str) -> None:
    """Configure logging to file in logs/ directory."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{run_name}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def calculate_stop_loss_price(entry_price: float, side: str, sl_percent: float) -> float:
    """
    Calculate stop-loss price based on entry price and percentage.

    Args:
        entry_price: Entry price of the position
        side: Position side - "BUY" (long) or "SELL" (short)
        sl_percent: Stop-loss percentage (e.g., 2.0 for 2%)

    Returns:
        Stop-loss trigger price
    """
    if side == "BUY":
        return entry_price * (1 - sl_percent / 100)
    else:
        return entry_price * (1 + sl_percent / 100)


def calculate_position_size(exchange, symbol: str, position_size: str | float | int) -> tuple[float, float]:
    """
    Calculate position size in base currency and quote currency.

    Supports two modes:
    1. Percentage string: "10%" → 10% of available capital
    2. Float/int: 100 → Fixed cost of 100 USD

    Args:
        exchange: Exchange client
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        position_size: Position size specification (percentage string or fixed cost in USD)

    Returns:
        Tuple of (base_qty, quote_amount) - e.g., (0.001 BTC, 100 USD)
    """
    capital = exchange.get_account_balance("USDT")
    current_price = exchange.get_current_price(symbol)

    if isinstance(position_size, str):
        if position_size.endswith("%"):
            try:
                percentage = float(position_size.rstrip("%"))
                if not 0 < percentage <= 100:
                    raise ValueError(f"Percentage must be between 0 and 100, got {percentage}%")
                fraction = percentage / 100
                quote_amount = capital * fraction
            except ValueError as e:
                raise ValueError(f"Invalid percentage format '{position_size}': {e}")
        else:
            raise ValueError(f"String position_size must end with '%', got '{position_size}'")

    elif isinstance(position_size, (int, float)):
        if position_size <= 0:
            raise ValueError(f"Position size must be positive, got {position_size}")
        if position_size > capital:
            raise ValueError(f"Fixed amount {position_size} USD exceeds available capital {capital:.2f} USD")
        quote_amount = position_size
    else:
        raise TypeError(f"position_size must be str, int, or float, got {type(position_size)}")

    base_qty = quote_amount / current_price

    return base_qty, quote_amount


def _is_coinbase_exchange(exchange) -> bool:
    """Check if exchange is Coinbase client."""
    return exchange.__class__.__name__ == "CoinbaseAdvanced"


def _is_forward_tester(exchange) -> bool:
    """Check if exchange is forward tester."""
    return exchange.__class__.__name__ == "ForwardTester"


def open_position(
        exchange,
        symbol: str,
        direction: str,
        position_size: str | float | int,
        stop_loss_percent: float | None = None,
        **kwargs
) -> dict[str, str]:
    """
    Open a market position (buy or sell).

    This helper function handles:
    - Position sizing (percentage or fixed amount)
    - Stop-loss calculation (percentage-based)
    - Calling the exchange's place_order() method with computed values
    - Attaching position-level stop-loss (if supported by exchange)

    Works with BitunixFutures, CoinbaseAdvanced, and ForwardTester exchange clients.

    Args:
        exchange: Exchange client
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        direction: "buy" or "sell"
        position_size: Position size ("10%" or fixed amount like 100)
        stop_loss_percent: Optional stop-loss percentage (e.g., 2.0 for 2%)
        **kwargs: Additional parameters passed to exchange.place_order()

    Returns:
        Order response from exchange
    """
    side = direction.upper()

    base_qty, quote_amount = calculate_position_size(exchange, symbol, position_size)
    logging.info(f"Position size: {base_qty:.6f} base ({quote_amount:.2f} USD)")

    # Detect exchange type and call with appropriate parameters
    if _is_coinbase_exchange(exchange):
        # Coinbase: use quote_size for buys, qty for sells
        if side == "BUY":
            order_response = exchange.place_order(
                symbol=symbol,
                side=side.lower(),
                quote_size=quote_amount,
                **kwargs
            )
        else:
            order_response = exchange.place_order(
                symbol=symbol,
                side=side.lower(),
                qty=base_qty,
                **kwargs
            )
    elif _is_forward_tester(exchange):
        # Forward tester: simplified interface
        order_response = exchange.place_order(
            symbol=symbol,
            qty=base_qty,
            side=side,
            trade_side="OPEN",
            order_type="MARKET",
            **kwargs
        )
    else:
        # Bitunix: full futures interface
        order_response = exchange.place_order(
            symbol=symbol,
            qty=base_qty,
            side=side,
            trade_side="OPEN",
            order_type="MARKET",
            **kwargs
        )

    # Attach stop-loss if supported
    if stop_loss_percent is not None and hasattr(exchange, 'place_position_tpsl'):
        try:
            position = exchange.get_pending_positions(symbol=symbol)
            if position:
                entry_price = float(position.avgOpenPrice)
                sl_price = calculate_stop_loss_price(entry_price, side, stop_loss_percent)
                logging.info(f"Stop-loss: {sl_price:.2f} USD ({stop_loss_percent}% from entry {entry_price:.2f})")

                exchange.place_position_tpsl(
                    symbol=symbol,
                    position_id=position.positionId,
                    sl_price=sl_price
                )
                logging.info("Position stop-loss attached successfully")
            else:
                logging.warning("Could not attach stop-loss: position not found")
        except Exception as e:
            logging.warning(f"Failed to attach position stop-loss: {e}")
    elif stop_loss_percent is not None:
        logging.info("Stop-loss not supported for this exchange mode")

    return order_response
