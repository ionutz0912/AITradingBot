# AI Trading Bot - Development Progress

## Project Overview

AI-powered cryptocurrency trading bot with multi-provider AI support and Coinbase exchange integration.

---

## Features

### AI Providers
| Provider | Config Value | Model | Status |
|----------|--------------|-------|--------|
| **Anthropic (Claude)** | `anthropic` | `claude-sonnet-4-20250514` | ✅ Working |
| **xAI (Grok)** | `xai` or `grok` | `grok-3-latest` | ✅ Working |
| **DeepSeek** | `deepseek` | `deepseek-chat` | ✅ Available |

### Exchange Providers
| Provider | Config Value | Type | Status |
|----------|--------------|------|--------|
| **Coinbase** | `coinbase` | Spot | ✅ Working |
| **Bitunix** | `bitunix` | Futures | ✅ Available |

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

### 3. Run
```bash
python3 runner.py
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

### Coinbase API Key Setup
1. Go to **https://cloud.coinbase.com/access/api** (NOT coinbase.com/settings/api)
2. Create new API key with `view` and `trade` permissions
3. Download the key and PEM secret
4. In `.env`, use `\n` for newlines in the PEM secret
5. Remove any IP whitelist restrictions (or add your IP)

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
├── runner.py                 # Main trading bot
├── runner_with_discord.py    # Bot with Discord notifications
├── requirements.txt          # Python dependencies
├── .env.template             # Environment template
├── .env                      # Your config (gitignored)
├── lib/
│   ├── ai.py                 # Multi-provider AI module
│   ├── coinbase_client.py    # Coinbase exchange client
│   ├── bitunix.py            # Bitunix exchange client
│   ├── forward_tester.py     # Simulated trading
│   ├── custom_helpers.py     # Trading helpers
│   └── discord_notifications.py  # Discord webhook
├── PROGRESS.md               # This file
└── TODO_COINBASE.md          # Coinbase implementation notes
```

---

## Testing

### Forward Testing (Simulated)
Edit `runner.py`:
```python
FORWARD_TESTING_CONFIG = {
    "run_name": RUN_NAME,
    "initial_capital": 10000,
    "fees": 0.0006,
}
```

### Live Trading
Edit `runner.py`:
```python
FORWARD_TESTING_CONFIG = None
```

---

## Completed Work

- [x] Security analysis of original codebase
- [x] Multi-provider AI support (Anthropic, xAI, DeepSeek)
- [x] Coinbase Advanced Trade API integration
- [x] Python 3.9 compatibility fixes
- [x] Discord notifications module (was missing)
- [x] Forward testing mode
- [x] Exchange provider selection
- [x] Spot trading support (handles no-shorting gracefully)
- [x] PEM secret newline handling for .env files

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

---

## Security Notes

- Never commit `.env` files (already in `.gitignore`)
- Rotate API keys if exposed
- Use forward testing before live trading
- Start with small position sizes ($5-20)
- Monitor bot activity regularly
- Coinbase CDP keys use PEM format - keep private

---

*Last Updated: 2026-02-03*
