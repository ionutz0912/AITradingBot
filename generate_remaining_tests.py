#!/usr/bin/env python3
"""
Script to generate remaining test files for AI Trading Bot.
Run this script to create comprehensive test coverage for all modules.
"""

from pathlib import Path

TEST_TEMPLATES = {
    "test_market_data.py": '''"""
Tests for lib/market_data.py - Market data fetching module
"""

import pytest
from unittest.mock import patch, Mock
import requests

from lib.market_data import (
    MarketData,
    normalize_symbol,
    get_coingecko_data,
    get_coinbase_price,
    get_binance_price,
    get_market_data,
    get_multiple_market_data,
    format_market_context,
    get_fear_greed_index,
    get_enhanced_market_context,
    MarketDataError,
)


class TestMarketData:
    """Test MarketData dataclass."""

    def test_market_data_creation(self):
        """Test creating MarketData object."""
        data = MarketData(
            symbol="BTC",
            price=50000.0,
            price_change_24h=1500.0,
            price_change_24h_percent=3.1,
            high_24h=51000.0,
            low_24h=48500.0,
            volume_24h=25000000000.0
        )

        assert data.symbol == "BTC"
        assert data.price == 50000.0
        assert data.timestamp is not None


class TestSymbolNormalization:
    """Test symbol normalization."""

    @pytest.mark.parametrize("input_symbol,expected", [
        ("BTCUSDT", "BTC"),
        ("BTC-USD", "BTC"),
        ("ETHUSDC", "ETH"),
        ("BTC", "BTC"),
    ])
    def test_normalize_symbol(self, input_symbol, expected):
        """Test symbol normalization for various formats."""
        result = normalize_symbol(input_symbol)
        assert result == expected


class TestCoinGeckoData:
    """Test CoinGecko data fetching."""

    @patch("requests.get")
    def test_get_coingecko_data_success(self, mock_get, mock_coingecko_response):
        """Test successful CoinGecko data fetch."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_coingecko_response

        data = get_coingecko_data("BTC")

        assert data is not None
        assert data.symbol == "BTC"
        assert data.price == 50000.0

    @patch("requests.get")
    def test_get_coingecko_data_error(self, mock_get):
        """Test CoinGecko error handling."""
        mock_get.side_effect = requests.RequestException()

        data = get_coingecko_data("BTC")

        assert data is None


class TestCoinbasePrice:
    """Test Coinbase price fetching."""

    @patch("requests.get")
    def test_get_coinbase_price_success(self, mock_get, mock_coinbase_price_response):
        """Test successful Coinbase price fetch."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_coinbase_price_response

        data = get_coinbase_price("BTC")

        assert data is not None
        assert data.symbol == "BTC"


class TestGetMarketData:
    """Test main market data fetching function."""

    @patch("lib.market_data.get_coinbase_price")
    def test_get_market_data_auto_mode(self, mock_coinbase):
        """Test auto fallback mode."""
        mock_coinbase.return_value = MarketData(
            symbol="BTC",
            price=50000.0,
            price_change_24h=1000.0,
            price_change_24h_percent=2.0,
            high_24h=51000.0,
            low_24h=49000.0,
            volume_24h=1000000000.0
        )

        data = get_market_data("BTCUSDT", source="auto")

        assert data.symbol == "BTC"

    @patch("lib.market_data.get_coingecko_data")
    @patch("lib.market_data.get_coinbase_price")
    @patch("lib.market_data.get_binance_price")
    def test_get_market_data_all_fail(self, mock_binance, mock_coinbase, mock_gecko):
        """Test error when all sources fail."""
        mock_gecko.return_value = None
        mock_coinbase.return_value = None
        mock_binance.return_value = None

        with pytest.raises(MarketDataError):
            get_market_data("BTC", source="auto")
''',

    "test_forward_tester.py": '''"""
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
''',

    "test_performance_tracker.py": '''"""
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
''',

    "test_telegram_notifications.py": '''"""
Tests for lib/telegram_notifications.py - Telegram notification service
"""

import pytest
from unittest.mock import patch, Mock

from lib.telegram_notifications import TelegramNotifier


class TestTelegramNotifier:
    """Test TelegramNotifier class."""

    def test_initialization(self):
        """Test Telegram notifier initialization."""
        notifier = TelegramNotifier("test_token", "123456789")

        assert notifier.bot_token == "test_token"
        assert notifier.chat_id == "123456789"

    def test_initialization_invalid_token(self):
        """Test initialization with invalid token."""
        with pytest.raises(ValueError):
            TelegramNotifier("your_telegram_bot_token_here", "123")

    @patch("requests.post")
    def test_send_notification(self, mock_post, mock_telegram_response):
        """Test sending a notification."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_telegram_response

        notifier = TelegramNotifier("test_token", "123456789")
        result = notifier.send_notification(
            symbol="BTCUSDT",
            interpretation="Bullish",
            reasoning="Test reasoning"
        )

        assert result is True

    @patch("requests.post")
    def test_send_trade_opened(self, mock_post, mock_telegram_response):
        """Test sending trade opened notification."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_telegram_response

        notifier = TelegramNotifier("test_token", "123456789")
        result = notifier.send_trade_opened(
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
            price=50000,
            is_paper=True
        )

        assert result is True

    @patch("requests.get")
    def test_test_connection(self, mock_get):
        """Test connection testing."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "ok": True,
            "result": {"username": "TestBot"}
        }

        notifier = TelegramNotifier("test_token", "123456789")
        result = notifier.test_connection()

        assert result is True
''',

    "test_coinbase_client.py": '''"""
Tests for lib/coinbase_client.py - Coinbase API client
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from lib.coinbase_client import (
    CoinbaseAdvanced,
    CoinbasePosition,
    CoinbaseError,
    to_coinbase_symbol,
    from_coinbase_symbol,
)


class TestSymbolMapping:
    """Test symbol mapping functions."""

    def test_to_coinbase_symbol(self):
        """Test converting to Coinbase format."""
        assert to_coinbase_symbol("BTCUSDT") == "BTC-USD"
        assert to_coinbase_symbol("ETHUSDT") == "ETH-USD"

    def test_from_coinbase_symbol(self):
        """Test converting from Coinbase format."""
        assert from_coinbase_symbol("BTC-USD") == "BTCUSDT"


class TestCoinbaseAdvanced:
    """Test CoinbaseAdvanced client."""

    def test_initialization(self, mock_coinbase_client):
        """Test client initialization."""
        client = CoinbaseAdvanced("test_key", "test_secret")

        assert client is not None

    def test_initialization_no_credentials(self):
        """Test initialization without credentials."""
        with pytest.raises(CoinbaseError):
            CoinbaseAdvanced("", "")

    def test_get_account_balance(self, mock_coinbase_client):
        """Test getting account balance."""
        client = CoinbaseAdvanced("test_key", "test_secret")
        balance = client.get_account_balance("USD")

        assert balance >= 0

    def test_get_current_price(self, mock_coinbase_client):
        """Test getting current price."""
        client = CoinbaseAdvanced("test_key", "test_secret")
        price = client.get_current_price("BTCUSDT")

        assert price > 0

    def test_place_buy_order(self, mock_coinbase_client):
        """Test placing a buy order."""
        client = CoinbaseAdvanced("test_key", "test_secret")
        result = client.place_order(
            symbol="BTCUSDT",
            side="buy",
            quote_size=100.0
        )

        assert "order_id" in result or result is not None
''',
}


def create_test_file(filename: str, content: str):
    """Create a test file with the given content."""
    filepath = Path("tests/lib") / filename
    with open(filepath, "w") as f:
        f.write(content)
    print(f"Created: {filepath}")


def main():
    """Generate all remaining test files."""
    print("Generating remaining test files...")

    for filename, content in TEST_TEMPLATES.items():
        create_test_file(filename, content)

    print(f"\nGenerated {len(TEST_TEMPLATES)} test files!")
    print("\nTo run tests:")
    print("  pip install -r requirements-test.txt")
    print("  pytest tests/")


if __name__ == "__main__":
    main()
