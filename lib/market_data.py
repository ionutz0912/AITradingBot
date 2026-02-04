"""
Market Data Module for AI Trading Bot

Fetches real-time and historical market data from multiple sources:
- CoinGecko (free, no API key required)
- Coinbase public API
- Binance public API (fallback)

Provides price data for enhanced AI prompts.
"""

import logging
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class MarketData:
    """Market data for a cryptocurrency."""
    symbol: str
    price: float
    price_change_24h: float
    price_change_24h_percent: float
    high_24h: float
    low_24h: float
    volume_24h: float
    market_cap: Optional[float] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class MarketDataError(Exception):
    """Exception raised for market data fetch errors."""
    pass


# CoinGecko ID mapping for common symbols
COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "SHIB": "shiba-inu",
    "LTC": "litecoin",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XLM": "stellar",
}


def normalize_symbol(symbol: str) -> str:
    """Extract base symbol from trading pair (e.g., BTCUSDT -> BTC)."""
    symbol = symbol.upper()
    for suffix in ["USDT", "USD", "USDC", "BUSD", "-USD", "-USDT"]:
        if symbol.endswith(suffix):
            return symbol[:-len(suffix)]
    return symbol


def get_coingecko_data(symbol: str) -> Optional[MarketData]:
    """Fetch market data from CoinGecko (free, no API key)."""
    base_symbol = normalize_symbol(symbol)
    coin_id = COINGECKO_IDS.get(base_symbol)

    if not coin_id:
        logging.warning(f"Unknown CoinGecko ID for symbol: {base_symbol}")
        return None

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        market = data.get("market_data", {})

        return MarketData(
            symbol=base_symbol,
            price=market.get("current_price", {}).get("usd", 0),
            price_change_24h=market.get("price_change_24h", 0),
            price_change_24h_percent=market.get("price_change_percentage_24h", 0),
            high_24h=market.get("high_24h", {}).get("usd", 0),
            low_24h=market.get("low_24h", {}).get("usd", 0),
            volume_24h=market.get("total_volume", {}).get("usd", 0),
            market_cap=market.get("market_cap", {}).get("usd")
        )

    except requests.RequestException as e:
        logging.warning(f"CoinGecko request failed: {e}")
        return None


def get_coinbase_price(symbol: str) -> Optional[MarketData]:
    """Fetch market data from Coinbase public API."""
    base_symbol = normalize_symbol(symbol)
    product_id = f"{base_symbol}-USD"

    url = f"https://api.exchange.coinbase.com/products/{product_id}/stats"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        current_price = float(data.get("last", 0))
        open_price = float(data.get("open", 0))
        change = current_price - open_price if open_price else 0
        change_percent = (change / open_price * 100) if open_price else 0

        return MarketData(
            symbol=base_symbol,
            price=current_price,
            price_change_24h=change,
            price_change_24h_percent=change_percent,
            high_24h=float(data.get("high", 0)),
            low_24h=float(data.get("low", 0)),
            volume_24h=float(data.get("volume", 0)) * current_price  # Convert to USD
        )

    except requests.RequestException as e:
        logging.warning(f"Coinbase request failed: {e}")
        return None


def get_binance_price(symbol: str) -> Optional[MarketData]:
    """Fetch market data from Binance public API (fallback)."""
    base_symbol = normalize_symbol(symbol)
    binance_symbol = f"{base_symbol}USDT"

    url = "https://api.binance.com/api/v3/ticker/24hr"
    params = {"symbol": binance_symbol}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        return MarketData(
            symbol=base_symbol,
            price=float(data.get("lastPrice", 0)),
            price_change_24h=float(data.get("priceChange", 0)),
            price_change_24h_percent=float(data.get("priceChangePercent", 0)),
            high_24h=float(data.get("highPrice", 0)),
            low_24h=float(data.get("lowPrice", 0)),
            volume_24h=float(data.get("quoteVolume", 0))  # Already in USDT
        )

    except requests.RequestException as e:
        logging.warning(f"Binance request failed: {e}")
        return None


def get_market_data(symbol: str, source: str = "auto") -> MarketData:
    """
    Fetch market data with automatic fallback.

    Args:
        symbol: Trading symbol (e.g., "BTC", "BTCUSDT", "BTC-USD")
        source: Data source - "coingecko", "coinbase", "binance", or "auto"

    Returns:
        MarketData object with current market data

    Raises:
        MarketDataError: If all sources fail
    """
    base_symbol = normalize_symbol(symbol)

    if source == "coingecko":
        data = get_coingecko_data(base_symbol)
        if data:
            return data
        raise MarketDataError(f"Failed to fetch data from CoinGecko for {base_symbol}")

    if source == "coinbase":
        data = get_coinbase_price(base_symbol)
        if data:
            return data
        raise MarketDataError(f"Failed to fetch data from Coinbase for {base_symbol}")

    if source == "binance":
        data = get_binance_price(base_symbol)
        if data:
            return data
        raise MarketDataError(f"Failed to fetch data from Binance for {base_symbol}")

    # Auto mode: try sources in order
    for fetcher, name in [
        (get_coinbase_price, "Coinbase"),
        (get_coingecko_data, "CoinGecko"),
        (get_binance_price, "Binance")
    ]:
        data = fetcher(base_symbol)
        if data:
            logging.debug(f"Market data fetched from {name} for {base_symbol}")
            return data

    raise MarketDataError(f"All market data sources failed for {base_symbol}")


def get_multiple_market_data(symbols: List[str]) -> Dict[str, MarketData]:
    """Fetch market data for multiple symbols."""
    results = {}
    for symbol in symbols:
        try:
            results[normalize_symbol(symbol)] = get_market_data(symbol)
        except MarketDataError as e:
            logging.warning(f"Failed to get market data for {symbol}: {e}")
    return results


def format_market_context(market_data: MarketData) -> str:
    """Format market data as context string for AI prompts."""
    direction = "up" if market_data.price_change_24h_percent > 0 else "down"

    return f"""Current {market_data.symbol} Market Data:
- Price: ${market_data.price:,.2f}
- 24h Change: {market_data.price_change_24h_percent:+.2f}% (${market_data.price_change_24h:+,.2f})
- 24h High: ${market_data.high_24h:,.2f}
- 24h Low: ${market_data.low_24h:,.2f}
- 24h Volume: ${market_data.volume_24h:,.0f}
- Price is trending {direction} over the last 24 hours
- Current price is {((market_data.price - market_data.low_24h) / (market_data.high_24h - market_data.low_24h) * 100) if market_data.high_24h != market_data.low_24h else 50:.0f}% of the way between 24h low and high"""


def get_fear_greed_index() -> Optional[Dict[str, Any]]:
    """Fetch the Crypto Fear & Greed Index."""
    url = "https://api.alternative.me/fng/"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("data"):
            entry = data["data"][0]
            return {
                "value": int(entry.get("value", 50)),
                "classification": entry.get("value_classification", "Neutral"),
                "timestamp": entry.get("timestamp")
            }
    except requests.RequestException as e:
        logging.warning(f"Fear & Greed Index request failed: {e}")

    return None


def get_enhanced_market_context(symbol: str) -> str:
    """
    Get comprehensive market context for AI prompts.
    Includes price data and sentiment indicators.
    """
    try:
        market_data = get_market_data(symbol)
        context = format_market_context(market_data)

        # Add Fear & Greed Index
        fng = get_fear_greed_index()
        if fng:
            context += f"\n\nMarket Sentiment (Fear & Greed Index):\n- Value: {fng['value']}/100\n- Classification: {fng['classification']}"

        return context

    except MarketDataError as e:
        logging.warning(f"Could not fetch market context: {e}")
        return f"(Market data unavailable for {symbol})"
