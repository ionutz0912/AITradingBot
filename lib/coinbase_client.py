"""
Coinbase Advanced Trade API client for trading bot.

Implements the same interface as BitunixFutures for compatibility.
Documentation: https://docs.cdp.coinbase.com/advanced-trade/docs/welcome
SDK: https://github.com/coinbase/coinbase-advanced-py
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from coinbase.rest import RESTClient


class CoinbaseError(Exception):
    """Coinbase API error."""
    pass


@dataclass
class CoinbasePosition:
    """
    Position data structure matching bot interface.

    For spot trading, a "position" is simply a non-zero balance.
    """
    positionId: str  # account UUID
    symbol: str      # e.g., "BTC-USD"
    qty: float       # amount held
    side: str        # "buy" for long (spot only supports long)
    avgOpenPrice: float  # Not tracked in spot, set to 0


# Symbol mapping: Internal format -> Coinbase format
SYMBOL_MAP = {
    "BTCUSDT": "BTC-USD",
    "ETHUSDT": "ETH-USD",
    "SOLUSDT": "SOL-USD",
    "XRPUSDT": "XRP-USD",
    "ADAUSDT": "ADA-USD",
    "DOGEUSDT": "DOGE-USD",
    "DOTUSDT": "DOT-USD",
    "AVAXUSDT": "AVAX-USD",
    "LINKUSDT": "LINK-USD",
    "MATICUSDT": "MATIC-USD",
    # Add more as needed
}

# Reverse mapping for lookups
SYMBOL_MAP_REVERSE = {v: k for k, v in SYMBOL_MAP.items()}


def to_coinbase_symbol(symbol: str) -> str:
    """Convert internal symbol format to Coinbase format."""
    return SYMBOL_MAP.get(symbol, symbol)


def from_coinbase_symbol(symbol: str) -> str:
    """Convert Coinbase symbol format to internal format."""
    return SYMBOL_MAP_REVERSE.get(symbol, symbol)


class CoinbaseAdvanced:
    """
    Coinbase Advanced Trade API client.

    Implements same interface as BitunixFutures for compatibility with the trading bot.

    Note: Coinbase spot trading does NOT support:
    - Short selling (bearish signals will close positions instead)
    - Leverage
    - Margin modes
    """

    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize Coinbase client.

        Args:
            api_key: Coinbase API key
            api_secret: Coinbase API secret (PEM format, can have escaped newlines)
        """
        if not api_key or not api_secret:
            raise CoinbaseError("Coinbase API key and secret are required")

        # Convert escaped newlines to actual newlines (for .env file compatibility)
        if "\\n" in api_secret:
            api_secret = api_secret.replace("\\n", "\n")

        try:
            self.client = RESTClient(api_key=api_key, api_secret=api_secret)
            logging.info("Coinbase client initialized")
        except Exception as e:
            raise CoinbaseError(f"Failed to initialize Coinbase client: {e}")

        # Cache for account UUIDs
        self._account_cache: dict[str, str] = {}

    def _get_account_uuid(self, currency: str) -> str | None:
        """Get account UUID for a currency."""
        if currency in self._account_cache:
            return self._account_cache[currency]

        try:
            response = self.client.get_accounts()
            # SDK returns object with .accounts attribute
            accounts = response.accounts if hasattr(response, 'accounts') else response.get("accounts", [])
            for account in accounts:
                acc_currency = account.get("currency") if isinstance(account, dict) else account.currency
                if acc_currency == currency:
                    acc_uuid = account.get("uuid") if isinstance(account, dict) else account.uuid
                    self._account_cache[currency] = acc_uuid
                    return acc_uuid
        except Exception as e:
            logging.error(f"Failed to get account UUID for {currency}: {e}")

        return None

    def get_account_balance(self, currency: str = "USD") -> float:
        """
        Get available balance for currency.

        Args:
            currency: Currency code (e.g., "USD", "BTC")

        Returns:
            Available balance as float
        """
        # Map USDT to USD for Coinbase
        if currency == "USDT":
            currency = "USD"

        try:
            response = self.client.get_accounts()
            # SDK returns object with .accounts attribute
            accounts = response.accounts if hasattr(response, 'accounts') else response.get("accounts", [])
            for account in accounts:
                acc_currency = account.get("currency") if isinstance(account, dict) else account.currency
                if acc_currency == currency:
                    if isinstance(account, dict):
                        available = account.get("available_balance", {})
                        return float(available.get("value", 0))
                    else:
                        return float(account.available_balance.get("value", 0))
            return 0.0
        except Exception as e:
            logging.error(f"Failed to get balance for {currency}: {e}")
            raise CoinbaseError(f"Failed to get balance: {e}")

    def get_pending_positions(
        self,
        symbol: str,
        position_id: str | None = None
    ) -> CoinbasePosition | None:
        """
        Get open position for symbol.

        For spot trading, a "position" is a non-zero balance of the base asset.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT" or "BTC-USD")
            position_id: Ignored for spot trading

        Returns:
            CoinbasePosition if position exists, None otherwise
        """
        # Convert symbol and extract base currency
        cb_symbol = to_coinbase_symbol(symbol)
        base_currency = cb_symbol.split("-")[0]  # "BTC-USD" -> "BTC"

        try:
            response = self.client.get_accounts()
            # SDK returns object with .accounts attribute
            accounts = response.accounts if hasattr(response, 'accounts') else response.get("accounts", [])
            for account in accounts:
                acc_currency = account.get("currency") if isinstance(account, dict) else account.currency
                if acc_currency == base_currency:
                    if isinstance(account, dict):
                        available = account.get("available_balance", {})
                        qty = float(available.get("value", 0))
                        acc_uuid = account.get("uuid", "")
                    else:
                        qty = float(account.available_balance.get("value", 0))
                        acc_uuid = account.uuid

                    # Only return position if we have a meaningful balance
                    if qty > 0.0000001:  # Small threshold to ignore dust
                        return CoinbasePosition(
                            positionId=acc_uuid,
                            symbol=cb_symbol,
                            qty=qty,
                            side="buy",  # Spot is always "long"
                            avgOpenPrice=0.0  # Not tracked in spot
                        )
            return None
        except Exception as e:
            logging.error(f"Failed to get position for {symbol}: {e}")
            raise CoinbaseError(f"Failed to get position: {e}")

    def get_current_price(self, symbol: str) -> float:
        """
        Get current market price for symbol.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT" or "BTC-USD")

        Returns:
            Current price as float
        """
        cb_symbol = to_coinbase_symbol(symbol)

        try:
            product = self.client.get_product(product_id=cb_symbol)
            return float(product.get("price", 0))
        except Exception as e:
            logging.error(f"Failed to get price for {symbol}: {e}")
            raise CoinbaseError(f"Failed to get price: {e}")

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float | None = None,
        quote_size: float | None = None,
        order_type: str = "MARKET"
    ) -> dict[str, Any]:
        """
        Place a market order.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT" or "BTC-USD")
            side: "buy" or "sell"
            qty: Base asset quantity (e.g., 0.001 BTC)
            quote_size: Quote currency amount (e.g., 100 USD)
            order_type: Order type (only "MARKET" supported currently)

        Returns:
            Order response dict
        """
        cb_symbol = to_coinbase_symbol(symbol)
        client_order_id = str(uuid.uuid4())

        # Build order configuration
        if side.upper() == "BUY":
            if quote_size:
                # Buy with USD amount
                order_config = {
                    "market_market_ioc": {
                        "quote_size": str(quote_size)
                    }
                }
            elif qty:
                # Buy specific amount of base asset
                order_config = {
                    "market_market_ioc": {
                        "base_size": str(qty)
                    }
                }
            else:
                raise CoinbaseError("Either qty or quote_size must be provided")
        else:  # SELL
            if not qty:
                raise CoinbaseError("qty is required for sell orders")
            order_config = {
                "market_market_ioc": {
                    "base_size": str(qty)
                }
            }

        try:
            logging.info(f"Placing {side} order for {cb_symbol}: qty={qty}, quote_size={quote_size}")

            response = self.client.create_order(
                client_order_id=client_order_id,
                product_id=cb_symbol,
                side=side.upper(),
                order_configuration=order_config
            )

            logging.info(f"Order placed: {response}")
            return response

        except Exception as e:
            logging.error(f"Failed to place order: {e}")
            raise CoinbaseError(f"Failed to place order: {e}")

    def flash_close_position(self, position_id: str) -> dict[str, Any]:
        """
        Close position immediately at market price.

        For spot trading, this sells all holdings of the base asset.

        Args:
            position_id: Account UUID (from CoinbasePosition.positionId)

        Returns:
            Order response dict
        """
        try:
            # Get account details to find currency and balance
            account = self.client.get_account(account_uuid=position_id)
            currency = account.get("currency", "")
            available = account.get("available_balance", {})
            qty = float(available.get("value", 0))

            if qty <= 0:
                logging.warning(f"No balance to close for account {position_id}")
                return {"status": "no_balance"}

            # Construct symbol (assume USD quote)
            symbol = f"{currency}-USD"

            logging.info(f"Closing position: selling {qty} {currency}")

            return self.place_order(
                symbol=symbol,
                side="sell",
                qty=qty
            )

        except Exception as e:
            logging.error(f"Failed to close position: {e}")
            raise CoinbaseError(f"Failed to close position: {e}")

    def set_leverage(self, symbol: str, leverage: int) -> None:
        """
        Set leverage for symbol.

        Note: Coinbase spot trading does not support leverage.
        This method is a no-op for compatibility.
        """
        if leverage != 1:
            logging.warning(f"Coinbase spot does not support leverage. Ignoring leverage={leverage}")

    def set_margin_mode(self, symbol: str, mode: str) -> None:
        """
        Set margin mode for symbol.

        Note: Coinbase spot trading does not support margin modes.
        This method is a no-op for compatibility.
        """
        logging.debug(f"Coinbase spot does not support margin modes. Ignoring mode={mode}")

    def get_trading_pairs(self, symbols: list[str] | None = None) -> list[dict]:
        """
        Get available trading pairs.

        Args:
            symbols: Optional list of symbols to filter

        Returns:
            List of product info dicts
        """
        try:
            products = self.client.get_products()
            product_list = products.get("products", [])

            if symbols:
                cb_symbols = [to_coinbase_symbol(s) for s in symbols]
                product_list = [p for p in product_list if p.get("product_id") in cb_symbols]

            return product_list
        except Exception as e:
            logging.error(f"Failed to get trading pairs: {e}")
            raise CoinbaseError(f"Failed to get trading pairs: {e}")
