# AI Trading Bot - Development Guide

This document provides context for AI assistants working on this codebase.

## Project Overview

AI-powered cryptocurrency trading bot with multi-provider AI support (Claude, Grok, DeepSeek), multi-exchange integration (Coinbase, Bitunix), and real-time monitoring dashboard.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   runner_*.py   │────▶│     lib/*.py    │────▶│   Exchanges     │
│   (Entry Point) │     │   (Core Logic)  │     │ Coinbase/Bitunix│
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        │                       ▼
        │               ┌─────────────────┐
        │               │  AI Providers   │
        │               │ Claude/Grok/DS  │
        │               └─────────────────┘
        │
        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    dashboard/   │────▶│ Notifications   │────▶│    Database     │
│  (Flask Web UI) │     │ Discord/Telegram│     │ SQLite (WAL)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        │                                               │
        └───────────────────┬───────────────────────────┘
                            ▼
                  ┌─────────────────┐
                  │   Simulation    │
                  │   Manager       │
                  │  (Up to 5)      │
                  └─────────────────┘
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `lib/ai.py` | Multi-provider AI integration (Anthropic, xAI, DeepSeek) |
| `lib/coinbase_client.py` | Coinbase Advanced Trade API client |
| `lib/bitunix.py` | Bitunix futures exchange client |
| `lib/forward_tester.py` | Paper trading simulation |
| `lib/market_data.py` | Real-time price fetching (CoinGecko, Coinbase, Binance) |
| `lib/performance_tracker.py` | P&L and trade history tracking |
| `lib/config.py` | Pydantic-based configuration management |
| `lib/discord_notifications.py` | Discord webhook notifications |
| `lib/telegram_notifications.py` | Telegram Bot API notifications |
| `lib/database.py` | SQLite database with WAL mode (simulations, notifications) |
| `lib/notification_service.py` | Notification service for managing Telegram notifications |
| `lib/simulation_manager.py` | Manages up to 5 parallel trading simulations |
| `lib/simulation_worker.py` | Worker process for running individual simulations |
| `dashboard/` | Flask-based web monitoring dashboard |
| `dashboard/routes/simulations.py` | API endpoints for simulation management |
| `dashboard/routes/notifications.py` | API endpoints for notification management |

## Configuration

- **Environment**: `.env` file for secrets (API keys, tokens)
- **Trading Config**: `configs/config.json` for trading parameters
- **Never commit**: `.env` files or any API keys/secrets

## Code Conventions

### Python Style
- Python 3.9+ required
- Type hints for function signatures
- Docstrings for public functions
- Logging over print statements
- Pydantic models for configuration

### Error Handling
- Use custom exception classes (e.g., `CoinbaseError`, `BitunixError`)
- Log errors with context before raising
- Graceful degradation for optional features (notifications, dashboard)

### Testing
- Test files in `tests/` directory
- Run with `python -m pytest tests/`
- Forward testing mode for safe trade simulation

## Common Tasks

### Adding a New AI Provider
1. Add provider class in `lib/ai.py`
2. Update `AI_PROVIDERS` dict
3. Add API key handling in `.env.template`
4. Update config validation

### Adding a New Exchange
1. Create client module in `lib/` (follow `coinbase_client.py` pattern)
2. Implement required methods: `get_balance()`, `place_order()`, `get_position()`
3. Add to runner switching logic
4. Update config options

### Adding Notification Channel
1. Create notifier class in `lib/` (follow `telegram_notifications.py` pattern)
2. Implement `send_notification()`, `send_trade_opened()`, `send_trade_closed()`
3. Add config options in `lib/config.py`
4. Integrate in `runner_multi.py`

### Dashboard Development
1. Routes in `dashboard/routes/` (api.py for JSON, views.py for HTML)
2. Data aggregation in `dashboard/services/data_service.py`
3. Templates in `dashboard/templates/`
4. Run with `python3 run_dashboard.py --debug --port 5001`

### Working with Simulations
1. Database schema in `lib/database.py` (simulations, simulation_trades tables)
2. Simulation manager in `lib/simulation_manager.py` (orchestration, max 5 concurrent)
3. Simulation worker in `lib/simulation_worker.py` (individual simulation process)
4. API routes in `dashboard/routes/simulations.py`
5. States: created → running → paused/stopped/completed/error
6. Each simulation runs in isolated process for stability

## Environment Variables

Required:
- `AI_PROVIDER` - AI provider selection
- `ANTHROPIC_API_KEY` / `XAI_API_KEY` / `DEEPSEEK_API_KEY` - AI API key
- `EXCHANGE_PROVIDER` - Exchange selection
- `COINBASE_API_KEY` / `COINBASE_API_SECRET` - Exchange credentials

Optional:
- `DISCORD_WEBHOOK_URL` - Discord notifications
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` - Telegram notifications

## Data Directories

| Directory | Purpose |
|-----------|---------|
| `configs/` | Trading configuration files |
| `data/` | SQLite database (simulations, notifications) |
| `logs/` | Execution logs |
| `ai_responses/` | AI response history for analysis |
| `performance_data/` | Trade history and metrics |

## Safety Guidelines

1. **Never commit secrets** - Check `.gitignore` before commits
2. **Use forward testing** - Test strategies without real capital first
3. **Start small** - Use minimal position sizes ($5-20) initially
4. **Monitor actively** - Check dashboard and logs regularly
5. **Handle API errors** - All exchange calls should have error handling
