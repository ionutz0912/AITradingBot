"""
Pytest configuration and shared fixtures for AI Trading Bot tests.

This module provides reusable fixtures for:
- Database connections
- Mock API responses
- Sample configurations
- Temp directories
- Flask test client
"""

import os
import pytest
import tempfile
import sqlite3
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from typing import Generator, Dict, Any

# Import application modules
from lib.config import TradingConfig, SymbolConfig, SimulationConfig
from lib.database import init_database, get_connection
from dashboard.app import create_app


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_db_path(tmp_path) -> Generator[Path, None, None]:
    """Provide a temporary database path."""
    db_file = tmp_path / "test_trading_bot.db"
    yield db_file
    # Cleanup
    if db_file.exists():
        db_file.unlink()


@pytest.fixture
def test_db(temp_db_path, monkeypatch) -> Generator[None, None, None]:
    """
    Provide an initialized test database.

    Uses in-memory SQLite for fast testing.
    Automatically patches database module to use test database.
    """
    # Patch the database module to use test database
    import lib.database as db_module

    original_db_path = db_module.DATABASE_FILE
    monkeypatch.setattr(db_module, "DATABASE_FILE", temp_db_path)

    # Initialize test database
    init_database()

    yield

    # Cleanup is automatic with tmp_path


@pytest.fixture
def db_connection(test_db):
    """Provide a database connection for tests."""
    with get_connection() as conn:
        yield conn


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_symbol_config() -> SymbolConfig:
    """Provide a sample SymbolConfig for testing."""
    return SymbolConfig(
        symbol="BTCUSDT",
        crypto_name="Bitcoin",
        enabled=True,
        position_size=5.0,
        stop_loss_percent=10.0,
        leverage=1,
        margin_mode="ISOLATION"
    )


@pytest.fixture
def sample_trading_config(sample_symbol_config) -> TradingConfig:
    """Provide a sample TradingConfig for testing."""
    return TradingConfig(
        run_name="test_strategy",
        forward_testing=True,
        forward_testing_capital=10000.0,
        forward_testing_fees=0.0006,
        symbols=[sample_symbol_config],
        ai_provider="anthropic",
        exchange_provider="coinbase",
        discord_enabled=False,
        telegram_enabled=False,
        max_positions=5,
        max_daily_trades=20
    )


@pytest.fixture
def sample_simulation_config() -> SimulationConfig:
    """Provide a sample SimulationConfig for testing."""
    return SimulationConfig(
        name="Test Simulation",
        symbol="BTCUSDT",
        crypto_name="Bitcoin",
        initial_capital=10000.0,
        position_size=5.0,
        fees=0.0006,
        ai_provider="anthropic",
        stop_loss_percent=10.0,
        max_daily_trades=10,
        check_interval_seconds=300
    )


# ============================================================================
# Mock API Response Fixtures
# ============================================================================

@pytest.fixture
def mock_anthropic_response() -> Dict[str, Any]:
    """Mock Anthropic API response."""
    return {
        "id": "msg_01test",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_01test",
                "name": "btcusdt_outlook",
                "input": {
                    "interpretation": "Bullish",
                    "reasons": "Strong upward momentum with increasing volume."
                }
            }
        ],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "tool_use"
    }


@pytest.fixture
def mock_xai_response() -> Dict[str, Any]:
    """Mock xAI (Grok) API response."""
    return {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "btcusdt_outlook",
                                "arguments": json.dumps({
                                    "interpretation": "Bearish",
                                    "reasons": "Declining momentum with high sell pressure."
                                })
                            }
                        }
                    ]
                }
            }
        ]
    }


@pytest.fixture
def mock_coingecko_response() -> Dict[str, Any]:
    """Mock CoinGecko API response."""
    return {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "market_data": {
            "current_price": {"usd": 50000.0},
            "price_change_24h": 1500.0,
            "price_change_percentage_24h": 3.1,
            "high_24h": {"usd": 51000.0},
            "low_24h": {"usd": 48500.0},
            "total_volume": {"usd": 25000000000.0},
            "market_cap": {"usd": 1000000000000.0}
        }
    }


@pytest.fixture
def mock_coinbase_price_response() -> Dict[str, Any]:
    """Mock Coinbase price API response."""
    return {
        "last": "50000.00",
        "open": "48500.00",
        "high": "51000.00",
        "low": "48500.00",
        "volume": "500000.00"
    }


@pytest.fixture
def mock_binance_response() -> Dict[str, Any]:
    """Mock Binance API response."""
    return {
        "symbol": "BTCUSDT",
        "lastPrice": "50000.00",
        "priceChange": "1500.00",
        "priceChangePercent": "3.1",
        "highPrice": "51000.00",
        "lowPrice": "48500.00",
        "quoteVolume": "25000000000.00"
    }


@pytest.fixture
def mock_telegram_response() -> Dict[str, Any]:
    """Mock Telegram API response."""
    return {
        "ok": True,
        "result": {
            "message_id": 12345,
            "chat": {"id": 123456789},
            "text": "Test message"
        }
    }


# ============================================================================
# Mock Objects and Services
# ============================================================================

@pytest.fixture
def mock_requests(mocker):
    """Mock requests library for API calls."""
    mock_post = mocker.patch("requests.post")
    mock_get = mocker.patch("requests.get")
    return {"post": mock_post, "get": mock_get}


@pytest.fixture
def mock_coinbase_client(mocker):
    """Mock Coinbase REST client."""
    mock_client = MagicMock()

    # Mock account balance
    mock_client.get_accounts.return_value = Mock(
        accounts=[
            Mock(currency="USD", available_balance=Mock(value="10000.00"), uuid="acc-usd"),
            Mock(currency="BTC", available_balance=Mock(value="0.5"), uuid="acc-btc")
        ]
    )

    # Mock price
    mock_client.get_product.return_value = Mock(price="50000.00")

    # Mock order creation
    mock_client.create_order.return_value = {
        "order_id": "order-123",
        "success": True
    }

    mocker.patch("coinbase.rest.RESTClient", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_ai_provider(mocker):
    """Mock AI provider for testing."""
    from lib.ai import AIOutlook

    mock_provider = Mock()
    mock_provider.name = "MockAI"
    mock_provider.send_request.return_value = AIOutlook(
        interpretation="Bullish",
        reasons="Test reasoning for bullish outlook."
    )

    return mock_provider


# ============================================================================
# Flask Application Fixtures
# ============================================================================

@pytest.fixture
def flask_app():
    """Provide a Flask test application."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture
def flask_client(flask_app):
    """Provide a Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def flask_runner(flask_app):
    """Provide a Flask CLI test runner."""
    return flask_app.test_cli_runner()


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch) -> Path:
    """Provide a temporary config directory."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()

    import lib.config as config_module
    monkeypatch.setattr(config_module, "CONFIG_DIR", str(config_dir))

    return config_dir


@pytest.fixture
def temp_performance_dir(tmp_path, monkeypatch) -> Path:
    """Provide a temporary performance data directory."""
    perf_dir = tmp_path / "performance_data"
    perf_dir.mkdir()

    import lib.performance_tracker as perf_module
    monkeypatch.setattr(perf_module, "PERFORMANCE_DIR", str(perf_dir))

    return perf_dir


@pytest.fixture
def temp_forward_test_dir(tmp_path, monkeypatch) -> Path:
    """Provide a temporary forward testing results directory."""
    ft_dir = tmp_path / "forward_testing_results"
    ft_dir.mkdir()
    return ft_dir


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_trade_data() -> Dict[str, Any]:
    """Provide sample trade data for testing."""
    return {
        "trade_id": "BTC_12345",
        "symbol": "BTCUSDT",
        "side": "buy",
        "entry_price": 48000.0,
        "exit_price": 50000.0,
        "quantity": 0.1,
        "entry_time": "2024-01-01T00:00:00+00:00",
        "exit_time": "2024-01-02T00:00:00+00:00",
        "pnl": 200.0,
        "pnl_percent": 4.17,
        "fees": 5.0,
        "notes": "Test trade"
    }


@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    """Provide sample market data for testing."""
    return {
        "symbol": "BTC",
        "price": 50000.0,
        "price_change_24h": 1500.0,
        "price_change_24h_percent": 3.1,
        "high_24h": 51000.0,
        "low_24h": 48500.0,
        "volume_24h": 25000000000.0,
        "market_cap": 1000000000000.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# Environment Variable Fixtures
# ============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    env_vars = {
        "AI_PROVIDER": "anthropic",
        "ANTHROPIC_API_KEY": "test_anthropic_key",
        "XAI_API_KEY": "test_xai_key",
        "DEEPSEEK_API_KEY": "test_deepseek_key",
        "EXCHANGE_PROVIDER": "coinbase",
        "COINBASE_API_KEY": "test_coinbase_key",
        "COINBASE_API_SECRET": "test_coinbase_secret",
        "TELEGRAM_BOT_TOKEN": "test_telegram_token",
        "TELEGRAM_CHAT_ID": "123456789",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
        "FORWARD_TESTING": "true"
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Automatically cleanup test files after each test."""
    yield

    # Cleanup patterns
    patterns = [
        "test_*.json",
        "test_*.csv",
        "test_*.db"
    ]

    for pattern in patterns:
        for file in Path(".").glob(pattern):
            try:
                file.unlink()
            except Exception:
                pass


# ============================================================================
# Logging Fixtures
# ============================================================================

@pytest.fixture
def caplog_info(caplog):
    """Capture INFO level logs and above."""
    import logging
    caplog.set_level(logging.INFO)
    return caplog


# ============================================================================
# Parametrize Helpers
# ============================================================================

# Common test parameters
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
AI_PROVIDERS = ["anthropic", "xai", "deepseek"]
EXCHANGE_PROVIDERS = ["coinbase", "bitunix"]
INTERPRETATIONS = ["Bullish", "Bearish", "Neutral"]
