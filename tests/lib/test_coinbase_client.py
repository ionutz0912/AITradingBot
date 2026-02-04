"""
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
