# AI Trading Bot - Development Progress

## Project Overview

AI-powered cryptocurrency trading bot with multi-provider AI support, multi-exchange integration, and comprehensive trading tools.

---

## Features

### AI Providers
| Provider | Config Value | Model | Status |
|----------|--------------|-------|--------|
| **Anthropic (Claude)** | `anthropic` | `claude-sonnet-4-20250514` | Working |
| **xAI (Grok)** | `xai` or `grok` | `grok-3-latest` | Working |
| **DeepSeek** | `deepseek` | `deepseek-chat` | Available |

### Exchange Providers
| Provider | Config Value | Type | Status |
|----------|--------------|------|--------|
| **Coinbase** | `coinbase` | Spot | Working |
| **Bitunix** | `bitunix` | Futures | Available |

### New Features (v2.0)
| Feature | Module | Status |
|---------|--------|--------|
| **Performance Tracking** | `lib/performance_tracker.py` | Complete |
| **Real-Time Market Data** | `lib/market_data.py` | Complete |
| **Health Check Utility** | `health_check.py` | Complete |
| **Configuration Files** | `lib/config.py` | Complete |
| **Multi-Symbol Runner** | `runner_multi.py` | Complete |

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.template .env
# Edit .env with your API keys
```

### 3. Verify Setup
```bash
python health_check.py
```

### 4. Run
```bash
# Single symbol
python3 runner.py

# Multi-symbol with config
python3 runner_multi.py

# Dry run mode
python3 runner_multi.py --dry-run
```

---

## Configuration

### `.env` File Structure
```bash
# AI Provider: anthropic, xai, grok, deepseek
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
XAI_API_KEY=xai-...

# Exchange Provider: coinbase, bitunix
EXCHANGE_PROVIDER=coinbase

# Coinbase (CDP API keys from cloud.coinbase.com/access/api)
COINBASE_API_KEY=organizations/.../apiKeys/...
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----\n

# Bitunix (if using)
BITUNIX_API_KEY=...
BITUNIX_API_SECRET=...

# Optional
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Configuration File (Multi-Symbol)
```bash
# Create sample config
python runner_multi.py --create-config

# Copy and customize
cp configs/config.sample.json configs/config.json
```

---

## Runners

| Runner | Description | Use Case |
|--------|-------------|----------|
| `runner.py` | Single symbol, basic | Simple setups |
| `runner_with_discord.py` | Single symbol + Discord | With notifications |
| `runner_multi.py` | Multi-symbol from config | Production use |

### Multi-Symbol Runner Options
```bash
python runner_multi.py --help
python runner_multi.py --config my_config.json
python runner_multi.py --symbols BTC ETH SOL
python runner_multi.py --dry-run
```

---

## New Modules

### Performance Tracker (`lib/performance_tracker.py`)
Track trading performance with P&L, win rate, and trade history.

```python
from lib import get_tracker

tracker = get_tracker("my_strategy")
tracker.create_trade(
    symbol="BTCUSDT",
    side="buy",
    entry_price=95000,
    exit_price=96000,
    quantity=0.001
)
tracker.print_summary()
tracker.export_to_csv()
```

**Features:**
- Trade history persistence (JSON)
- P&L calculations (realized/unrealized)
- Win rate and average win/loss
- Maximum drawdown tracking
- Win/loss streak tracking
- CSV export

### Market Data (`lib/market_data.py`)
Fetch real-time prices from multiple sources.

```python
from lib import get_market_data, get_enhanced_market_context

# Get current price data
data = get_market_data("BTC")
print(f"BTC: ${data.price:,.2f} ({data.price_change_24h_percent:+.2f}%)")

# Get full context for AI prompts
context = get_enhanced_market_context("BTC")
print(context)
```

**Data Sources:**
- Coinbase (primary)
- CoinGecko (fallback)
- Binance (fallback)

**Includes:**
- Current price
- 24h high/low
- 24h volume
- Fear & Greed Index

### Health Check (`health_check.py`)
Verify API connectivity before trading.

```bash
python health_check.py
```

**Checks:**
- Environment variables
- AI provider connectivity
- Exchange connectivity
- Market data services
- Directory structure
- Python dependencies

### Configuration (`lib/config.py`)
JSON-based configuration management.

```python
from lib import load_config, get_enabled_symbols, validate_config

config = load_config("config.json")
symbols = get_enabled_symbols(config)
issues = validate_config(config)
```

---

## Trading Logic

### Spot Exchange (Coinbase)
| AI Signal | Action |
|-----------|--------|
| **Bullish** | Buy BTC (open long) |
| **Bearish** | Sell BTC (close position - no shorting) |
| **Neutral** | Sell BTC (close position) |

### Futures Exchange (Bitunix)
| AI Signal | Action |
|-----------|--------|
| **Bullish** | Open/hold long position |
| **Bearish** | Open/hold short position |
| **Neutral** | Close any position |

---

## Files Structure

```
AITradingBot/
├── runner.py                 # Basic single-symbol runner
├── runner_with_discord.py    # Runner with Discord notifications
├── runner_multi.py           # Multi-symbol runner (NEW)
├── health_check.py           # API connectivity checker (NEW)
├── batch_runner.sh           # Cron job script
├── requirements.txt          # Python dependencies
├── .env.template             # Environment template
├── .env                      # Your config (gitignored)
├── configs/                  # Configuration files (NEW)
│   └── config.sample.json    # Sample configuration
├── lib/
│   ├── ai.py                 # Multi-provider AI module
│   ├── coinbase_client.py    # Coinbase exchange client
│   ├── bitunix.py            # Bitunix exchange client
│   ├── forward_tester.py     # Simulated trading
│   ├── market_data.py        # Real-time market data (NEW)
│   ├── performance_tracker.py # P&L tracking (NEW)
│   ├── config.py             # Configuration management (NEW)
│   ├── custom_helpers.py     # Trading helpers
│   └── discord_notifications.py
├── logs/                     # Execution logs
├── ai_responses/             # AI response history
├── performance_data/         # Trade history (NEW)
├── PROGRESS.md               # This file
└── TODO_COINBASE.md          # Coinbase implementation notes
```

---

## Testing

### Forward Testing (Simulated)
Edit `runner.py` or use config file:
```python
FORWARD_TESTING_CONFIG = {
    "run_name": RUN_NAME,
    "initial_capital": 10000,
    "fees": 0.0006,
}
```

Or in `configs/config.json`:
```json
{
  "forward_testing": true,
  "forward_testing_capital": 10000,
  "forward_testing_fees": 0.0006
}
```

### Live Trading
```python
FORWARD_TESTING_CONFIG = None
```

Or in config:
```json
{
  "forward_testing": false
}
```

---

## Completed Work

### Original Features
- [x] Security analysis of original codebase
- [x] Multi-provider AI support (Anthropic, xAI, DeepSeek)
- [x] Coinbase Advanced Trade API integration
- [x] Python 3.9 compatibility fixes
- [x] Discord notifications module
- [x] Forward testing mode
- [x] Exchange provider selection
- [x] Spot trading support (handles no-shorting gracefully)
- [x] PEM secret newline handling for .env files

### New Features (v2.0)
- [x] Performance tracking module (P&L, win rate, history)
- [x] Real-time market data fetching
- [x] Health check utility
- [x] JSON configuration file support
- [x] Multi-symbol runner
- [x] Dry-run mode for testing
- [x] Enhanced AI prompts with market data
- [x] Updated documentation

---

## Live Testing Results

**Coinbase Integration - Verified Working:**
```
2026-02-03 19:18:23 - Coinbase client initialized
2026-02-03 19:18:23 - Live trading mode: Coinbase
2026-02-03 19:18:23 - AI Interpretation: Neutral
2026-02-03 19:18:23 - Current Position: None
2026-02-03 19:18:23 - Available Capital: 10.0 USD
2026-02-03 19:18:23 - Neutral signal: No position open, doing nothing
2026-02-03 19:18:23 - === Run Completed ===
```

---

## API Resources

### Coinbase
- Documentation: https://docs.cdp.coinbase.com/advanced-trade/docs/welcome
- Python SDK: https://github.com/coinbase/coinbase-advanced-py
- API Keys: https://cloud.coinbase.com/access/api

### AI Providers
- Anthropic: https://console.anthropic.com/
- xAI: https://console.x.ai/
- DeepSeek: https://platform.deepseek.com/

### Market Data
- CoinGecko: https://www.coingecko.com/api/documentation
- Fear & Greed Index: https://alternative.me/crypto/fear-and-greed-index/

---

## Security Notes

- Never commit `.env` files (already in `.gitignore`)
- Rotate API keys if exposed
- Use forward testing before live trading
- Start with small position sizes ($5-20)
- Monitor bot activity regularly
- Coinbase CDP keys use PEM format - keep private

---

*Last Updated: 2026-02-04*
