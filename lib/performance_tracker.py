"""
Performance Tracking Module for AI Trading Bot

Tracks trading performance metrics including:
- Trade history with entry/exit prices
- P&L calculations (realized and unrealized)
- Win rate and average win/loss
- Maximum drawdown
- Total trades and streaks
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path

PERFORMANCE_DIR = "performance_data"


@dataclass
class Trade:
    """Represents a completed trade."""
    trade_id: str
    symbol: str
    side: str  # "buy" or "sell"
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: str
    exit_time: str
    pnl: float
    pnl_percent: float
    fees: float = 0.0
    notes: str = ""


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_percent: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float
    max_drawdown: float
    current_streak: int  # Positive for wins, negative for losses
    best_streak: int
    worst_streak: int
    avg_trade_duration_hours: float


class PerformanceTracker:
    """
    Tracks and persists trading performance data.

    Usage:
        tracker = PerformanceTracker("my_strategy")
        tracker.record_trade(trade)
        metrics = tracker.get_metrics()
        tracker.print_summary()
    """

    def __init__(self, strategy_name: str = "default"):
        self.strategy_name = strategy_name
        self.trades: List[Trade] = []
        self.data_file = Path(PERFORMANCE_DIR) / f"{strategy_name}_trades.json"
        self._ensure_dir()
        self._load_trades()

    def _ensure_dir(self) -> None:
        """Create performance data directory if it doesn't exist."""
        Path(PERFORMANCE_DIR).mkdir(exist_ok=True)

    def _load_trades(self) -> None:
        """Load existing trades from file."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.trades = [Trade(**t) for t in data.get("trades", [])]
                logging.info(f"Loaded {len(self.trades)} historical trades for {self.strategy_name}")
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logging.warning(f"Failed to load trades file: {e}")
                self.trades = []

    def _save_trades(self) -> None:
        """Persist trades to file."""
        data = {
            "strategy_name": self.strategy_name,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "trades": [asdict(t) for t in self.trades]
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)

    def record_trade(self, trade: Trade) -> None:
        """Record a completed trade."""
        self.trades.append(trade)
        self._save_trades()
        logging.info(f"Recorded trade: {trade.symbol} {trade.side} PnL: {trade.pnl:.2f} ({trade.pnl_percent:.2f}%)")

    def create_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        entry_time: Optional[str] = None,
        exit_time: Optional[str] = None,
        fees: float = 0.0,
        notes: str = ""
    ) -> Trade:
        """Create and record a trade from parameters."""
        now = datetime.now(timezone.utc).isoformat()

        # Calculate PnL
        if side.lower() == "buy":
            pnl = (exit_price - entry_price) * quantity - fees
            pnl_percent = ((exit_price / entry_price) - 1) * 100
        else:  # sell/short
            pnl = (entry_price - exit_price) * quantity - fees
            pnl_percent = ((entry_price / exit_price) - 1) * 100

        trade = Trade(
            trade_id=f"{symbol}_{int(datetime.now(timezone.utc).timestamp())}",
            symbol=symbol,
            side=side.lower(),
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            entry_time=entry_time or now,
            exit_time=exit_time or now,
            pnl=pnl,
            pnl_percent=pnl_percent,
            fees=fees,
            notes=notes
        )

        self.record_trade(trade)
        return trade

    def get_metrics(self) -> PerformanceMetrics:
        """Calculate and return performance metrics."""
        if not self.trades:
            return PerformanceMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_pnl_percent=0.0,
                average_win=0.0,
                average_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                profit_factor=0.0,
                max_drawdown=0.0,
                current_streak=0,
                best_streak=0,
                worst_streak=0,
                avg_trade_duration_hours=0.0
            )

        # Basic counts
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]

        total_trades = len(self.trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)

        # Win rate
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0

        # P&L calculations
        total_pnl = sum(t.pnl for t in self.trades)
        total_pnl_percent = sum(t.pnl_percent for t in self.trades)

        # Average win/loss
        avg_win = sum(t.pnl for t in winning_trades) / win_count if win_count > 0 else 0.0
        avg_loss = sum(t.pnl for t in losing_trades) / loss_count if loss_count > 0 else 0.0

        # Largest win/loss
        largest_win = max((t.pnl for t in self.trades), default=0.0)
        largest_loss = min((t.pnl for t in self.trades), default=0.0)

        # Profit factor (gross profit / gross loss)
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0

        # Maximum drawdown calculation
        max_drawdown = self._calculate_max_drawdown()

        # Streak calculations
        current_streak, best_streak, worst_streak = self._calculate_streaks()

        # Average trade duration
        avg_duration = self._calculate_avg_duration()

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            average_win=avg_win,
            average_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            current_streak=current_streak,
            best_streak=best_streak,
            worst_streak=worst_streak,
            avg_trade_duration_hours=avg_duration
        )

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from peak equity."""
        if not self.trades:
            return 0.0

        equity_curve = [0.0]
        for trade in self.trades:
            equity_curve.append(equity_curve[-1] + trade.pnl)

        peak = equity_curve[0]
        max_dd = 0.0

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_streaks(self) -> tuple:
        """Calculate current, best, and worst winning/losing streaks."""
        if not self.trades:
            return 0, 0, 0

        current = 0
        best_win = 0
        worst_loss = 0
        streak = 0

        for trade in self.trades:
            if trade.pnl > 0:
                if streak > 0:
                    streak += 1
                else:
                    streak = 1
                if streak > best_win:
                    best_win = streak
            elif trade.pnl < 0:
                if streak < 0:
                    streak -= 1
                else:
                    streak = -1
                if streak < worst_loss:
                    worst_loss = streak
            # Break-even trades don't affect streak

        current = streak
        return current, best_win, worst_loss

    def _calculate_avg_duration(self) -> float:
        """Calculate average trade duration in hours."""
        durations = []
        for trade in self.trades:
            try:
                entry = datetime.fromisoformat(trade.entry_time.replace('Z', '+00:00'))
                exit = datetime.fromisoformat(trade.exit_time.replace('Z', '+00:00'))
                duration = (exit - entry).total_seconds() / 3600
                durations.append(duration)
            except (ValueError, AttributeError):
                continue

        return sum(durations) / len(durations) if durations else 0.0

    def get_trades_by_symbol(self, symbol: str) -> List[Trade]:
        """Get all trades for a specific symbol."""
        return [t for t in self.trades if t.symbol == symbol]

    def get_recent_trades(self, count: int = 10) -> List[Trade]:
        """Get the most recent trades."""
        return self.trades[-count:] if self.trades else []

    def print_summary(self) -> str:
        """Print a formatted performance summary."""
        metrics = self.get_metrics()

        summary = f"""
========================================
  Performance Summary: {self.strategy_name}
========================================
Total Trades:      {metrics.total_trades}
Win Rate:          {metrics.win_rate:.1f}% ({metrics.winning_trades}W / {metrics.losing_trades}L)
----------------------------------------
Total P&L:         ${metrics.total_pnl:.2f} ({metrics.total_pnl_percent:.2f}%)
Average Win:       ${metrics.average_win:.2f}
Average Loss:      ${metrics.average_loss:.2f}
Largest Win:       ${metrics.largest_win:.2f}
Largest Loss:      ${metrics.largest_loss:.2f}
----------------------------------------
Profit Factor:     {metrics.profit_factor:.2f}
Max Drawdown:      ${metrics.max_drawdown:.2f}
----------------------------------------
Current Streak:    {metrics.current_streak} ({'wins' if metrics.current_streak > 0 else 'losses' if metrics.current_streak < 0 else 'N/A'})
Best Win Streak:   {metrics.best_streak}
Worst Loss Streak: {abs(metrics.worst_streak)}
Avg Duration:      {metrics.avg_trade_duration_hours:.1f} hours
========================================
"""
        print(summary)
        logging.info(f"Performance: {metrics.total_trades} trades, {metrics.win_rate:.1f}% win rate, ${metrics.total_pnl:.2f} P&L")
        return summary

    def export_to_csv(self, filepath: Optional[str] = None) -> str:
        """Export trades to CSV format."""
        import csv

        filepath = filepath or str(Path(PERFORMANCE_DIR) / f"{self.strategy_name}_trades.csv")

        with open(filepath, 'w', newline='') as f:
            if self.trades:
                writer = csv.DictWriter(f, fieldnames=asdict(self.trades[0]).keys())
                writer.writeheader()
                for trade in self.trades:
                    writer.writerow(asdict(trade))

        logging.info(f"Exported {len(self.trades)} trades to {filepath}")
        return filepath

    def clear_history(self) -> None:
        """Clear all trade history (use with caution)."""
        self.trades = []
        self._save_trades()
        logging.warning(f"Cleared all trade history for {self.strategy_name}")


# Convenience function for quick access
def get_tracker(strategy_name: str = "default") -> PerformanceTracker:
    """Get or create a performance tracker for a strategy."""
    return PerformanceTracker(strategy_name)
