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

# View dashboard
python dashboard.py
```

---

## Configuration

### Environment Variables

Create a `.env` file with your credentials:

```env
# ===========================================
# AI PROVIDER CONFIGURATION
# ===========================================
# Choose one: anthropic, xai, grok, deepseek
AI_PROVIDER=anthropic

# Anthropic Claude (recommended)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# xAI Grok (alternative)
# XAI_API_KEY=xai-xxxxx

# DeepSeek (alternative)
# DEEPSEEK_API_KEY=sk-xxxxx

# ===========================================
# EXCHANGE PROVIDER CONFIGURATION
# ===========================================
# Choose one: coinbase, bitunix
EXCHANGE_PROVIDER=coinbase

# Coinbase Advanced Trade API
# Get keys from: https://cloud.coinbase.com/access/api
COINBASE_API_KEY=organizations/xxx/apiKeys/xxx
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\nMHQC...\n-----END EC PRIVATE KEY-----\n

# Bitunix Futures (alternative)
# BITUNIX_API_KEY=your_key
# BITUNIX_API_SECRET=your_secret

# ===========================================
# NOTIFICATIONS (Optional)
# ===========================================
# Discord Webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/xxx

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `AI_PROVIDER` | Yes | AI provider: `anthropic`, `xai`, `grok`, `deepseek` |
| `ANTHROPIC_API_KEY` | If using Anthropic | Claude API key from console.anthropic.com |
| `XAI_API_KEY` | If using xAI | Grok API key from console.x.ai |
| `DEEPSEEK_API_KEY` | If using DeepSeek | DeepSeek API key |
| `EXCHANGE_PROVIDER` | Yes | Exchange: `coinbase` or `bitunix` |
| `COINBASE_API_KEY` | If using Coinbase | CDP API key |
| `COINBASE_API_SECRET` | If using Coinbase | CDP secret (PEM format, use `\n` for newlines) |
| `BITUNIX_API_KEY` | If using Bitunix | Bitunix API key |
| `BITUNIX_API_SECRET` | If using Bitunix | Bitunix API secret |
| `DISCORD_WEBHOOK_URL` | Optional | Discord webhook URL |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Optional | Telegram chat/channel ID |

---

## Notifications

### Telegram Setup (Recommended)

Telegram provides instant mobile notifications with detailed trade information.

#### Step 1: Create a Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "My Trading Bot")
4. Choose a username (must end in `bot`, e.g., `my_trading_alerts_bot`)
5. Copy the **bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Step 2: Get Your Chat ID

1. Start a chat with your new bot (search for it and click Start)
2. Send any message to the bot
3. Open [@userinfobot](https://t.me/userinfobot) and it will show your chat ID
4. Or use [@getidsbot](https://t.me/getidsbot) - forward a message from your chat

#### Step 3: Configure Environment

Add to your `.env` file:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

#### Step 4: Test Connection

```bash
python -m lib.telegram_notifications --test
```

#### Step 5: Send Demo Alert

```bash
python -m lib.telegram_notifications --demo
```

#### Telegram Alert Format

When a trade signal is generated, you'll receive a message like:

```
📈 Trade Alert: Bitcoin (BTCUSDT)

Signal: 🟢 Bullish
Action: Opening LONG position
Current Price: $95,000.00
Entry Price: $95,000.00

🛑 Stop Loss:
   Price: $85,500.00
   Percent: 10%
   Risk: $9,500.00

💰 Position Size: $50.00

💭 AI Reasoning:
Market showing strong bullish momentum...

⏰ 2026-02-04 12:00:00 UTC
```

#### Telegram Configuration Options

In `configs/config.json`:
```json
{
  "telegram_enabled": true,
  "telegram_include_reasoning": true,
  "telegram_include_stop_loss": true
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `telegram_enabled` | `false` | Enable/disable Telegram notifications |
| `telegram_include_reasoning` | `false` | Include AI reasoning in messages |
| `telegram_include_stop_loss` | `true` | Include stop loss price and percentage |

### Discord Setup

1. Create a webhook in your Discord server (Server Settings > Integrations > Webhooks)
2. Copy the webhook URL
3. Add to `.env`:
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/xxx
```

In `configs/config.json`:
```json
{
  "discord_enabled": true,
  "discord_include_reasoning": false
}
```

---

## Configuration File

### Create Configuration

```bash
python runner_multi.py --create-config
cp configs/config.sample.json configs/config.json
```

### Full Configuration Example

```json
{
  "run_name": "my_trading_strategy",
  "forward_testing": true,
  "forward_testing_capital": 10000,
  "forward_testing_fees": 0.0006,
  "ai_provider": "anthropic",
  "exchange_provider": "coinbase",
  "include_market_data": true,
  "discord_enabled": false,
  "discord_include_reasoning": false,
  "telegram_enabled": true,
  "telegram_include_reasoning": true,
  "telegram_include_stop_loss": true,
  "max_positions": 5,
  "max_daily_trades": 20,
  "max_drawdown_percent": 20.0,
  "symbols": [
    {
      "symbol": "BTCUSDT",
      "crypto_name": "Bitcoin",
      "enabled": true,
      "position_size": 5.0,
      "stop_loss_percent": 10.0,
      "leverage": 1,
      "margin_mode": "ISOLATION"
    },
    {
      "symbol": "ETHUSDT",
      "crypto_name": "Ethereum",
      "enabled": false,
      "position_size": 5.0,
      "stop_loss_percent": 10.0,
      "leverage": 1,
      "margin_mode": "ISOLATION"
    }
  ]
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `run_name` | string | `"trading_bot"` | Strategy name for logs and tracking |
| `forward_testing` | bool | `false` | Enable simulated trading |
| `forward_testing_capital` | float | `10000` | Starting capital for simulation |
| `ai_provider` | string | `"anthropic"` | AI provider to use |
| `exchange_provider` | string | `"coinbase"` | Exchange to trade on |
| `include_market_data` | bool | `true` | Include live prices in AI prompts |
| `max_positions` | int | `5` | Maximum concurrent positions |
| `max_drawdown_percent` | float | `20.0` | Stop trading if drawdown exceeds |

### Symbol Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `symbol` | string | - | Trading pair (e.g., `BTCUSDT`) |
| `crypto_name` | string | - | Display name (e.g., `Bitcoin`) |
| `enabled` | bool | `true` | Whether to trade this symbol |
| `position_size` | float/string | `5.0` | USD amount or `"10%"` of capital |
| `stop_loss_percent` | float | `10.0` | Stop loss % from entry (null to disable) |
| `leverage` | int | `1` | Leverage (1-125, futures only) |
| `margin_mode` | string | `"ISOLATION"` | `ISOLATION` or `CROSS` |

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

# Create sample config
python runner_multi.py --create-config
```

---

## Dashboard

View comprehensive trading status:

```bash
python dashboard.py              # Full dashboard
python dashboard.py --summary    # Quick summary
python dashboard.py --positions  # Open positions only
python dashboard.py --performance # Performance metrics
python dashboard.py --config     # Show configuration
python dashboard.py --json       # JSON output for integrations
```

Dashboard shows:
- Account balances
- Open positions with stop loss levels
- Market data (price, 24h change, volume)
- Fear & Greed Index
- Performance metrics (win rate, P&L, streaks)
- Recent trades
- Active configuration
- System health status

---

## Utilities

### Health Check

Verify all API connections before trading:
```bash
python health_check.py
```

### Performance Tracking

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

Add for daily execution at midnight UTC:
```cron
0 0 * * * cd /path/to/AITradingBot && bash batch_runner.sh >> cron.log 2>&1
```

For every 6 hours:
```cron
0 */6 * * * cd /path/to/AITradingBot && bash batch_runner.sh >> cron.log 2>&1
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

- Never commit `.env` files (already in `.gitignore`)
- Rotate API keys if exposed
- Use forward testing before live trading
- Start with small position sizes ($5-20)
- Monitor bot activity regularly
- Use read-only API keys where possible for testing

---

## Troubleshooting

### Telegram not receiving messages?
1. Make sure you started a chat with your bot first
2. Verify bot token and chat ID with `python -m lib.telegram_notifications --test`
3. Check if bot token has any extra spaces

### Coinbase authentication failing?
1. Ensure PEM secret has `\n` for newlines in `.env`
2. Verify API key has trading permissions
3. Check if keys are from CDP (cloud.coinbase.com), not legacy

### AI request failing?
1. Verify API key is correct for selected provider
2. Check API key has sufficient credits/quota
3. Run `python health_check.py` to diagnose

---

## License

MIT License - see LICENSE file

---

## Disclaimer

This software is for educational and research purposes only. It is not financial advice. Trading cryptocurrency carries significant risk. The developers are not responsible for any financial losses incurred through use of this software. Always do your own research and consider consulting a financial advisor.
