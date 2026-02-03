from __future__ import annotations

import json
import hashlib
import time
import secrets
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar, Generic
import requests
import pandas as pd
import numpy as np
from dataclasses import dataclass


API_URL = "https://fapi.bitunix.com/api/v1/futures"
TIMEOUT = 10

T = TypeVar('T')


class BitunixError(Exception):
    pass


@dataclass(frozen=True)
class BitunixResponse(Generic[T]):
    code: int
    msg: str
    data: T


@dataclass(frozen=True)
class Position:
    positionId: str
    symbol: str
    marginCoin: str
    qty: float
    entryValue: float
    side: str  # "LONG" or "SHORT"
    marginMode: str  # "ISOLATION" or "CROSS"
    positionMode: str  # "ONE_WAY" or "HEDGE"
    leverage: int
    fee: float
    funding: float
    realizedPNL: float
    margin: float
    unrealizedPNL: float
    liqPrice: float
    marginRate: float
    avgOpenPrice: float
    ctime: datetime
    mtime: datetime


class BitunixAuth:
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key

    def _generate_signature(self, nonce: str, timestamp: str, query_params: str = "", body: str = "") -> str:
        digest_input = f"{nonce}{timestamp}{self.api_key}{query_params}{body}"
        digest = hashlib.sha256(digest_input.encode()).hexdigest()
        return hashlib.sha256(f"{digest}{self.secret_key}".encode()).hexdigest()

    def get_headers(self, query_params: str = "", body: str = "") -> dict[str, str]:
        nonce = secrets.token_hex(16)
        timestamp = str(int(time.time() * 1000))
        return {
            "api-key": self.api_key,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": self._generate_signature(nonce, timestamp, query_params, body),
            "Content-Type": "application/json"
        }


class BitunixClient:
    def __init__(self, auth: BitunixAuth):
        self._auth = auth

    @staticmethod
    def _handle_response(response: requests.Response) -> Any:
        if response.status_code != 200:
            try:
                error_detail = response.json()
            except (json.JSONDecodeError, AttributeError):
                error_detail = {"status": response.status_code}

            logging.error(f"Exchange API HTTP error {response.status_code}: {error_detail}")
            raise BitunixError(f"HTTP {response.status_code} error: {error_detail}")

        typed_response = BitunixResponse(**response.json())
        if typed_response.code != 0:
            logging.error(f"Exchange API error code {typed_response.code}: {typed_response.msg}")
            raise BitunixError(f"Bitunix API error code {typed_response.code}: {typed_response.msg}")
        return typed_response.data

    def get(self, endpoint: str, query_params: dict[str, Any] | None = None) -> Any:
        url = f"{API_URL}{endpoint}"

        sorted_params = ""
        if query_params:
            sorted_items = sorted(query_params.items(), key=lambda x: x[0])
            sorted_params = "".join(f"{key}{value}" for key, value in sorted_items)

        headers = self._auth.get_headers(query_params=sorted_params)

        try:
            response = requests.get(
                url=url,
                headers=headers,
                params=query_params,
                timeout=TIMEOUT
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            raise BitunixError(f"Request failed: {e}")

    def post(self, endpoint: str, data: dict[str, Any]) -> Any:
        url = f"{API_URL}{endpoint}"
        data_str = json.dumps(data, separators=(',', ':'))
        headers = self._auth.get_headers(body=data_str)

        try:
            response = requests.post(
                url=url,
                headers=headers,
                data=data_str,
                timeout=TIMEOUT
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            raise BitunixError(f"Request failed: {e}")


class BitunixFutures:
    def __init__(self, api_key: str, secret_key: str):
        self._auth = BitunixAuth(api_key, secret_key)
        self._client = BitunixClient(self._auth)
        self._trading_pairs_info: pd.DataFrame | None = None
        self._current_symbol_info: dict[str, Any] | None = None

    def _ensure_trading_pairs_info(self, symbol: str) -> None:
        if self._trading_pairs_info is None:
            self._trading_pairs_info = self.get_trading_pairs()

        if symbol not in self._trading_pairs_info.index:
            raise ValueError(f"Symbol {symbol} not found in trading pairs")

        self._current_symbol_info = self._trading_pairs_info.loc[symbol].to_dict()

    def _qty_to_precision(self, symbol: str, amount: float, rounding_mode: str = "TRUNCATE") -> str:
        try:
            self._ensure_trading_pairs_info(symbol)
            min_amount = float(self._current_symbol_info['minTradeVolume'])

            if amount < min_amount:
                raise ValueError(f"Amount {amount} is less than minimum {min_amount}")

            return self._apply_precision(amount, self._current_symbol_info['basePrecision'], rounding_mode)

        except Exception as e:
            raise ValueError(f"Failed to calculate amount precision: {str(e)}")

    def _price_to_precision(self, symbol: str, price: float, rounding_mode: str = "ROUND") -> str:
        try:
            self._ensure_trading_pairs_info(symbol)
            return self._apply_precision(price, self._current_symbol_info['quotePrecision'], rounding_mode)

        except Exception as e:
            raise ValueError(f"Failed to calculate price precision: {str(e)}")

    @staticmethod
    def _apply_precision(value: float, precision: int, rounding_mode: str) -> str:
        multiplier = 10 ** precision
        scaled = value * multiplier
        scaled = int(scaled) if rounding_mode == "TRUNCATE" else round(scaled)
        return f"{scaled / multiplier:g}"

    def get_current_price(self, symbol: str) -> float:
        """
        Get current market price for a symbol from public API.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")

        Returns:
            Current last price
        """
        endpoint = "/market/tickers"
        query_params = {"symbols": symbol}
        response_data = self._client.get(endpoint, query_params)

        for ticker in response_data:
            if ticker["symbol"] == symbol:
                return float(ticker["lastPrice"])

        raise ValueError(f"Symbol {symbol} not found in ticker response")

    def get_account_balance(self, margin_coin: str) -> float:
        """
        Get total account balance (available + margin).

        Args:
            margin_coin: Margin currency (e.g., "USDT")

        Returns:
            Total balance as float
        """
        endpoint = "/account"
        query_params = {"marginCoin": margin_coin}
        response_data = self._client.get(endpoint, query_params)

        available = float(response_data["available"])
        margin = float(response_data["margin"])
        total_balance = available + margin

        return total_balance

    def set_margin_mode(self, symbol: str, margin_mode: str = "ISOLATION", margin_coin: str = "USDT") -> dict[str, Any]:
        margin_mode = margin_mode.upper()
        if margin_mode not in ['CROSS', 'ISOLATION']:
            raise ValueError("margin_mode must be either 'CROSS' or 'ISOLATION'")

        endpoint = "/account/change_margin_mode"
        data = {
            "symbol": symbol,
            "marginMode": margin_mode,
            "marginCoin": margin_coin
        }
        return self._client.post(endpoint, data)

    def set_leverage(self, symbol: str, leverage: int, margin_coin: str = "USDT") -> dict[str, Any]:
        endpoint = "/account/change_leverage"
        data = {
            "symbol": symbol,
            "leverage": leverage,
            "marginCoin": margin_coin
        }
        return self._client.post(endpoint, data)

    def get_trading_pairs(self, symbols: list[str] | None = None) -> pd.DataFrame:
        endpoint = "/market/trading_pairs"

        query_params = {}
        if symbols:
            query_params["symbols"] = ",".join(symbols)

        raw_data = self._client.get(endpoint, query_params)
        return self._convert_trading_pairs_to_dataframe(raw_data)

    @staticmethod
    def _convert_trading_pairs_to_dataframe(raw_data: list[dict[str, Any]]) -> pd.DataFrame:
        data = np.array([tuple(d.values()) for d in raw_data],
                        dtype=[(k, object) for k in raw_data[0].keys()])

        df = pd.DataFrame(data)

        return df.set_index('symbol')

    def place_order(
            self,
            symbol: str,
            qty: float,
            side: str,  # "BUY" or "SELL"
            trade_side: str,  # "OPEN" or "CLOSE"
            order_type: str,  # "LIMIT" or "MARKET"
            price: float | None = None,
            position_id: str | None = None,
            effect: str = "GTC",  # "IOC", "FOK", "GTC", "POST_ONLY"
            client_id: str | None = None,
            reduce_only: bool = False,
            tp_price: float | None = None,
            tp_stop_type: str = "MARK_PRICE",  # "MARK_PRICE" or "LAST_PRICE"
            tp_order_type: str = "MARKET",  # "LIMIT" or "MARKET"
            tp_order_price: float | None = None,
            sl_price: float | None = None,
            sl_stop_type: str = "MARK_PRICE",  # "MARK_PRICE" or "LAST_PRICE"
            sl_order_type: str = "MARKET",  # "LIMIT" or "MARKET"
            sl_order_price: float | None = None,
    ) -> dict[str, str]:
        """Place an order on the exchange."""
        endpoint = "/trade/place_order"

        if order_type == "LIMIT" and price is None:
            raise ValueError("Price is required for LIMIT orders")

        if trade_side == "CLOSE" and position_id is None:
            raise ValueError("Position ID is required when trade_side is CLOSE")

        order_data = {
            "symbol": symbol,
            "qty": self._qty_to_precision(symbol, qty),
            "side": side,
            "tradeSide": trade_side,
            "orderType": order_type,
            "effect": effect,
            "price": self._price_to_precision(symbol, price) if price is not None else None,
            "positionId": position_id,
            "clientId": client_id,
            "reduceOnly": reduce_only,
            "tpPrice": self._price_to_precision(symbol, tp_price) if tp_price is not None else None,
            "tpStopType": tp_stop_type,
            "tpOrderType": tp_order_type,
            "tpOrderPrice": self._price_to_precision(symbol, tp_order_price) if tp_order_price is not None else None,
            "slPrice": self._price_to_precision(symbol, sl_price) if sl_price is not None else None,
            "slStopType": sl_stop_type,
            "slOrderType": sl_order_type,
            "slOrderPrice": self._price_to_precision(symbol, sl_order_price) if sl_order_price is not None else None,
        }

        return self._client.post(endpoint, {k: v for k, v in order_data.items() if v is not None})

    def get_pending_positions(
            self,
            symbol: str | None = None,
            position_id: str | None = None
    ) -> Position | None:
        if not symbol:
            raise ValueError("Symbol is required")

        endpoint = "/position/get_pending_positions"

        query_params = {"symbol": symbol}
        if position_id:
            query_params["positionId"] = position_id

        raw_data = self._client.get(endpoint, query_params)

        if len(raw_data) > 1:
            raise ValueError("Multiple positions found. Currently only one-way mode is supported")

        return Position(**raw_data[0]) if raw_data else None

    def flash_close_position(self, position_id: str) -> dict[str, str]:
        if not position_id:
            raise ValueError("Position ID is required")

        endpoint = "/trade/flash_close_position"
        data = {"positionId": position_id}

        return self._client.post(endpoint, data)

    def place_position_tpsl(
            self,
            symbol: str,
            position_id: str,
            tp_price: float | None = None,
            tp_stop_type: str = "MARK_PRICE",  # "MARK_PRICE" or "LAST_PRICE"
            sl_price: float | None = None,
            sl_stop_type: str = "MARK_PRICE",  # "MARK_PRICE" or "LAST_PRICE"
    ) -> dict[str, str]:
        """
        Place position-level TP/SL order (attached to position).
        At least one of tp_price or sl_price must be provided.
        """
        if not position_id:
            raise ValueError("Position ID is required")

        if tp_price is None and sl_price is None:
            raise ValueError("At least one of tp_price or sl_price must be provided")

        endpoint = "/tpsl/position/place_order"

        tpsl_data = {
            "symbol": symbol,
            "positionId": position_id,
            "tpPrice": self._price_to_precision(symbol, tp_price) if tp_price is not None else None,
            "tpStopType": tp_stop_type,
            "slPrice": self._price_to_precision(symbol, sl_price) if sl_price is not None else None,
            "slStopType": sl_stop_type,
        }

        return self._client.post(endpoint, {k: v for k, v in tpsl_data.items() if v is not None})
