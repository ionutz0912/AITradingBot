"""
Tests for lib/forward_tester.py - Paper trading simulation module
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from lib.forward_tester import (
    ForwardTester,
    MockPosition,
    _fetch_market_price,
    _calculate_pnl,
    _calculate_trade_fees,
)


class TestForwardTester:
    """Test ForwardTester class."""

    def test_initialization(self, tmp_path, monkeypatch):
        """Test ForwardTester initialization."""
        monkeypatch.chdir(tmp_path)

        config = {
            "initial_capital": 10000,
            "fees": 0.001,
            "run_name": "test_run"
        }

        tester = ForwardTester(config)

        assert tester.current_capital == 10000
        assert tester.fees == 0.001

    @patch("lib.forward_tester._fetch_market_price")
    def test_place_buy_order(self, mock_price, tmp_path, monkeypatch):
        """Test placing a buy order."""
        monkeypatch.chdir(tmp_path)
        mock_price.return_value = 50000.0

        config = {
            "initial_capital": 10000,
            "fees": 0.001,
            "run_name": "test_run"
        }

        tester = ForwardTester(config)
        result = tester.place_order(
            symbol="BTCUSDT",
            qty=0.1,
            side="BUY",
            trade_side="OPEN",
            order_type="MARKET"
        )

        assert "orderId" in result
        assert tester._current_position is not None


class TestCalculations:
    """Test calculation functions."""

    def test_calculate_pnl_long(self):
        """Test P&L calculation for long position."""
        pnl = _calculate_pnl("BUY", 50000, 52000, 0.1)
        assert pnl == 200.0

    def test_calculate_pnl_short(self):
        """Test P&L calculation for short position."""
        pnl = _calculate_pnl("SELL", 50000, 48000, 0.1)
        assert pnl == 200.0

    def test_calculate_trade_fees(self):
        """Test fee calculation."""
        fees = _calculate_trade_fees(0.1, 50000, 0.001)
        assert fees == 5.0
