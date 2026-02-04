# AI Trading Bot

AI-powered cryptocurrency trading bot with multi-provider AI support and multi-exchange integration.

## Features

- **Multi-Provider AI Support**: Anthropic Claude, xAI Grok, DeepSeek
- **Multi-Exchange Support**: Coinbase (spot), Bitunix (futures)
- **Multi-Symbol Trading**: Trade multiple cryptocurrencies from a single config
- **Real-Time Market Data**: Fetches prices from CoinGecko, Coinbase, Binance
- **Performance Tracking**: Track P&L, win rate, and trade history
- **Forward Testing**: Simulate trades without risking real capital
- **Notifications**: Discord and Telegram alerts with stop loss info
- **Dashboard**: Comprehensive trading dashboard with all metrics
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

# Optional Notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
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
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (from @BotFather) |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications |

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

### Dashboard

View comprehensive trading status:
```bash
python dashboard.py              # Full dashboard
python dashboard.py --summary    # Quick summary
python dashboard.py --positions  # Open positions only
python dashboard.py --performance # Performance metrics
python dashboard.py --config     # Show configuration
python dashboard.py --json       # JSON output for integrations
```

### Health Check

Verify API connectivity and configuration:
```bash
python health_check.py
```

### Telegram Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) on Telegram
2. Copy your bot token
3. Get your chat ID (message [@userinfobot](https://t.me/userinfobot))
4. Add to `.env`:
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```
5. Test: `python -m lib.telegram_notifications --test`

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
├── dashboard.py             # Trading dashboard
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
│   ├── discord_notifications.py
│   └── telegram_notifications.py  # Telegram alerts
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
