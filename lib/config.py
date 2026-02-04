"""
Configuration Management Module for AI Trading Bot

Supports loading trading configurations from JSON files,
environment variables, and programmatic defaults.

Features:
- JSON-based configuration files
- Environment variable overrides
- Multi-symbol configuration support
- Validation with Pydantic models
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel, Field, field_validator

CONFIG_DIR = "configs"
DEFAULT_CONFIG_FILE = "config.json"


class SimulationConfig(BaseModel):
    """Configuration for a trading simulation."""
    name: str = Field(description="Display name for the simulation")
    symbol: str = Field(description="Trading symbol (e.g., BTCUSDT)")
    crypto_name: str = Field(description="Human-readable name (e.g., Bitcoin)")

    # Capital and position settings
    initial_capital: float = Field(default=10000.0, ge=100, description="Initial capital for simulation")
    position_size: Union[str, float] = Field(
        default=5.0,
        description="Position size: USD amount (5.0) or percentage ('10%')"
    )
    fees: float = Field(default=0.0006, ge=0, description="Fee rate per trade")

    # AI settings
    ai_provider: str = Field(default="anthropic", description="AI provider: anthropic, xai, grok, deepseek")

    # Risk settings
    stop_loss_percent: Optional[float] = Field(
        default=10.0,
        ge=0.1,
        le=50.0,
        description="Stop loss percentage from entry price"
    )
    max_daily_trades: int = Field(default=10, ge=1, le=100, description="Maximum trades per day")

    # Notification settings
    telegram_enabled: bool = Field(default=True, description="Send Telegram notifications for this simulation")
    telegram_include_reasoning: bool = Field(default=False, description="Include AI reasoning in notifications")

    # Execution settings
    check_interval_seconds: int = Field(default=300, ge=60, le=3600, description="Interval between market checks")

    @field_validator('ai_provider')
    @classmethod
    def validate_ai_provider(cls, v):
        valid = ['anthropic', 'xai', 'grok', 'deepseek']
        if v.lower() not in valid:
            raise ValueError(f'ai_provider must be one of: {valid}')
        return v.lower()


class SymbolConfig(BaseModel):
    """Configuration for a single trading symbol."""
    symbol: str = Field(description="Trading symbol (e.g., BTCUSDT)")
    crypto_name: str = Field(description="Human-readable name (e.g., Bitcoin)")
    enabled: bool = Field(default=True, description="Whether to trade this symbol")
    position_size: Union[str, float] = Field(
        default=5.0,
        description="Position size: USD amount (5.0) or percentage ('10%')"
    )
    stop_loss_percent: Optional[float] = Field(
        default=10.0,
        description="Stop loss percentage from entry price"
    )
    leverage: int = Field(default=1, ge=1, le=125, description="Leverage (1-125)")
    margin_mode: str = Field(default="ISOLATION", description="ISOLATION or CROSS")

    @field_validator('margin_mode')
    @classmethod
    def validate_margin_mode(cls, v):
        if v.upper() not in ('ISOLATION', 'CROSS'):
            raise ValueError('margin_mode must be ISOLATION or CROSS')
        return v.upper()


class TradingConfig(BaseModel):
    """Main trading bot configuration."""
    # General settings
    run_name: str = Field(default="trading_bot", description="Name for this run/strategy")
    forward_testing: bool = Field(default=False, description="Enable simulated trading")
    forward_testing_capital: float = Field(default=10000, description="Initial capital for forward testing")
    forward_testing_fees: float = Field(default=0.0006, description="Fee rate for forward testing")

    # Symbols to trade
    symbols: List[SymbolConfig] = Field(default_factory=list, description="Trading symbols configuration")

    # AI settings
    ai_provider: str = Field(default="anthropic", description="AI provider: anthropic, xai, grok, deepseek")
    include_market_data: bool = Field(default=True, description="Include real-time market data in AI prompts")

    # Exchange settings
    exchange_provider: str = Field(default="coinbase", description="Exchange: coinbase or bitunix")

    # Notification settings
    discord_enabled: bool = Field(default=False, description="Send Discord notifications")
    discord_include_reasoning: bool = Field(default=False, description="Include AI reasoning in Discord messages")
    telegram_enabled: bool = Field(default=False, description="Send Telegram notifications")
    telegram_include_reasoning: bool = Field(default=False, description="Include AI reasoning in Telegram messages")

    # Risk management
    max_positions: int = Field(default=5, ge=1, description="Maximum concurrent positions")
    max_daily_trades: int = Field(default=20, ge=1, description="Maximum trades per day")
    max_drawdown_percent: float = Field(default=20.0, ge=1, description="Max drawdown before stopping")

    @field_validator('ai_provider')
    @classmethod
    def validate_ai_provider(cls, v):
        valid = ['anthropic', 'xai', 'grok', 'deepseek']
        if v.lower() not in valid:
            raise ValueError(f'ai_provider must be one of: {valid}')
        return v.lower()

    @field_validator('exchange_provider')
    @classmethod
    def validate_exchange_provider(cls, v):
        valid = ['coinbase', 'bitunix']
        if v.lower() not in valid:
            raise ValueError(f'exchange_provider must be one of: {valid}')
        return v.lower()


def get_default_symbols() -> List[SymbolConfig]:
    """Return default symbol configurations."""
    return [
        SymbolConfig(symbol="BTCUSDT", crypto_name="Bitcoin", position_size=5.0),
        SymbolConfig(symbol="ETHUSDT", crypto_name="Ethereum", position_size=5.0, enabled=False),
        SymbolConfig(symbol="SOLUSDT", crypto_name="Solana", position_size=5.0, enabled=False),
    ]


def get_default_config() -> TradingConfig:
    """Return default configuration."""
    return TradingConfig(
        run_name="ai_trading_bot",
        symbols=get_default_symbols(),
        forward_testing=False,
        ai_provider=os.environ.get("AI_PROVIDER", "anthropic"),
        exchange_provider=os.environ.get("EXCHANGE_PROVIDER", "coinbase"),
    )


def ensure_config_dir():
    """Create config directory if it doesn't exist."""
    Path(CONFIG_DIR).mkdir(exist_ok=True)


def save_config(config: TradingConfig, filename: str = DEFAULT_CONFIG_FILE) -> str:
    """Save configuration to a JSON file."""
    ensure_config_dir()
    filepath = Path(CONFIG_DIR) / filename

    with open(filepath, 'w') as f:
        json.dump(config.model_dump(), f, indent=2)

    logging.info(f"Configuration saved to {filepath}")
    return str(filepath)


def load_config(filename: str = DEFAULT_CONFIG_FILE) -> TradingConfig:
    """
    Load configuration from a JSON file.

    Falls back to defaults if file doesn't exist.
    Environment variables override file settings.
    """
    filepath = Path(CONFIG_DIR) / filename

    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            config = TradingConfig(**data)
            logging.info(f"Configuration loaded from {filepath}")
        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"Failed to load config from {filepath}: {e}")
            logging.info("Using default configuration")
            config = get_default_config()
    else:
        logging.info(f"Config file not found at {filepath}, using defaults")
        config = get_default_config()

    # Apply environment variable overrides
    config = apply_env_overrides(config)

    return config


def apply_env_overrides(config: TradingConfig) -> TradingConfig:
    """Apply environment variable overrides to configuration."""
    data = config.model_dump()

    # AI provider override
    if os.environ.get("AI_PROVIDER"):
        data["ai_provider"] = os.environ.get("AI_PROVIDER").lower()

    # Exchange provider override
    if os.environ.get("EXCHANGE_PROVIDER"):
        data["exchange_provider"] = os.environ.get("EXCHANGE_PROVIDER").lower()

    # Forward testing override
    if os.environ.get("FORWARD_TESTING"):
        data["forward_testing"] = os.environ.get("FORWARD_TESTING").lower() in ('true', '1', 'yes')

    # Discord override
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        data["discord_enabled"] = True

    return TradingConfig(**data)


def create_sample_config() -> str:
    """Create a sample configuration file with comments."""
    ensure_config_dir()
    filepath = Path(CONFIG_DIR) / "config.sample.json"

    sample = {
        "_comment": "AI Trading Bot Configuration - Copy to config.json and customize",
        "run_name": "my_trading_strategy",
        "forward_testing": True,
        "forward_testing_capital": 10000,
        "forward_testing_fees": 0.0006,
        "ai_provider": "anthropic",
        "exchange_provider": "coinbase",
        "include_market_data": True,
        "discord_enabled": False,
        "discord_include_reasoning": False,
        "max_positions": 5,
        "max_daily_trades": 20,
        "max_drawdown_percent": 20.0,
        "symbols": [
            {
                "_comment": "Bitcoin - Primary trading pair",
                "symbol": "BTCUSDT",
                "crypto_name": "Bitcoin",
                "enabled": True,
                "position_size": 5.0,
                "stop_loss_percent": 10.0,
                "leverage": 1,
                "margin_mode": "ISOLATION"
            },
            {
                "_comment": "Ethereum - Secondary pair (disabled by default)",
                "symbol": "ETHUSDT",
                "crypto_name": "Ethereum",
                "enabled": False,
                "position_size": 5.0,
                "stop_loss_percent": 10.0,
                "leverage": 1,
                "margin_mode": "ISOLATION"
            },
            {
                "_comment": "Solana - Higher volatility (disabled by default)",
                "symbol": "SOLUSDT",
                "crypto_name": "Solana",
                "enabled": False,
                "position_size": "5%",
                "stop_loss_percent": 15.0,
                "leverage": 1,
                "margin_mode": "ISOLATION"
            }
        ]
    }

    with open(filepath, 'w') as f:
        json.dump(sample, f, indent=2)

    logging.info(f"Sample configuration created at {filepath}")
    return str(filepath)


def get_enabled_symbols(config: TradingConfig) -> List[SymbolConfig]:
    """Get only enabled symbols from configuration."""
    return [s for s in config.symbols if s.enabled]


def validate_config(config: TradingConfig) -> List[str]:
    """
    Validate configuration and return list of issues.

    Returns empty list if configuration is valid.
    """
    issues = []

    # Check for enabled symbols
    enabled = get_enabled_symbols(config)
    if not enabled:
        issues.append("No trading symbols are enabled")

    # Check position sizes
    for symbol in enabled:
        if isinstance(symbol.position_size, str):
            if not symbol.position_size.endswith('%'):
                issues.append(f"{symbol.symbol}: Invalid position_size format (use number or 'X%')")
        elif symbol.position_size <= 0:
            issues.append(f"{symbol.symbol}: position_size must be positive")

    # Check leverage for spot exchanges
    if config.exchange_provider == "coinbase":
        for symbol in enabled:
            if symbol.leverage > 1:
                issues.append(f"{symbol.symbol}: Coinbase spot doesn't support leverage > 1")

    # Check max positions
    if config.max_positions < len(enabled):
        issues.append(f"max_positions ({config.max_positions}) is less than enabled symbols ({len(enabled)})")

    return issues


# CLI helper for generating configs
def init_config_cli():
    """Initialize configuration from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="AI Trading Bot Configuration Manager")
    parser.add_argument('--create-sample', action='store_true', help="Create sample config file")
    parser.add_argument('--validate', type=str, help="Validate a config file")
    parser.add_argument('--show-default', action='store_true', help="Show default configuration")

    args = parser.parse_args()

    if args.create_sample:
        path = create_sample_config()
        print(f"Sample configuration created: {path}")

    elif args.validate:
        try:
            config = load_config(args.validate)
            issues = validate_config(config)
            if issues:
                print("Configuration issues found:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("Configuration is valid!")
        except Exception as e:
            print(f"Failed to load configuration: {e}")

    elif args.show_default:
        config = get_default_config()
        print(json.dumps(config.model_dump(), indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    init_config_cli()
