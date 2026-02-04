"""
Tests for lib/config.py - Configuration management module
"""

import pytest
import json
import os
from pathlib import Path
from pydantic import ValidationError

from lib.config import (
    SimulationConfig,
    SymbolConfig,
    TradingConfig,
    get_default_config,
    get_default_symbols,
    save_config,
    load_config,
    apply_env_overrides,
    get_enabled_symbols,
    validate_config,
    create_sample_config,
)


class TestSimulationConfig:
    """Test SimulationConfig model validation."""

    def test_valid_simulation_config(self):
        """Test creating a valid SimulationConfig."""
        config = SimulationConfig(
            name="Test Simulation",
            symbol="BTCUSDT",
            crypto_name="Bitcoin",
            initial_capital=10000.0,
            position_size=5.0,
            fees=0.0006,
            ai_provider="anthropic"
        )

        assert config.name == "Test Simulation"
        assert config.symbol == "BTCUSDT"
        assert config.initial_capital == 10000.0
        assert config.fees == 0.0006

    def test_simulation_config_defaults(self):
        """Test default values in SimulationConfig."""
        config = SimulationConfig(
            name="Test",
            symbol="BTCUSDT",
            crypto_name="Bitcoin"
        )

        assert config.initial_capital == 10000.0
        assert config.position_size == 5.0
        assert config.fees == 0.0006
        assert config.stop_loss_percent == 10.0
        assert config.max_daily_trades == 10
        assert config.check_interval_seconds == 300

    def test_simulation_config_percentage_position_size(self):
        """Test SimulationConfig with percentage position size."""
        config = SimulationConfig(
            name="Test",
            symbol="BTCUSDT",
            crypto_name="Bitcoin",
            position_size="10%"
        )

        assert config.position_size == "10%"

    def test_simulation_config_invalid_ai_provider(self):
        """Test SimulationConfig with invalid AI provider."""
        with pytest.raises(ValidationError):
            SimulationConfig(
                name="Test",
                symbol="BTCUSDT",
                crypto_name="Bitcoin",
                ai_provider="invalid_provider"
            )

    def test_simulation_config_capital_too_low(self):
        """Test SimulationConfig with capital below minimum."""
        with pytest.raises(ValidationError):
            SimulationConfig(
                name="Test",
                symbol="BTCUSDT",
                crypto_name="Bitcoin",
                initial_capital=50.0  # Below minimum of 100
            )


class TestSymbolConfig:
    """Test SymbolConfig model validation."""

    def test_valid_symbol_config(self):
        """Test creating a valid SymbolConfig."""
        config = SymbolConfig(
            symbol="BTCUSDT",
            crypto_name="Bitcoin",
            enabled=True,
            position_size=5.0,
            stop_loss_percent=10.0,
            leverage=1,
            margin_mode="ISOLATION"
        )

        assert config.symbol == "BTCUSDT"
        assert config.enabled is True
        assert config.leverage == 1

    def test_symbol_config_defaults(self):
        """Test default values in SymbolConfig."""
        config = SymbolConfig(
            symbol="ETHUSDT",
            crypto_name="Ethereum"
        )

        assert config.enabled is True
        assert config.position_size == 5.0
        assert config.leverage == 1
        assert config.margin_mode == "ISOLATION"

    def test_symbol_config_cross_margin(self):
        """Test SymbolConfig with CROSS margin mode."""
        config = SymbolConfig(
            symbol="BTCUSDT",
            crypto_name="Bitcoin",
            margin_mode="cross"  # Should normalize to uppercase
        )

        assert config.margin_mode == "CROSS"

    def test_symbol_config_invalid_margin_mode(self):
        """Test SymbolConfig with invalid margin mode."""
        with pytest.raises(ValidationError):
            SymbolConfig(
                symbol="BTCUSDT",
                crypto_name="Bitcoin",
                margin_mode="INVALID"
            )

    def test_symbol_config_invalid_leverage(self):
        """Test SymbolConfig with invalid leverage."""
        with pytest.raises(ValidationError):
            SymbolConfig(
                symbol="BTCUSDT",
                crypto_name="Bitcoin",
                leverage=200  # Above maximum of 125
            )


class TestTradingConfig:
    """Test TradingConfig model validation."""

    def test_valid_trading_config(self, sample_symbol_config):
        """Test creating a valid TradingConfig."""
        config = TradingConfig(
            run_name="test_strategy",
            symbols=[sample_symbol_config],
            ai_provider="anthropic",
            exchange_provider="coinbase"
        )

        assert config.run_name == "test_strategy"
        assert len(config.symbols) == 1
        assert config.ai_provider == "anthropic"
        assert config.exchange_provider == "coinbase"

    def test_trading_config_defaults(self):
        """Test default values in TradingConfig."""
        config = TradingConfig()

        assert config.run_name == "trading_bot"
        assert config.forward_testing is False
        assert config.max_positions == 5
        assert config.max_daily_trades == 20

    def test_trading_config_invalid_ai_provider(self):
        """Test TradingConfig with invalid AI provider."""
        with pytest.raises(ValidationError):
            TradingConfig(ai_provider="invalid")

    def test_trading_config_invalid_exchange(self):
        """Test TradingConfig with invalid exchange provider."""
        with pytest.raises(ValidationError):
            TradingConfig(exchange_provider="invalid")


class TestConfigHelpers:
    """Test configuration helper functions."""

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_default_config()

        assert isinstance(config, TradingConfig)
        assert config.run_name == "ai_trading_bot"
        assert len(config.symbols) > 0

    def test_get_default_symbols(self):
        """Test getting default symbol configurations."""
        symbols = get_default_symbols()

        assert len(symbols) >= 3
        assert all(isinstance(s, SymbolConfig) for s in symbols)
        assert any(s.symbol == "BTCUSDT" for s in symbols)

    def test_get_enabled_symbols(self, sample_trading_config):
        """Test filtering enabled symbols."""
        # Add a disabled symbol
        disabled_symbol = SymbolConfig(
            symbol="DISABLED",
            crypto_name="Disabled",
            enabled=False
        )
        sample_trading_config.symbols.append(disabled_symbol)

        enabled = get_enabled_symbols(sample_trading_config)

        assert len(enabled) == 1  # Only the original enabled symbol
        assert all(s.enabled for s in enabled)


class TestConfigFileOperations:
    """Test configuration file save/load operations."""

    def test_save_and_load_config(self, temp_config_dir, sample_trading_config):
        """Test saving and loading configuration from file."""
        # Save config
        filepath = save_config(sample_trading_config, "test_config.json")
        assert Path(filepath).exists()

        # Load config
        loaded_config = load_config("test_config.json")

        assert loaded_config.run_name == sample_trading_config.run_name
        assert len(loaded_config.symbols) == len(sample_trading_config.symbols)
        assert loaded_config.ai_provider == sample_trading_config.ai_provider

    def test_load_config_nonexistent_file(self, temp_config_dir):
        """Test loading config from nonexistent file returns defaults."""
        config = load_config("nonexistent.json")

        assert isinstance(config, TradingConfig)
        assert config.run_name == "ai_trading_bot"  # Default value

    def test_load_config_invalid_json(self, temp_config_dir):
        """Test loading config from invalid JSON file."""
        # Create invalid JSON file
        invalid_file = temp_config_dir / "invalid.json"
        invalid_file.write_text("{ invalid json }")

        config = load_config("invalid.json")

        # Should return default config on error
        assert isinstance(config, TradingConfig)

    def test_create_sample_config(self, temp_config_dir):
        """Test creating sample configuration file."""
        filepath = create_sample_config()

        assert Path(filepath).exists()

        # Verify it's valid JSON
        with open(filepath) as f:
            data = json.load(f)
            assert "_comment" in data
            assert "symbols" in data


class TestEnvOverrides:
    """Test environment variable override functionality."""

    def test_apply_env_overrides_ai_provider(self, sample_trading_config, monkeypatch):
        """Test AI provider override from environment."""
        monkeypatch.setenv("AI_PROVIDER", "xai")

        overridden = apply_env_overrides(sample_trading_config)

        assert overridden.ai_provider == "xai"

    def test_apply_env_overrides_exchange(self, sample_trading_config, monkeypatch):
        """Test exchange provider override from environment."""
        monkeypatch.setenv("EXCHANGE_PROVIDER", "bitunix")

        overridden = apply_env_overrides(sample_trading_config)

        assert overridden.exchange_provider == "bitunix"

    def test_apply_env_overrides_forward_testing(self, sample_trading_config, monkeypatch):
        """Test forward testing override from environment."""
        monkeypatch.setenv("FORWARD_TESTING", "true")

        overridden = apply_env_overrides(sample_trading_config)

        assert overridden.forward_testing is True

    def test_apply_env_overrides_discord(self, sample_trading_config, monkeypatch):
        """Test Discord enabling via webhook URL."""
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/webhook/test")

        overridden = apply_env_overrides(sample_trading_config)

        assert overridden.discord_enabled is True


class TestConfigValidation:
    """Test configuration validation logic."""

    def test_validate_config_valid(self, sample_trading_config):
        """Test validation of valid configuration."""
        issues = validate_config(sample_trading_config)

        assert len(issues) == 0

    def test_validate_config_no_enabled_symbols(self):
        """Test validation when no symbols are enabled."""
        config = TradingConfig(
            symbols=[
                SymbolConfig(symbol="BTC", crypto_name="Bitcoin", enabled=False)
            ]
        )

        issues = validate_config(config)

        assert len(issues) > 0
        assert any("No trading symbols are enabled" in issue for issue in issues)

    def test_validate_config_invalid_position_size(self):
        """Test validation of invalid position size format."""
        config = TradingConfig(
            symbols=[
                SymbolConfig(
                    symbol="BTC",
                    crypto_name="Bitcoin",
                    position_size="invalid"
                )
            ]
        )

        issues = validate_config(config)

        assert len(issues) > 0
        assert any("Invalid position_size format" in issue for issue in issues)

    def test_validate_config_coinbase_leverage(self):
        """Test validation of leverage on Coinbase (spot)."""
        config = TradingConfig(
            exchange_provider="coinbase",
            symbols=[
                SymbolConfig(
                    symbol="BTC",
                    crypto_name="Bitcoin",
                    leverage=5  # Invalid for Coinbase spot
                )
            ]
        )

        issues = validate_config(config)

        assert len(issues) > 0
        assert any("leverage" in issue.lower() for issue in issues)

    def test_validate_config_max_positions(self):
        """Test validation of max_positions vs enabled symbols."""
        config = TradingConfig(
            max_positions=1,
            symbols=[
                SymbolConfig(symbol="BTC", crypto_name="Bitcoin", enabled=True),
                SymbolConfig(symbol="ETH", crypto_name="Ethereum", enabled=True)
            ]
        )

        issues = validate_config(config)

        assert len(issues) > 0
        assert any("max_positions" in issue for issue in issues)


@pytest.mark.parametrize("provider", ["anthropic", "xai", "grok", "deepseek"])
def test_ai_provider_validation(provider):
    """Test all valid AI providers."""
    config = SimulationConfig(
        name="Test",
        symbol="BTCUSDT",
        crypto_name="Bitcoin",
        ai_provider=provider
    )

    assert config.ai_provider in ["anthropic", "xai", "grok", "deepseek"]


@pytest.mark.parametrize("exchange", ["coinbase", "bitunix"])
def test_exchange_provider_validation(exchange):
    """Test all valid exchange providers."""
    config = TradingConfig(exchange_provider=exchange)

    assert config.exchange_provider in ["coinbase", "bitunix"]
