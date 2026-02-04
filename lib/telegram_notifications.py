"""Telegram bot notifications for trading bot."""

import logging
from datetime import datetime, timezone
import requests


class TelegramNotifier:
    """Send trading notifications to Telegram via Bot API."""

    TIMEOUT = 10  # seconds
    API_BASE = "https://api.telegram.org/bot"
    APP_NAME = "AITrading Bot"

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat ID to send messages to

        Raises:
            ValueError: If bot token or chat ID is invalid
        """
        if not bot_token or bot_token == "your_telegram_bot_token_here":
            raise ValueError("Invalid Telegram bot token")

        if not chat_id or chat_id == "your_telegram_chat_id_here":
            raise ValueError("Invalid Telegram chat ID")

        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"{self.API_BASE}{bot_token}"

    def send_notification(
        self,
        symbol: str,
        interpretation: str,
        reasoning: str = None,
        include_reasoning: bool = True
    ) -> bool:
        """
        Send trading signal notification to Telegram.

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            interpretation: AI interpretation (Bullish/Bearish/Neutral)
            reasoning: AI reasoning for the interpretation
            include_reasoning: Whether to include reasoning in message

        Returns:
            True if notification sent successfully, False otherwise
        """
        # Choose emoji based on interpretation
        emoji_map = {
            "Bullish": "\u2705",   # Green checkmark
            "Bearish": "\u274c",   # Red X
            "Neutral": "\u26a0\ufe0f",   # Warning sign
        }
        emoji = emoji_map.get(interpretation, "\u2753")

        # Build message
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        message = f"\U0001F916 *{self.APP_NAME}*\n\n"
        message += f"{emoji} *Trading Signal: {interpretation}*\n\n"
        message += f"*Symbol:* `{symbol}`\n"
        message += f"*Signal:* {interpretation}\n"
        message += f"*Time:* {timestamp}\n"

        if include_reasoning and reasoning:
            # Truncate if too long
            truncated = reasoning[:800] + "..." if len(reasoning) > 800 else reasoning
            message += f"\n*Reasoning:*\n{truncated}"

        return self._send_message(message)

    def send_trade_opened(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        is_paper: bool = False
    ) -> bool:
        """
        Send trade opened notification.

        Args:
            symbol: Trading symbol
            side: Trade side (buy/sell)
            quantity: Trade quantity
            price: Entry price
            is_paper: Whether this is a paper trade

        Returns:
            True if notification sent successfully
        """
        emoji = "\U0001F7E2" if side.lower() == "buy" else "\U0001F534"  # Green/Red circle
        paper_tag = " [PAPER]" if is_paper else ""

        message = f"\U0001F916 *{self.APP_NAME}*\n\n"
        message += f"{emoji} *Position Opened{paper_tag}*\n\n"
        message += f"*Symbol:* `{symbol}`\n"
        message += f"*Side:* {side.upper()}\n"
        message += f"*Quantity:* {quantity:.6f}\n"
        message += f"*Entry Price:* ${price:,.2f}\n"
        message += f"*Value:* ${quantity * price:,.2f}"

        return self._send_message(message)

    def send_trade_closed(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        exit_price: float,
        pnl: float,
        is_paper: bool = False
    ) -> bool:
        """
        Send trade closed notification.

        Args:
            symbol: Trading symbol
            side: Trade side (buy/sell)
            quantity: Trade quantity
            entry_price: Entry price
            exit_price: Exit price
            pnl: Profit/Loss
            is_paper: Whether this is a paper trade

        Returns:
            True if notification sent successfully
        """
        emoji = "\U0001F4B0" if pnl >= 0 else "\U0001F4B8"  # Money bag / Money with wings
        paper_tag = " [PAPER]" if is_paper else ""
        pnl_emoji = "\u2705" if pnl >= 0 else "\u274c"

        message = f"\U0001F916 *{self.APP_NAME}*\n\n"
        message += f"{emoji} *Position Closed{paper_tag}*\n\n"
        message += f"*Symbol:* `{symbol}`\n"
        message += f"*Side:* {side.upper()}\n"
        message += f"*Entry:* ${entry_price:,.2f}\n"
        message += f"*Exit:* ${exit_price:,.2f}\n"
        message += f"\n{pnl_emoji} *P&L:* ${pnl:,.2f}"

        return self._send_message(message)

    def send_error(self, run_name: str, error_message: str) -> bool:
        """
        Send error notification to Telegram.

        Args:
            run_name: Name of the trading run
            error_message: Error description

        Returns:
            True if notification sent successfully
        """
        message = f"\U0001F916 *{self.APP_NAME}*\n\n"
        message += "\u26a0\ufe0f *Error Alert*\n\n"
        message += f"*Run:* {run_name}\n"
        message += f"*Error:* {error_message[:500]}"

        return self._send_message(message)

    def send_daily_summary(
        self,
        run_name: str,
        total_trades: int,
        winning_trades: int,
        total_pnl: float,
        balance: float
    ) -> bool:
        """
        Send daily summary notification.

        Args:
            run_name: Name of the trading run
            total_trades: Number of trades today
            winning_trades: Number of winning trades
            total_pnl: Total P&L for the day
            balance: Current account balance

        Returns:
            True if notification sent successfully
        """
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        pnl_emoji = "\U0001F4C8" if total_pnl >= 0 else "\U0001F4C9"  # Chart up/down

        message = f"\U0001F916 *{self.APP_NAME}*\n\n"
        message += f"\U0001F4CA *Daily Summary*\n\n"
        message += f"*Run:* {run_name}\n"
        message += f"*Trades:* {total_trades}\n"
        message += f"*Win Rate:* {win_rate:.1f}%\n"
        message += f"{pnl_emoji} *P&L:* ${total_pnl:,.2f}\n"
        message += f"*Balance:* ${balance:,.2f}"

        return self._send_message(message)

    def _send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a message via Telegram Bot API.

        Args:
            text: Message text
            parse_mode: Parse mode (Markdown or HTML)

        Returns:
            True if message sent successfully
        """
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        try:
            r = requests.post(url, json=payload, timeout=self.TIMEOUT)
            r.raise_for_status()

            result = r.json()
            if result.get("ok"):
                logging.info("Telegram notification sent")
                return True
            else:
                logging.error(f"Telegram API error: {result.get('description')}")
                return False

        except requests.RequestException as e:
            logging.error(f"Telegram notification failed: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test the Telegram bot connection.

        Returns:
            True if connection is working
        """
        url = f"{self.api_url}/getMe"

        try:
            r = requests.get(url, timeout=self.TIMEOUT)
            r.raise_for_status()

            result = r.json()
            if result.get("ok"):
                bot_name = result.get("result", {}).get("username", "Unknown")
                logging.info(f"Telegram bot connected: @{bot_name}")
                return True

            return False

        except requests.RequestException as e:
            logging.error(f"Telegram connection test failed: {e}")
            return False
