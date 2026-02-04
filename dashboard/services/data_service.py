"""
Data Service for Dashboard

Aggregates data from various lib/ modules to provide
unified data access for the dashboard API endpoints.

Supports both live trading (Coinbase) and paper trading (ForwardTester).
"""

import os
import csv
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import asdict

# Import lib modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.config import load_config, get_enabled_symbols, TradingConfig
from lib.performance_tracker import PerformanceTracker, PerformanceMetrics
from lib.market_data import get_market_data, get_fear_greed_index, MarketData, MarketDataError


class DashboardDataService:
    """Service for aggregating dashboard data from various sources."""

    def __init__(self, config_file: str = "config.json"):
        """
        Initialize the data service.

        Args:
            config_file: Name of the config file to load
        """
        self.config_file = config_file
        self._config: Optional[TradingConfig] = None
        self._tracker: Optional[PerformanceTracker] = None
        self._coinbase_client = None

    @property
    def config(self) -> TradingConfig:
        """Lazy load configuration."""
        if self._config is None:
            try:
                self._config = load_config(self.config_file)
            except Exception as e:
                logging.warning(f"Failed to load config: {e}")
                from lib.config import get_default_config
                self._config = get_default_config()
        return self._config

    @property
    def tracker(self) -> PerformanceTracker:
        """Lazy load performance tracker."""
        if self._tracker is None:
            self._tracker = PerformanceTracker(self.config.run_name)
        return self._tracker

    @property
    def coinbase(self):
        """Lazy load Coinbase client."""
        if self._coinbase_client is None:
            try:
                from lib.coinbase_client import CoinbaseAdvanced
                api_key = os.environ.get("COINBASE_API_KEY", "")
                api_secret = os.environ.get("COINBASE_API_SECRET", "")
                if api_key and api_secret:
                    self._coinbase_client = CoinbaseAdvanced(api_key, api_secret)
            except Exception as e:
                logging.warning(f"Failed to initialize Coinbase client: {e}")
        return self._coinbase_client

    def get_status(self) -> Dict[str, Any]:
        """
        Get bot status information.

        Returns:
            Dict with run_name, mode, enabled symbols, etc.
        """
        config = self.config
        enabled_symbols = get_enabled_symbols(config)

        return {
            "run_name": config.run_name,
            "mode": "forward_testing" if config.forward_testing else "live",
            "ai_provider": config.ai_provider,
            "exchange_provider": config.exchange_provider,
            "enabled_symbols": [s.symbol for s in enabled_symbols],
            "max_positions": config.max_positions,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.

        Returns:
            Dict with win rate, P&L, drawdown, etc.
        """
        # Use paper trading metrics if in forward testing mode
        if self.config.forward_testing:
            return self._get_paper_metrics()

        metrics = self.tracker.get_metrics()

        return {
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades,
            "win_rate": round(metrics.win_rate, 2),
            "total_pnl": round(metrics.total_pnl, 2),
            "total_pnl_percent": round(metrics.total_pnl_percent, 2),
            "average_win": round(metrics.average_win, 2),
            "average_loss": round(metrics.average_loss, 2),
            "largest_win": round(metrics.largest_win, 2),
            "largest_loss": round(metrics.largest_loss, 2),
            "profit_factor": round(metrics.profit_factor, 2) if metrics.profit_factor != float('inf') else None,
            "max_drawdown": round(metrics.max_drawdown, 2),
            "current_streak": metrics.current_streak,
            "best_streak": metrics.best_streak,
            "worst_streak": metrics.worst_streak,
            "avg_trade_duration_hours": round(metrics.avg_trade_duration_hours, 2)
        }

    def _get_paper_metrics(self) -> Dict[str, Any]:
        """Calculate metrics from ForwardTester CSV file."""
        csv_file = Path("forward_testing_results") / f"{self.config.run_name}.csv"

        # Default metrics
        metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "total_pnl_percent": 0,
            "average_win": 0,
            "average_loss": 0,
            "largest_win": 0,
            "largest_loss": 0,
            "profit_factor": None,
            "max_drawdown": 0,
            "current_streak": 0,
            "best_streak": 0,
            "worst_streak": 0,
            "avg_trade_duration_hours": 0,
            "is_paper": True
        }

        if not csv_file.exists():
            return metrics

        try:
            with open(csv_file, 'r') as f:
                rows = list(csv.DictReader(f))

            if not rows:
                return metrics

            # Calculate metrics from closed trades
            pnls = []
            wins = []
            losses = []

            for row in rows:
                if row["action"] in ["CLOSE_LONG", "CLOSE_SHORT"]:
                    pnl = float(row.get("pnl", 0))
                    pnls.append(pnl)
                    if pnl > 0:
                        wins.append(pnl)
                    elif pnl < 0:
                        losses.append(pnl)

            total_trades = len(pnls)
            if total_trades == 0:
                return metrics

            metrics["total_trades"] = total_trades
            metrics["winning_trades"] = len(wins)
            metrics["losing_trades"] = len(losses)
            metrics["win_rate"] = round((len(wins) / total_trades) * 100, 2) if total_trades > 0 else 0
            metrics["total_pnl"] = round(sum(pnls), 2)

            initial = self.config.forward_testing_capital
            metrics["total_pnl_percent"] = round((metrics["total_pnl"] / initial) * 100, 2) if initial > 0 else 0

            if wins:
                metrics["average_win"] = round(sum(wins) / len(wins), 2)
                metrics["largest_win"] = round(max(wins), 2)

            if losses:
                metrics["average_loss"] = round(sum(losses) / len(losses), 2)
                metrics["largest_loss"] = round(min(losses), 2)

            # Profit factor
            gross_profit = sum(wins) if wins else 0
            gross_loss = abs(sum(losses)) if losses else 0
            if gross_loss > 0:
                metrics["profit_factor"] = round(gross_profit / gross_loss, 2)

            return metrics

        except Exception as e:
            logging.warning(f"Failed to calculate paper metrics: {e}")
            return metrics

    def get_recent_trades(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent trades.

        Args:
            count: Number of trades to return

        Returns:
            List of trade dictionaries
        """
        # Use paper trades if in forward testing mode
        if self.config.forward_testing:
            return self._get_paper_trades(count)

        trades = self.tracker.get_recent_trades(count)
        return [
            {
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": round(t.entry_price, 2),
                "exit_price": round(t.exit_price, 2),
                "quantity": t.quantity,
                "pnl": round(t.pnl, 2),
                "pnl_percent": round(t.pnl_percent, 2),
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "notes": t.notes
            }
            for t in reversed(trades)  # Most recent first
        ]

    def _get_paper_trades(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get trades from ForwardTester CSV file."""
        csv_file = Path("forward_testing_results") / f"{self.config.run_name}.csv"
        if not csv_file.exists():
            return []

        try:
            with open(csv_file, 'r') as f:
                rows = list(csv.DictReader(f))

            # Convert CSV rows to trade format
            trades = []
            for row in reversed(rows[-count*2:]):  # Get more rows to find closed trades
                action = row.get("action", "")

                # Only show closed trades (they have P&L)
                if action in ["CLOSE_LONG", "CLOSE_SHORT"]:
                    pnl = float(row.get("pnl", 0))
                    entry_price = float(row.get("price", 0))  # This is exit price for close
                    qty = float(row.get("qty", 0))

                    trades.append({
                        "trade_id": f"PAPER_{row['timestamp']}",
                        "symbol": row.get("symbol", ""),
                        "side": "buy" if action == "CLOSE_LONG" else "sell",
                        "entry_price": 0,  # Not tracked in simple CSV
                        "exit_price": round(entry_price, 2),
                        "quantity": qty,
                        "pnl": round(pnl, 2),
                        "pnl_percent": 0,  # Not tracked
                        "entry_time": "",
                        "exit_time": row.get("timestamp", ""),
                        "notes": f"Paper trade - {row.get('interpretation', '')}",
                        "is_paper": True
                    })

                    if len(trades) >= count:
                        break

            return trades

        except Exception as e:
            logging.warning(f"Failed to read paper trades: {e}")
            return []

    def get_market_data(self) -> Dict[str, Any]:
        """
        Get market data for enabled symbols.

        Returns:
            Dict with symbol -> market data
        """
        enabled_symbols = get_enabled_symbols(self.config)
        result = {}

        for symbol_config in enabled_symbols:
            try:
                data = get_market_data(symbol_config.symbol)
                result[data.symbol] = {
                    "price": round(data.price, 2),
                    "price_change_24h": round(data.price_change_24h, 2),
                    "price_change_24h_percent": round(data.price_change_24h_percent, 2),
                    "high_24h": round(data.high_24h, 2),
                    "low_24h": round(data.low_24h, 2),
                    "volume_24h": round(data.volume_24h, 0),
                    "timestamp": data.timestamp
                }
            except MarketDataError as e:
                logging.warning(f"Failed to get market data for {symbol_config.symbol}: {e}")
                result[symbol_config.symbol] = {"error": str(e)}

        return result

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current open positions.

        Returns:
            List of position dictionaries
        """
        # Use paper trading data if in forward testing mode
        if self.config.forward_testing:
            return self._get_paper_positions()

        if not self.coinbase:
            return []

        positions = []
        enabled_symbols = get_enabled_symbols(self.config)

        for symbol_config in enabled_symbols:
            try:
                position = self.coinbase.get_pending_positions(symbol_config.symbol)
                if position:
                    # Get current price for unrealized P&L
                    try:
                        current_price = self.coinbase.get_current_price(symbol_config.symbol)
                    except Exception:
                        current_price = 0

                    positions.append({
                        "position_id": position.positionId,
                        "symbol": position.symbol,
                        "quantity": position.qty,
                        "side": position.side,
                        "avg_open_price": position.avgOpenPrice,
                        "current_price": round(current_price, 2),
                        "unrealized_pnl": round((current_price - position.avgOpenPrice) * position.qty, 2) if position.avgOpenPrice > 0 else None
                    })
            except Exception as e:
                logging.warning(f"Failed to get position for {symbol_config.symbol}: {e}")

        return positions

    def _get_paper_positions(self) -> List[Dict[str, Any]]:
        """Get positions from ForwardTester CSV file."""
        csv_file = Path("forward_testing_results") / f"{self.config.run_name}.csv"
        if not csv_file.exists():
            return []

        try:
            with open(csv_file, 'r') as f:
                rows = list(csv.DictReader(f))

            if not rows:
                return []

            # Find last open position (not closed)
            position = None
            for row in reversed(rows):
                if row["action"] in ["OPEN_LONG", "OPEN_SHORT"]:
                    position = {
                        "side": "buy" if row["action"] == "OPEN_LONG" else "sell",
                        "symbol": row["symbol"],
                        "qty": float(row["qty"]),
                        "entry_price": float(row["price"]),
                    }
                    break
                elif row["action"] in ["CLOSE_LONG", "CLOSE_SHORT"]:
                    break  # Position was closed

            if not position:
                return []

            # Get current market price for unrealized P&L
            try:
                market = get_market_data(position["symbol"])
                current_price = market.price
            except Exception:
                current_price = position["entry_price"]

            # Calculate unrealized P&L
            if position["side"] == "buy":
                unrealized_pnl = (current_price - position["entry_price"]) * position["qty"]
            else:
                unrealized_pnl = (position["entry_price"] - current_price) * position["qty"]

            return [{
                "position_id": "PAPER",
                "symbol": position["symbol"],
                "quantity": position["qty"],
                "side": position["side"],
                "avg_open_price": round(position["entry_price"], 2),
                "current_price": round(current_price, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "is_paper": True
            }]

        except Exception as e:
            logging.warning(f"Failed to read paper positions: {e}")
            return []

    def get_account_balance(self) -> Dict[str, Any]:
        """
        Get account balance.

        Returns:
            Dict with USD balance and holdings
        """
        # Use paper trading balance if in forward testing mode
        if self.config.forward_testing:
            return self._get_paper_balance()

        if not self.coinbase:
            return {"error": "Coinbase client not available"}

        try:
            usd_balance = self.coinbase.get_account_balance("USD")
            return {
                "usd_available": round(usd_balance, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logging.warning(f"Failed to get account balance: {e}")
            return {"error": str(e)}

    def _get_paper_balance(self) -> Dict[str, Any]:
        """Get balance from ForwardTester CSV file."""
        csv_file = Path("forward_testing_results") / f"{self.config.run_name}.csv"

        # Default to initial capital from config
        balance = self.config.forward_testing_capital

        if csv_file.exists():
            try:
                with open(csv_file, 'r') as f:
                    rows = list(csv.DictReader(f))
                if rows:
                    balance = float(rows[-1]["capital"])
            except Exception as e:
                logging.warning(f"Failed to read paper balance: {e}")

        return {
            "usd_available": round(balance, 2),
            "initial_capital": self.config.forward_testing_capital,
            "is_paper": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def close_position(self, symbol: str, position_id: str = None) -> Dict[str, Any]:
        """
        Close an open position.

        Args:
            symbol: Trading symbol
            position_id: Position ID (optional)

        Returns:
            Dict with success status and details
        """
        if self.config.forward_testing:
            return self._close_paper_position(symbol)

        if not self.coinbase:
            return {"success": False, "error": "Coinbase client not available"}

        try:
            position = self.coinbase.get_pending_positions(symbol)
            if not position:
                return {"success": False, "error": "No open position found"}

            result = self.coinbase.flash_close_position(position.positionId)
            return {
                "success": True,
                "symbol": symbol,
                "message": "Position closed successfully",
                "result": result
            }
        except Exception as e:
            logging.error(f"Failed to close position: {e}")
            return {"success": False, "error": str(e)}

    def _close_paper_position(self, symbol: str) -> Dict[str, Any]:
        """Close a paper trading position."""
        csv_file = Path("forward_testing_results") / f"{self.config.run_name}.csv"

        if not csv_file.exists():
            return {"success": False, "error": "No paper trading data found"}

        try:
            # Read current state
            with open(csv_file, 'r') as f:
                rows = list(csv.DictReader(f))

            if not rows:
                return {"success": False, "error": "No trades found"}

            # Find last open position
            position = None
            for row in reversed(rows):
                if row["action"] in ["OPEN_LONG", "OPEN_SHORT"]:
                    position = {
                        "side": "BUY" if row["action"] == "OPEN_LONG" else "SELL",
                        "symbol": row["symbol"],
                        "qty": float(row["qty"]),
                        "entry_price": float(row["price"]),
                    }
                    break
                elif row["action"] in ["CLOSE_LONG", "CLOSE_SHORT"]:
                    return {"success": False, "error": "No open position to close"}

            if not position:
                return {"success": False, "error": "No open position found"}

            # Get current market price
            try:
                market = get_market_data(position["symbol"])
                exit_price = market.price
            except Exception:
                return {"success": False, "error": "Could not fetch market price"}

            # Calculate P&L
            if position["side"] == "BUY":
                pnl = (exit_price - position["entry_price"]) * position["qty"]
            else:
                pnl = (position["entry_price"] - exit_price) * position["qty"]

            # Get current capital
            current_capital = float(rows[-1]["capital"])
            new_capital = current_capital + pnl

            # Calculate fees
            fee_rate = self.config.forward_testing_fees
            fees = position["qty"] * exit_price * fee_rate
            new_capital -= fees

            # Append close trade to CSV
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            action = f"CLOSE_{position['side']}"

            with open(csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    "Manual Close",
                    action,
                    position["symbol"],
                    position["qty"],
                    exit_price,
                    round(fees, 2),
                    round(pnl, 2),
                    round(new_capital, 2)
                ])

            return {
                "success": True,
                "symbol": position["symbol"],
                "side": position["side"].lower(),
                "entry_price": round(position["entry_price"], 2),
                "exit_price": round(exit_price, 2),
                "pnl": round(pnl, 2),
                "fees": round(fees, 2),
                "new_balance": round(new_capital, 2),
                "message": f"Paper position closed with P&L: ${pnl:.2f}"
            }

        except Exception as e:
            logging.error(f"Failed to close paper position: {e}")
            return {"success": False, "error": str(e)}

    def get_ai_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent AI interpretations from ai_responses directory.

        Args:
            count: Number of interpretations to return

        Returns:
            List of AI interpretation dictionaries
        """
        ai_dir = Path("ai_responses")
        if not ai_dir.exists():
            return []

        interpretations = []

        # Load all JSON files
        for json_file in ai_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # Extract symbol from filename
                symbol = json_file.stem.split("_")[-1] if "_" in json_file.stem else "UNKNOWN"

                for timestamp, entry in data.items():
                    if isinstance(entry, dict) and "interpretation" in entry:
                        interpretations.append({
                            "symbol": symbol,
                            "timestamp": timestamp,
                            "interpretation": entry.get("interpretation", "Unknown"),
                            "reasons": entry.get("reasons", ""),
                            "provider": entry.get("provider", "Unknown")
                        })
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to read AI response file {json_file}: {e}")

        # Sort by timestamp descending and limit
        interpretations.sort(key=lambda x: x["timestamp"], reverse=True)
        return interpretations[:count]

    def get_fear_greed(self) -> Dict[str, Any]:
        """
        Get Fear & Greed Index.

        Returns:
            Dict with index value and classification
        """
        result = get_fear_greed_index()
        if result:
            return {
                "value": result["value"],
                "classification": result["classification"],
                "timestamp": result.get("timestamp")
            }
        return {"error": "Failed to fetch Fear & Greed Index"}


    def get_simulations_summary(self) -> Dict[str, Any]:
        """
        Get aggregated performance data from all simulations.

        Returns:
            Dict with aggregate metrics and per-simulation breakdown
        """
        try:
            from lib.database import list_simulations, get_simulation_stats, get_simulation_trades
            from lib.simulation_manager import get_simulation_manager

            manager = get_simulation_manager()
            simulations = manager.list_simulations()

            # Initialize aggregate metrics
            aggregate = {
                "total_simulations": len(simulations),
                "running": 0,
                "paused": 0,
                "stopped": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "total_fees": 0,
                "avg_win": 0,
                "avg_loss": 0,
            }

            # Per-simulation data
            simulation_data = []
            all_wins = []
            all_losses = []

            for sim in simulations:
                # Count by status
                if sim["status"] == "running":
                    aggregate["running"] += 1
                elif sim["status"] == "paused":
                    aggregate["paused"] += 1
                elif sim["status"] == "stopped":
                    aggregate["stopped"] += 1

                # Get stats for this simulation
                stats = get_simulation_stats(sim["id"])

                # Add to aggregates
                aggregate["total_trades"] += stats.get("total_trades", 0)
                aggregate["winning_trades"] += stats.get("winning_trades", 0)
                aggregate["losing_trades"] += stats.get("losing_trades", 0)
                aggregate["total_pnl"] += stats.get("total_pnl", 0)
                aggregate["total_fees"] += stats.get("total_fees", 0)

                if stats.get("avg_win"):
                    all_wins.append(stats["avg_win"])
                if stats.get("avg_loss"):
                    all_losses.append(stats["avg_loss"])

                # Get recent trades for this simulation
                recent_trades = get_simulation_trades(sim["id"], limit=5)

                simulation_data.append({
                    "id": sim["id"],
                    "name": sim["name"],
                    "status": sim["status"],
                    "symbol": sim["config"].get("symbol", ""),
                    "stats": stats,
                    "recent_trades": recent_trades
                })

            # Calculate aggregate win rate
            if aggregate["total_trades"] > 0:
                aggregate["win_rate"] = round(
                    (aggregate["winning_trades"] / aggregate["total_trades"]) * 100, 2
                )

            # Calculate aggregate averages
            if all_wins:
                aggregate["avg_win"] = round(sum(all_wins) / len(all_wins), 2)
            if all_losses:
                aggregate["avg_loss"] = round(sum(all_losses) / len(all_losses), 2)

            # Round totals
            aggregate["total_pnl"] = round(aggregate["total_pnl"], 2)
            aggregate["total_fees"] = round(aggregate["total_fees"], 2)

            # Calculate profit factor
            gross_profit = sum(w for w in all_wins if w > 0) if all_wins else 0
            gross_loss = abs(sum(l for l in all_losses if l < 0)) if all_losses else 0
            aggregate["profit_factor"] = round(gross_profit / gross_loss, 2) if gross_loss > 0 else None

            return {
                "aggregate": aggregate,
                "simulations": simulation_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logging.warning(f"Failed to get simulations summary: {e}")
            return {
                "aggregate": {
                    "total_simulations": 0,
                    "running": 0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "total_fees": 0,
                },
                "simulations": [],
                "error": str(e)
            }


# Singleton instance for the dashboard
_data_service: Optional[DashboardDataService] = None


def get_data_service() -> DashboardDataService:
    """Get or create the singleton data service instance."""
    global _data_service
    if _data_service is None:
        _data_service = DashboardDataService()
    return _data_service
