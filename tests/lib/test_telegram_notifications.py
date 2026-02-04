"""
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
