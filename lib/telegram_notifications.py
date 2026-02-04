"""
Telegram Notifications Module for AI Trading Bot

Send trading signals, alerts, and status updates via Telegram bot.

Features:
- Trade signal notifications with entry/stop loss prices
- Position open/close alerts
- Error notifications
- Daily summary reports
- Custom message formatting with emojis

Setup:
1. Create a bot with @BotFather on Telegram
2. Get your bot token
3. Get your chat ID (use @userinfobot or @getidsbot)
4. Set environment variables:
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id

Usage:
    from lib.telegram_notifications import TelegramNotifier

    notifier = TelegramNotifier()
    notifier.send_trade_signal("BTCUSDT", "Bullish", entry=95000, stop_loss=85500)
"""

import os
import logging
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


class TelegramError(Exception):
    """Exception raised for Telegram API errors."""
    pass


@dataclass
class TradeAlert:
    """Trade alert data structure."""
    symbol: str
    signal: str  # Bullish, Bearish, Neutral
    action: str  # open_long, close_long, open_short, close_short, hold, etc.
    entry_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    stop_loss_percent: Optional[float] = None
    take_profit_price: Optional[float] = None
    position_size: Optional[float] = None
    reasoning: Optional[str] = None


class TelegramNotifier:
    """
    Telegram notification handler for trading alerts.

    Environment variables:
        TELEGRAM_BOT_TOKEN: Bot token from @BotFather
        TELEGRAM_CHAT_ID: Your chat ID or channel ID
    """

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    # Emoji mappings
    SIGNAL_EMOJI = {
        "Bullish": "🟢",
        "Bearish": "🔴",
        "Neutral": "🟡",
    }

    ACTION_EMOJI = {
        "open_long": "📈",
        "close_long": "📉",
        "open_short": "📉",
        "close_short": "📈",
        "hold_long": "⏳",
        "hold_short": "⏳",
        "no_action": "⏸️",
        "emergency_close": "🚨",
    }

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML"
    ):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token (or use TELEGRAM_BOT_TOKEN env var)
            chat_id: Telegram chat/channel ID (or use TELEGRAM_CHAT_ID env var)
            parse_mode: Message parse mode (HTML or Markdown)
        """
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.parse_mode = parse_mode
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logging.warning("Telegram notifications disabled: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    def _make_request(self, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to Telegram API."""
        if not self.enabled:
            logging.debug("Telegram notifications disabled, skipping request")
            return {"ok": False, "error": "Notifications disabled"}

        url = self.BASE_URL.format(token=self.bot_token, method=method)

        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if not result.get("ok"):
                error_msg = result.get("description", "Unknown error")
                logging.error(f"Telegram API error: {error_msg}")
                raise TelegramError(error_msg)

            return result

        except requests.RequestException as e:
            logging.error(f"Telegram request failed: {e}")
            raise TelegramError(f"Request failed: {e}")

    def send_message(self, text: str, disable_preview: bool = True) -> bool:
        """
        Send a text message.

        Args:
            text: Message text (supports HTML or Markdown based on parse_mode)
            disable_preview: Disable link preview

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False

        try:
            self._make_request("sendMessage", {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": disable_preview,
            })
            return True
        except TelegramError as e:
            logging.error(f"Failed to send Telegram message: {e}")
            return False

    def send_trade_signal(
        self,
        symbol: str,
        signal: str,
        action: str = "signal",
        entry_price: Optional[float] = None,
        current_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        stop_loss_percent: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        position_size: Optional[float] = None,
        reasoning: Optional[str] = None,
        crypto_name: Optional[str] = None
    ) -> bool:
        """
        Send a trade signal notification with all relevant details.

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            signal: AI signal (Bullish, Bearish, Neutral)
            action: Action taken (open_long, close_long, etc.)
            entry_price: Entry price for the trade
            current_price: Current market price
            stop_loss_price: Calculated stop loss price
            stop_loss_percent: Stop loss percentage
            take_profit_price: Optional take profit price
            position_size: Position size in USD
            reasoning: AI reasoning (optional)
            crypto_name: Human-readable name (e.g., Bitcoin)
        """
        signal_emoji = self.SIGNAL_EMOJI.get(signal, "⚪")
        action_emoji = self.ACTION_EMOJI.get(action, "📊")

        # Build message
        name_display = f"{crypto_name} " if crypto_name else ""
        lines = [
            f"{action_emoji} <b>Trade Alert: {name_display}({symbol})</b>",
            "",
            f"Signal: {signal_emoji} <b>{signal}</b>",
            f"Action: {self._format_action(action)}",
        ]

        # Price information
        if current_price:
            lines.append(f"Current Price: <code>${current_price:,.2f}</code>")
        if entry_price:
            lines.append(f"Entry Price: <code>${entry_price:,.2f}</code>")

        # Stop loss information
        if stop_loss_price or stop_loss_percent:
            lines.append("")
            lines.append("🛑 <b>Stop Loss:</b>")
            if stop_loss_price:
                lines.append(f"   Price: <code>${stop_loss_price:,.2f}</code>")
            if stop_loss_percent:
                lines.append(f"   Percent: <code>{stop_loss_percent}%</code>")
            if entry_price and stop_loss_price:
                risk = abs(entry_price - stop_loss_price)
                lines.append(f"   Risk: <code>${risk:,.2f}</code>")

        # Take profit
        if take_profit_price:
            lines.append("")
            lines.append(f"🎯 Take Profit: <code>${take_profit_price:,.2f}</code>")
            if entry_price:
                reward = abs(take_profit_price - entry_price)
                lines.append(f"   Potential: <code>${reward:,.2f}</code>")

        # Position size
        if position_size:
            lines.append("")
            if isinstance(position_size, str) and position_size.endswith('%'):
                lines.append(f"💰 Position Size: <code>{position_size}</code> of capital")
            else:
                lines.append(f"💰 Position Size: <code>${position_size:,.2f}</code>")

        # Reasoning (truncated)
        if reasoning:
            lines.append("")
            lines.append("💭 <b>AI Reasoning:</b>")
            # Truncate to 300 chars
            truncated = reasoning[:300] + "..." if len(reasoning) > 300 else reasoning
            lines.append(f"<i>{truncated}</i>")

        # Timestamp
        lines.append("")
        lines.append(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

        message = "\n".join(lines)
        return self.send_message(message)

    def _format_action(self, action: str) -> str:
        """Format action string for display."""
        action_display = {
            "open_long": "Opening LONG position",
            "close_long": "Closing LONG position",
            "open_short": "Opening SHORT position",
            "close_short": "Closing SHORT position",
            "hold_long": "Holding LONG position",
            "hold_short": "Holding SHORT position",
            "flip_to_long": "Flipping to LONG",
            "flip_to_short": "Flipping to SHORT",
            "no_action": "No action taken",
            "no_action_spot": "No action (spot - can't short)",
            "close_long_spot": "Closing LONG (spot)",
            "emergency_close": "EMERGENCY CLOSE",
        }
        return action_display.get(action, action.replace("_", " ").title())

    def send_position_opened(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss_price: Optional[float] = None,
        stop_loss_percent: Optional[float] = None
    ) -> bool:
        """Send notification when a position is opened."""
        side_upper = side.upper()
        emoji = "📈" if side_upper == "BUY" else "📉"

        lines = [
            f"{emoji} <b>Position Opened: {symbol}</b>",
            "",
            f"Side: <b>{side_upper}</b>",
            f"Entry: <code>${entry_price:,.2f}</code>",
            f"Size: <code>{quantity}</code>",
        ]

        if stop_loss_price:
            lines.append("")
            lines.append(f"🛑 Stop Loss: <code>${stop_loss_price:,.2f}</code>")
            if stop_loss_percent:
                lines.append(f"   ({stop_loss_percent}% from entry)")

        lines.append("")
        lines.append(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

        return self.send_message("\n".join(lines))

    def send_position_closed(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        pnl_percent: float,
        reason: str = "signal"
    ) -> bool:
        """Send notification when a position is closed."""
        pnl_emoji = "✅" if pnl >= 0 else "❌"

        lines = [
            f"{pnl_emoji} <b>Position Closed: {symbol}</b>",
            "",
            f"Side: <b>{side.upper()}</b>",
            f"Entry: <code>${entry_price:,.2f}</code>",
            f"Exit: <code>${exit_price:,.2f}</code>",
            "",
            f"P&L: <code>${pnl:+,.2f}</code> ({pnl_percent:+.2f}%)",
            f"Reason: {reason}",
            "",
            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        ]

        return self.send_message("\n".join(lines))

    def send_error(self, error_message: str, symbol: Optional[str] = None) -> bool:
        """Send error notification."""
        lines = [
            "🚨 <b>Trading Bot Error</b>",
            "",
        ]

        if symbol:
            lines.append(f"Symbol: {symbol}")

        lines.extend([
            f"Error: <code>{error_message[:500]}</code>",
            "",
            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        ])

        return self.send_message("\n".join(lines))

    def send_daily_summary(
        self,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        total_pnl: float,
        positions: Optional[List[Dict]] = None
    ) -> bool:
        """Send daily trading summary."""
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"

        lines = [
            "📊 <b>Daily Trading Summary</b>",
            "",
            f"Total Trades: <code>{total_trades}</code>",
            f"Win Rate: <code>{win_rate:.1f}%</code> ({winning_trades}W / {losing_trades}L)",
            f"P&L: {pnl_emoji} <code>${total_pnl:+,.2f}</code>",
        ]

        if positions:
            lines.append("")
            lines.append("<b>Open Positions:</b>")
            for pos in positions:
                lines.append(f"  • {pos.get('symbol')}: {pos.get('side', 'N/A').upper()}")

        lines.extend([
            "",
            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        ])

        return self.send_message("\n".join(lines))

    def send_startup_message(self, config_summary: str = "") -> bool:
        """Send bot startup notification."""
        lines = [
            "🤖 <b>Trading Bot Started</b>",
            "",
        ]

        if config_summary:
            lines.append(config_summary)
            lines.append("")

        lines.append(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

        return self.send_message("\n".join(lines))

    def test_connection(self) -> bool:
        """Test Telegram connection by sending a test message."""
        if not self.enabled:
            print("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            return False

        try:
            # Get bot info
            result = self._make_request("getMe", {})
            bot_name = result.get("result", {}).get("username", "Unknown")

            # Send test message
            test_msg = f"✅ <b>Connection Test Successful</b>\n\nBot: @{bot_name}\nTime: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
            self.send_message(test_msg)

            print(f"Telegram connected successfully! Bot: @{bot_name}")
            return True

        except TelegramError as e:
            print(f"Telegram connection failed: {e}")
            return False


# Convenience function
def get_telegram_notifier() -> TelegramNotifier:
    """Get a configured Telegram notifier instance."""
    return TelegramNotifier()


# CLI for testing
if __name__ == "__main__":
    import sys

    notifier = TelegramNotifier()

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        notifier.test_connection()
    elif len(sys.argv) > 1 and sys.argv[1] == "--demo":
        # Send demo trade alert
        notifier.send_trade_signal(
            symbol="BTCUSDT",
            signal="Bullish",
            action="open_long",
            crypto_name="Bitcoin",
            current_price=95000,
            entry_price=95000,
            stop_loss_price=85500,
            stop_loss_percent=10,
            position_size=50,
            reasoning="Market showing strong bullish momentum with positive sentiment indicators."
        )
        print("Demo trade alert sent!")
    else:
        print("Usage:")
        print("  python -m lib.telegram_notifications --test   # Test connection")
        print("  python -m lib.telegram_notifications --demo   # Send demo alert")
