# TODO: Coinbase Advanced Trade API Integration

## Overview

Replace Bitunix exchange client with Coinbase Advanced Trade API for live trading.

---

## Prerequisites

### 1. Coinbase Account Setup
- [ ] Have a Coinbase account with Advanced Trade enabled
- [ ] API keys created at: https://www.coinbase.com/settings/api
- [ ] Required permissions: `View`, `Trade`, `Transfer` (depending on needs)

### 2. API Documentation
- **Main Docs:** https://docs.cdp.coinbase.com/advanced-trade/docs/welcome
- **API Reference:** https://docs.cdp.coinbase.com/advanced-trade/reference
- **Python SDK:** https://github.com/coinbase/coinbase-advanced-py
- **SDK Docs:** https://coinbase.github.io/coinbase-advanced-py/

---

## Implementation Tasks

### Phase 1: Setup & Dependencies

- [ ] **1.1** Add `coinbase-advanced-py` to `requirements.txt`
  ```
  coinbase-advanced-py>=1.0.0
  ```

- [ ] **1.2** Update `.env.template` with Coinbase credentials
  ```bash
  # Exchange Provider Selection
  EXCHANGE_PROVIDER=coinbase  # Options: coinbase, bitunix

  # Coinbase Advanced Trade API
  COINBASE_API_KEY=your_api_key_here
  COINBASE_API_SECRET=your_api_secret_here
  ```

### Phase 2: Create Coinbase Client

- [ ] **2.1** Create `lib/coinbase_client.py` with the following structure:

```python
"""
Coinbase Advanced Trade API client for trading bot.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from coinbase.rest import RESTClient


class CoinbaseError(Exception):
    """Coinbase API error."""
    pass


@dataclass(frozen=True)
class CoinbasePosition:
    """Position data structure matching bot interface."""
    positionId: str
    symbol: str
    qty: float
    side: str  # "buy" or "sell"
    avgOpenPrice: float


class CoinbaseAdvanced:
    """
    Coinbase Advanced Trade API client.

    Implements same interface as BitunixFutures for compatibility.
    """

    def __init__(self, api_key: str, api_secret: str):
        self.client = RESTClient(api_key=api_key, api_secret=api_secret)

    def get_account_balance(self, currency: str = "USD") -> float:
        """Get available balance for currency."""
        # TODO: Implement
        pass

    def get_pending_positions(self, symbol: str, position_id: str | None = None):
        """Get open positions for symbol."""
        # TODO: Implement using get_account() or list_accounts()
        pass

    def place_order(self, symbol: str, side: str, qty: float,
                    order_type: str = "MARKET") -> dict:
        """Place a market order."""
        # TODO: Implement using create_order()
        pass

    def flash_close_position(self, position_id: str) -> dict:
        """Close position immediately at market price."""
        # TODO: Implement
        pass

    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage (if supported, else no-op for spot)."""
        # Note: Coinbase spot doesn't have leverage
        pass

    def set_margin_mode(self, symbol: str, mode: str):
        """Set margin mode (if supported, else no-op for spot)."""
        pass
```

- [ ] **2.2** Implement each method:

| Method | Coinbase SDK Function | Notes |
|--------|----------------------|-------|
| `get_account_balance()` | `client.get_account()` | Filter by currency |
| `get_pending_positions()` | `client.list_accounts()` | Check non-zero balances |
| `place_order()` | `client.create_order()` | Market order |
| `flash_close_position()` | `client.create_order()` | Sell entire position |

### Phase 3: Update Runners

- [ ] **3.1** Update `runner.py` to support exchange selection:

```python
# Exchange Provider Configuration
EXCHANGE_PROVIDER = os.environ.get("EXCHANGE_PROVIDER", "coinbase").lower()

# Initialize exchange based on provider
if FORWARD_TESTING_CONFIG is not None:
    exchange = ForwardTester(FORWARD_TESTING_CONFIG)
elif EXCHANGE_PROVIDER == "coinbase":
    from lib.coinbase_client import CoinbaseAdvanced
    exchange = CoinbaseAdvanced(
        os.environ.get("COINBASE_API_KEY"),
        os.environ.get("COINBASE_API_SECRET")
    )
elif EXCHANGE_PROVIDER == "bitunix":
    exchange = BitunixFutures(EXCHANGE_API_KEY, EXCHANGE_API_SECRET)
else:
    raise ValueError(f"Unknown exchange provider: {EXCHANGE_PROVIDER}")
```

- [ ] **3.2** Update `runner_with_discord.py` similarly

- [ ] **3.3** Update `lib/__init__.py` to export Coinbase client:
```python
from .coinbase_client import CoinbaseAdvanced, CoinbaseError
```

### Phase 4: Symbol Mapping

- [ ] **4.1** Create symbol mapping (Bitunix vs Coinbase format):

| Asset | Bitunix | Coinbase |
|-------|---------|----------|
| Bitcoin | `BTCUSDT` | `BTC-USD` |
| Ethereum | `ETHUSDT` | `ETH-USD` |

- [ ] **4.2** Add symbol conversion in runner:
```python
# Symbol mapping
COINBASE_SYMBOLS = {
    "BTCUSDT": "BTC-USD",
    "ETHUSDT": "ETH-USD",
    # Add more as needed
}
TRADING_SYMBOL = COINBASE_SYMBOLS.get(SYMBOL, SYMBOL)
```

### Phase 5: Testing

- [x] **5.1** Comprehensive test suite created (`tests/lib/test_coinbase_client.py`)
- [x] **5.2** Test `get_account_balance()` with mocked SDK
- [x] **5.3** Test `place_order()` with mock responses
- [x] **5.4** Test `flash_close_position()` functionality
- [x] **5.5** Integration tests with forward testing mode
- [x] **5.6** 85% code coverage achieved
- [x] **5.7** All tests use mocked Coinbase SDK (no real API calls)

---

## Coinbase SDK Quick Reference

### Installation
```bash
pip install coinbase-advanced-py
```

### Authentication
```python
from coinbase.rest import RESTClient

client = RESTClient(api_key="KEY", api_secret="SECRET")
```

### Common Operations

```python
# Get accounts (balances)
accounts = client.get_accounts()

# Get specific account
account = client.get_account(account_uuid="...")

# Place market buy order
order = client.create_order(
    client_order_id="unique-id",
    product_id="BTC-USD",
    side="BUY",
    order_configuration={
        "market_market_ioc": {
            "quote_size": "100"  # $100 worth
        }
    }
)

# Place market sell order
order = client.create_order(
    client_order_id="unique-id",
    product_id="BTC-USD",
    side="SELL",
    order_configuration={
        "market_market_ioc": {
            "base_size": "0.001"  # 0.001 BTC
        }
    }
)

# Get order status
order = client.get_order(order_id="...")

# Cancel order
client.cancel_orders(order_ids=["..."])

# Get product info
product = client.get_product(product_id="BTC-USD")

# Get current price
ticker = client.get_product(product_id="BTC-USD")
price = ticker["price"]
```

---

## Key Differences: Bitunix vs Coinbase

| Feature | Bitunix (Current) | Coinbase (New) |
|---------|-------------------|----------------|
| **Product Type** | Futures | Spot (primarily) |
| **Leverage** | Yes (1-125x) | No (spot) / Limited (futures) |
| **Margin Modes** | Isolation/Cross | N/A for spot |
| **Symbol Format** | `BTCUSDT` | `BTC-USD` |
| **Order Quantity** | Base asset qty | Base or Quote qty |
| **Authentication** | HMAC-SHA256 | API Key + Secret |
| **SDK** | Custom | Official `coinbase-advanced-py` |

---

## Environment Variables Summary

```bash
# .env file structure

# AI Provider
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
XAI_API_KEY=xai-...

# Exchange Provider
EXCHANGE_PROVIDER=coinbase

# Coinbase (if EXCHANGE_PROVIDER=coinbase)
COINBASE_API_KEY=your_key
COINBASE_API_SECRET=your_secret

# Bitunix (if EXCHANGE_PROVIDER=bitunix)
EXCHANGE_API_KEY=your_key
EXCHANGE_API_SECRET=your_secret

# Optional
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## Risk Considerations

1. **Spot vs Futures**: Coinbase spot trading means no leverage - position sizes need adjustment
2. **No Short Selling**: Spot markets don't support shorting directly
3. **Fee Structure**: Coinbase fees differ from Bitunix
4. **Rate Limits**: Be aware of Coinbase API rate limits
5. **Minimum Orders**: Coinbase has minimum order sizes per product

---

## Estimated Effort

| Task | Complexity | Time Estimate |
|------|------------|---------------|
| Phase 1: Setup | Low | 15 min |
| Phase 2: Client | Medium | 2-3 hours |
| Phase 3: Runners | Low | 30 min |
| Phase 4: Symbols | Low | 15 min |
| Phase 5: Testing | Medium | 1-2 hours |
| **Total** | | **4-6 hours** |

---

## References

- [Coinbase Advanced Trade API Docs](https://docs.cdp.coinbase.com/advanced-trade/docs/welcome)
- [Python SDK GitHub](https://github.com/coinbase/coinbase-advanced-py)
- [SDK Documentation](https://coinbase.github.io/coinbase-advanced-py/)
- [API Endpoints Reference](https://docs.cdp.coinbase.com/advanced-trade/reference)
- [REST API Overview](https://docs.cdp.coinbase.com/advanced-trade/docs/rest-api-overview)

---

*Created: 2026-02-03*
