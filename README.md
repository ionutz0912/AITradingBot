# AI Trading Bot

AI-powered cryptocurrency trading bot with multi-provider AI support and multi-exchange integration.

## Features

- **Multi-Provider AI Support**: Anthropic Claude, xAI Grok, DeepSeek
- **Multi-Exchange Support**: Coinbase (spot), Bitunix (futures)
- **Multi-Symbol Trading**: Trade multiple cryptocurrencies from a single config
- **Real-Time Market Data**: Fetches prices from CoinGecko, Coinbase, Binance
- **Performance Tracking**: Track P&L, win rate, and trade history
- **Forward Testing**: Simulate trades without risking real capital
- **Simulation Management**: Run up to 5 parallel trading simulations with start/stop/pause controls
- **Database Integration**: SQLite with WAL mode for reliable data persistence
- **Web Dashboard**: Real-time monitoring with Flask-based web interface
- **Discord Notifications**: Get alerts for trade signals
- **Telegram Notifications**: Get alerts via Telegram Bot API with notification history
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

# Optional - Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Optional - Telegram (get from @BotFather)
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
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather |
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

## Web Dashboard

Monitor your trading bot in real-time with the built-in web dashboard.

### Start the Dashboard

```bash
# Basic usage (localhost:5000)
python3 run_dashboard.py

# Custom port (useful if 5000 is in use by AirPlay on macOS)
python3 run_dashboard.py --port 5001

# Allow external connections
python3 run_dashboard.py --host 0.0.0.0

# Debug mode
python3 run_dashboard.py --debug

# Disable simulations (for testing)
python3 run_dashboard.py --no-simulations
```

Access the dashboard at `http://127.0.0.1:5000` (or your chosen port).

### Dashboard Pages

#### Main Dashboard (`/`)
- **Status Overview**: Bot configuration, mode, enabled symbols
- **Performance Metrics**: P&L, win rate, total trades
- **Trade History**: Recent trades with entry/exit prices
- **Market Data**: Real-time prices for enabled symbols
- **Open Positions**: Current positions with P&L
- **AI History**: Recent AI interpretations and reasoning
- **Fear & Greed Index**: Market sentiment indicator
- **Account Balance**: Current account balance

#### Simulations Page (`/simulations`)
- **Simulation Management**: Start, stop, pause, and resume up to 5 parallel simulations
- **Real-time Monitoring**: Live status, P&L, and trade count for each simulation
- **Configuration**: Customize symbol, position size, and strategy for each simulation
- **Performance Tracking**: View individual simulation metrics and statistics

#### Notifications Page (`/notifications`)
- **Notification History**: View all sent Telegram notifications
- **Settings**: Configure Telegram bot token and chat ID
- **Test Notifications**: Send test messages to verify configuration
- **Filter & Search**: Filter notifications by type and search by content

### API Endpoints

#### Core Endpoints
| Endpoint | Description |
|----------|-------------|
| `/api/status` | Bot configuration and status |
| `/api/metrics` | Performance metrics |
| `/api/trades` | Recent trade history |
| `/api/market` | Live market prices |
| `/api/positions` | Current open positions |
| `/api/ai-history` | Recent AI interpretations |
| `/api/fear-greed` | Fear & Greed Index |
| `/api/balance` | Account balance |
| `/api/summary` | Combined summary (all data) |

#### Simulation Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/simulations` | GET | List all simulations |
| `/api/simulations` | POST | Create new simulation |
| `/api/simulations/<id>` | GET | Get simulation details |
| `/api/simulations/<id>` | DELETE | Delete simulation |
| `/api/simulations/<id>/start` | POST | Start simulation |
| `/api/simulations/<id>/stop` | POST | Stop simulation |
| `/api/simulations/<id>/pause` | POST | Pause simulation |
| `/api/simulations/<id>/resume` | POST | Resume simulation |

#### Notification Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notifications` | GET | List notification history |
| `/api/notifications/settings` | GET | Get notification settings |
| `/api/notifications/settings` | POST | Update notification settings |
| `/api/notifications/test` | POST | Send test notification |

---

## Simulation Management

Run multiple trading simulations in parallel to test different strategies, symbols, and configurations.

### Features

- **Parallel Simulations**: Run up to 5 simulations concurrently
- **Process Isolation**: Each simulation runs in its own process for stability
- **Real-time Control**: Start, stop, pause, and resume simulations on-the-fly
- **Performance Tracking**: Monitor P&L, trade count, and win rate for each simulation
- **Persistent Storage**: Simulation data stored in SQLite database

### Using Simulations

#### Via Web Dashboard

1. Navigate to `http://127.0.0.1:5001/simulations`
2. Click "Create New Simulation"
3. Configure:
   - **Symbol**: Trading pair (e.g., BTCUSDT, ETHUSDT)
   - **Position Size**: Amount per trade (e.g., $5)
   - **AI Provider**: anthropic, xai, or deepseek
   - **Exchange**: coinbase or bitunix
4. Click "Start" to begin the simulation
5. Monitor real-time progress and statistics
6. Use "Pause", "Resume", or "Stop" controls as needed

#### Via API

```bash
# Create simulation
curl -X POST http://127.0.0.1:5001/api/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "position_size": 5.0,
    "ai_provider": "anthropic",
    "exchange_provider": "coinbase"
  }'

# Start simulation
curl -X POST http://127.0.0.1:5001/api/simulations/sim_123/start

# Pause simulation
curl -X POST http://127.0.0.1:5001/api/simulations/sim_123/pause

# Resume simulation
curl -X POST http://127.0.0.1:5001/api/simulations/sim_123/resume

# Stop simulation
curl -X POST http://127.0.0.1:5001/api/simulations/sim_123/stop

# Get simulation status
curl http://127.0.0.1:5001/api/simulations/sim_123

# List all simulations
curl http://127.0.0.1:5001/api/simulations
```

### Simulation States

| State | Description |
|-------|-------------|
| `created` | Simulation created but not started |
| `running` | Actively executing trades |
| `paused` | Temporarily paused, can be resumed |
| `stopped` | Stopped, cannot be restarted |
| `completed` | Finished successfully |
| `error` | Encountered an error |

### Database Schema

Simulations are stored in `data/trading_bot.db` with the following tables:

- **simulations**: Simulation configuration and state
- **simulation_trades**: Individual trades per simulation
- **notifications**: Notification history

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
├── run_dashboard.py         # Web dashboard entry point
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
│   ├── discord_notifications.py  # Discord alerts
│   ├── telegram_notifications.py # Telegram alerts
│   ├── database.py          # SQLite database management
│   ├── notification_service.py   # Notification service
│   ├── simulation_manager.py     # Simulation orchestration
│   └── simulation_worker.py      # Simulation worker process
├── dashboard/               # Web dashboard
│   ├── app.py               # Flask application factory
│   ├── routes/              # API and view routes
│   │   ├── api.py           # Core API endpoints
│   │   ├── views.py         # HTML page routes
│   │   ├── simulations.py   # Simulation management API
│   │   └── notifications.py # Notification management API
│   ├── services/            # Data aggregation services
│   ├── templates/           # HTML templates
│   │   ├── index.html       # Main dashboard
│   │   ├── simulations.html # Simulations page
│   │   └── notifications.html # Notifications page
│   └── static/              # CSS, JS assets
│       └── js/
│           ├── dashboard.js      # Main dashboard JS
│           ├── simulations.js    # Simulations page JS
│           └── notifications.js  # Notifications page JS
├── configs/                 # Configuration files
├── data/                    # SQLite database directory
├── logs/                    # Execution logs
├── ai_responses/            # AI response history
└── performance_data/        # Trade history
```

---

## Notifications

### Discord Setup

1. Create a webhook in your Discord server (Server Settings → Integrations → Webhooks)
2. Copy the webhook URL to `.env`:
   ```env
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```
3. Enable in config.json:
   ```json
   {
     "discord_enabled": true,
     "discord_include_reasoning": false
   }
   ```

### Telegram Setup

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Copy the bot token
3. Start a chat with your bot and send any message
4. Get your chat ID by visiting: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
5. Add to `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```
6. Enable in config.json:
   ```json
   {
     "telegram_enabled": true,
     "telegram_include_reasoning": false
   }
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
