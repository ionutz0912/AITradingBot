"""
Tests for lib/performance_tracker.py - Performance metrics tracking
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone

from lib.performance_tracker import (
    PerformanceTracker,
    Trade,
    PerformanceMetrics,
    get_tracker,
)


class TestPerformanceTracker:
    """Test PerformanceTracker class."""

    def test_initialization(self, temp_performance_dir):
        """Test tracker initialization."""
        tracker = PerformanceTracker("test_strategy")

        assert tracker.strategy_name == "test_strategy"
        assert len(tracker.trades) == 0

    def test_record_trade(self, temp_performance_dir):
        """Test recording a trade."""
        tracker = PerformanceTracker("test_strategy")

        trade = Trade(
            trade_id="test_1",
            symbol="BTCUSDT",
            side="buy",
            entry_price=50000,
            exit_price=52000,
            quantity=0.1,
            entry_time=datetime.now(timezone.utc).isoformat(),
            exit_time=datetime.now(timezone.utc).isoformat(),
            pnl=200,
            pnl_percent=4.0
        )

        tracker.record_trade(trade)

        assert len(tracker.trades) == 1

    def test_create_trade(self, temp_performance_dir):
        """Test creating a trade from parameters."""
        tracker = PerformanceTracker("test_strategy")

        trade = tracker.create_trade(
            symbol="BTCUSDT",
            side="buy",
            entry_price=50000,
            exit_price=52000,
            quantity=0.1,
            fees=5.0
        )

        assert trade.pnl > 0
        assert len(tracker.trades) == 1

    def test_get_metrics(self, temp_performance_dir):
        """Test calculating performance metrics."""
        tracker = PerformanceTracker("test_strategy")

        # Add winning and losing trades
        tracker.create_trade("BTC", "buy", 50000, 52000, 0.1)
        tracker.create_trade("BTC", "buy", 51000, 50000, 0.1)

        metrics = tracker.get_metrics()

        assert metrics.total_trades == 2
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
        assert metrics.win_rate == 50.0
