# AI Trading Bot

AI-powered cryptocurrency trading bot with multi-provider AI support and multi-exchange integration.

## Features

- **Multi-Provider AI Support**: Anthropic Claude, xAI Grok, DeepSeek
- **Multi-Exchange Support**: Coinbase (spot), Bitunix (futures)
- **Multi-Symbol Trading**: Trade multiple cryptocurrencies from a single config
- **Real-Time Market Data**: Fetches prices from CoinGecko, Coinbase, Binance
- **Performance Tracking**: Track P&L, win rate, and trade history
- **Forward Testing**: Simulate trades without risking real capital
- **Discord Notifications**: Get alerts for trade signals
- **Health Check**: Verify API connectivity before trading

---

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/RobotTraders/AITradingBot.git
cd AITradingBot
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.template .env
nano .env  # or your preferred editor
```

Add your API keys:
```env
# AI Provider (choose one)
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
# XAI_API_KEY=xai-...
# DEEPSEEK_API_KEY=sk-...

# Exchange Provider (choose one)
EXCHANGE_PROVIDER=coinbase
COINBASE_API_KEY=organizations/.../apiKeys/...
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----\n

# Optional
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 3. Verify Setup

```bash
python health_check.py
```

### 4. Run

```bash
# Single symbol (basic)
python runner.py

# Multi-symbol with config
python runner_multi.py

# Dry run (analyze without trading)
python runner_multi.py --dry-run
```

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AI_PROVIDER` | AI provider: `anthropic`, `xai`, `grok`, `deepseek` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `XAI_API_KEY` | xAI Grok API key |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `EXCHANGE_PROVIDER` | Exchange: `coinbase` or `bitunix` |
| `COINBASE_API_KEY` | Coinbase CDP API key |
| `COINBASE_API_SECRET` | Coinbase CDP secret (PEM format) |
| `DISCORD_WEBHOOK_URL` | Discord webhook for notifications |

### Configuration File (Multi-Symbol)

Create `configs/config.json`:

```bash
python runner_multi.py --create-config
cp configs/config.sample.json configs/config.json
```

Example configuration:
```json
{
  "run_name": "my_strategy",
  "forward_testing": true,
  "ai_provider": "anthropic",
  "exchange_provider": "coinbase",
  "include_market_data": true,
  "symbols": [
    {
      "symbol": "BTCUSDT",
      "crypto_name": "Bitcoin",
      "enabled": true,
      "position_size": 5.0,
      "stop_loss_percent": 10.0
    },
    {
      "symbol": "ETHUSDT",
      "crypto_name": "Ethereum",
      "enabled": false,
      "position_size": 5.0
    }
  ]
}
```

---

## Runners

| Runner | Description |
|--------|-------------|
| `runner.py` | Single symbol, basic execution |
| `runner_with_discord.py` | Single symbol with Discord notifications |
| `runner_multi.py` | Multi-symbol from config file |

### Multi-Symbol Runner Options

```bash
python runner_multi.py --help

# Use custom config file
python runner_multi.py --config my_config.json

# Trade specific symbols only
python runner_multi.py --symbols BTC ETH SOL

# Analyze without executing trades
python runner_multi.py --dry-run
```

---

## Utilities

### Health Check

Verify API connectivity and configuration:
```bash
python health_check.py
```

### Performance Tracking

Track your trading performance:
```python
from lib import get_tracker

tracker = get_tracker("my_strategy")
tracker.print_summary()
tracker.export_to_csv()
```

---

## Directory Structure

```
AITradingBot/
├── runner.py                # Basic single-symbol runner
├── runner_with_discord.py   # Runner with Discord notifications
├── runner_multi.py          # Multi-symbol runner
├── health_check.py          # API connectivity checker
├── batch_runner.sh          # Cron job script
├── requirements.txt         # Python dependencies
├── .env.template            # Environment template
├── lib/
│   ├── ai.py                # Multi-provider AI module
│   ├── coinbase_client.py   # Coinbase exchange client
│   ├── bitunix.py           # Bitunix exchange client
│   ├── forward_tester.py    # Simulated trading
│   ├── market_data.py       # Real-time price fetching
│   ├── performance_tracker.py  # P&L tracking
│   ├── config.py            # Configuration management
│   ├── custom_helpers.py    # Trading helpers
│   └── discord_notifications.py
├── configs/                 # Configuration files
├── logs/                    # Execution logs
├── ai_responses/            # AI response history
└── performance_data/        # Trade history
```

---

## Automated Trading (Cron)

Run the bot on a schedule:

```bash
crontab -e
```

Add this line for daily execution at midnight UTC:
```cron
0 0 * * * cd /path/to/AITradingBot && bash batch_runner.sh >> cron.log 2>&1
```

---

## Trading Logic

### Spot Exchange (Coinbase)

| AI Signal | Action |
|-----------|--------|
| Bullish | Buy (open long) |
| Bearish | Sell (close position - no shorting) |
| Neutral | Close any position |

### Futures Exchange (Bitunix)

| AI Signal | Action |
|-----------|--------|
| Bullish | Open/hold long |
| Bearish | Open/hold short |
| Neutral | Close any position |

---

## Requirements

- Python 3.9+
- See `requirements.txt` for packages

---

## Security Notes

- Never commit `.env` files
- Rotate API keys if exposed
- Use forward testing before live trading
- Start with small position sizes ($5-20)
- Monitor bot activity regularly

---

## License

MIT License - see LICENSE file

---

## Disclaimer

This software is for educational and research purposes only. It is not financial advice. Trading cryptocurrency carries significant risk. The developers are not responsible for any financial losses incurred through use of this software. Always do your own research and consider consulting a financial advisor.
