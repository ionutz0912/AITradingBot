"""
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
