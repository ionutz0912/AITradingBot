"""
Notification Service for AI Trading Bot

Wraps TelegramNotifier with history tracking and database persistence.
All notifications are recorded in SQLite for history and retry functionality.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .database import (
    create_notification,
    get_notification,
    list_notifications,
    update_notification,
    get_notification_stats,
)
from .telegram_notifications import TelegramNotifier

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications with history tracking.

    Wraps TelegramNotifier and stores all notifications in the database
    for history tracking, retry functionality, and analytics.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Initialize the notification service.

        Args:
            bot_token: Telegram bot token (falls back to env var)
            chat_id: Telegram chat ID (falls back to env var)
            enabled: Whether to actually send notifications
        """
        self.enabled = enabled
        self._notifier: Optional[TelegramNotifier] = None

        # Try to initialize Telegram notifier
        token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        chat = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

        if token and chat and enabled:
            try:
                self._notifier = TelegramNotifier(token, chat)
                logger.info("NotificationService initialized with Telegram")
            except ValueError as e:
                logger.warning(f"Failed to initialize Telegram: {e}")
                self._notifier = None
        else:
            logger.info("NotificationService initialized without Telegram (disabled or missing config)")

    def send_signal(
        self,
        symbol: str,
        interpretation: str,
        reasoning: Optional[str] = None,
        include_reasoning: bool = True,
        simulation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a trading signal notification.

        Args:
            symbol: Trading symbol
            interpretation: AI interpretation (Bullish/Bearish/Neutral)
            reasoning: AI reasoning
            include_reasoning: Whether to include reasoning
            simulation_id: Optional simulation ID for tracking

        Returns:
            Notification record with delivery status
        """
        # Build content for storage
        content = f"Signal: {interpretation} for {symbol}"
        if include_reasoning and reasoning:
            content += f"\nReasoning: {reasoning[:500]}"

        # Create notification record
        notification = create_notification(
            notification_type="signal",
            content=content,
            simulation_id=simulation_id,
            symbol=symbol
        )

        # Send via Telegram if available
        if self._notifier and self.enabled:
            result = self._send_telegram_signal(
                symbol, interpretation, reasoning, include_reasoning
            )
            notification = update_notification(
                notification["id"],
                delivery_status="sent" if result["success"] else "failed",
                telegram_message_id=result.get("message_id"),
                error_message=result.get("error")
            )
        else:
            notification = update_notification(
                notification["id"],
                delivery_status="skipped",
                error_message="Telegram not configured or disabled"
            )

        return notification

    def send_trade_opened(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        is_paper: bool = False,
        simulation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send trade opened notification.

        Args:
            symbol: Trading symbol
            side: Trade side (buy/sell)
            quantity: Trade quantity
            price: Entry price
            is_paper: Whether this is a paper trade
            simulation_id: Optional simulation ID for tracking

        Returns:
            Notification record with delivery status
        """
        paper_tag = "[PAPER] " if is_paper else ""
        content = f"{paper_tag}Opened {side.upper()} {quantity:.6f} {symbol} @ ${price:,.2f}"

        notification = create_notification(
            notification_type="trade_opened",
            content=content,
            simulation_id=simulation_id,
            symbol=symbol
        )

        if self._notifier and self.enabled:
            result = self._send_telegram_trade_opened(
                symbol, side, quantity, price, is_paper
            )
            notification = update_notification(
                notification["id"],
                delivery_status="sent" if result["success"] else "failed",
                telegram_message_id=result.get("message_id"),
                error_message=result.get("error")
            )
        else:
            notification = update_notification(
                notification["id"],
                delivery_status="skipped",
                error_message="Telegram not configured or disabled"
            )

        return notification

    def send_trade_closed(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        exit_price: float,
        pnl: float,
        is_paper: bool = False,
        simulation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send trade closed notification.

        Args:
            symbol: Trading symbol
            side: Trade side
            quantity: Trade quantity
            entry_price: Entry price
            exit_price: Exit price
            pnl: Profit/Loss
            is_paper: Whether this is a paper trade
            simulation_id: Optional simulation ID for tracking

        Returns:
            Notification record with delivery status
        """
        paper_tag = "[PAPER] " if is_paper else ""
        pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"
        content = f"{paper_tag}Closed {side.upper()} {symbol} | Entry: ${entry_price:,.2f} | Exit: ${exit_price:,.2f} | PnL: {pnl_str}"

        notification = create_notification(
            notification_type="trade_closed",
            content=content,
            simulation_id=simulation_id,
            symbol=symbol
        )

        if self._notifier and self.enabled:
            result = self._send_telegram_trade_closed(
                symbol, side, quantity, entry_price, exit_price, pnl, is_paper
            )
            notification = update_notification(
                notification["id"],
                delivery_status="sent" if result["success"] else "failed",
                telegram_message_id=result.get("message_id"),
                error_message=result.get("error")
            )
        else:
            notification = update_notification(
                notification["id"],
                delivery_status="skipped",
                error_message="Telegram not configured or disabled"
            )

        return notification

    def send_error(
        self,
        run_name: str,
        error_message: str,
        simulation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send error notification.

        Args:
            run_name: Name of the trading run
            error_message: Error description
            simulation_id: Optional simulation ID for tracking

        Returns:
            Notification record with delivery status
        """
        content = f"Error in {run_name}: {error_message[:500]}"

        notification = create_notification(
            notification_type="error",
            content=content,
            simulation_id=simulation_id
        )

        if self._notifier and self.enabled:
            result = self._send_telegram_error(run_name, error_message)
            notification = update_notification(
                notification["id"],
                delivery_status="sent" if result["success"] else "failed",
                telegram_message_id=result.get("message_id"),
                error_message=result.get("error")
            )
        else:
            notification = update_notification(
                notification["id"],
                delivery_status="skipped",
                error_message="Telegram not configured or disabled"
            )

        return notification

    def send_daily_summary(
        self,
        run_name: str,
        total_trades: int,
        winning_trades: int,
        total_pnl: float,
        balance: float,
        simulation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send daily summary notification.

        Args:
            run_name: Name of the trading run
            total_trades: Number of trades
            winning_trades: Number of winning trades
            total_pnl: Total P&L
            balance: Current balance
            simulation_id: Optional simulation ID for tracking

        Returns:
            Notification record with delivery status
        """
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        pnl_str = f"+${total_pnl:,.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):,.2f}"
        content = f"Daily Summary for {run_name}: {total_trades} trades, {win_rate:.1f}% win rate, PnL: {pnl_str}, Balance: ${balance:,.2f}"

        notification = create_notification(
            notification_type="daily_summary",
            content=content,
            simulation_id=simulation_id
        )

        if self._notifier and self.enabled:
            result = self._send_telegram_daily_summary(
                run_name, total_trades, winning_trades, total_pnl, balance
            )
            notification = update_notification(
                notification["id"],
                delivery_status="sent" if result["success"] else "failed",
                telegram_message_id=result.get("message_id"),
                error_message=result.get("error")
            )
        else:
            notification = update_notification(
                notification["id"],
                delivery_status="skipped",
                error_message="Telegram not configured or disabled"
            )

        return notification

    def send_simulation_status(
        self,
        simulation_name: str,
        status: str,
        message: Optional[str] = None,
        simulation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send simulation status change notification.

        Args:
            simulation_name: Name of the simulation
            status: New status (started, stopped, paused, resumed, error)
            message: Optional additional message
            simulation_id: Simulation ID for tracking

        Returns:
            Notification record with delivery status
        """
        status_emoji = {
            "started": "\u25b6\ufe0f",  # Play button
            "stopped": "\u23f9\ufe0f",  # Stop button
            "paused": "\u23f8\ufe0f",   # Pause button
            "resumed": "\u25b6\ufe0f",  # Play button
            "error": "\u26a0\ufe0f",    # Warning
        }.get(status, "\u2139\ufe0f")   # Info

        content = f"{status_emoji} Simulation '{simulation_name}' {status}"
        if message:
            content += f": {message}"

        notification = create_notification(
            notification_type="simulation_status",
            content=content,
            simulation_id=simulation_id
        )

        if self._notifier and self.enabled:
            text = f"\U0001F916 *AITrading Bot*\n\n{status_emoji} *Simulation Status*\n\n"
            text += f"*Name:* {simulation_name}\n"
            text += f"*Status:* {status.upper()}"
            if message:
                text += f"\n*Details:* {message}"

            result = self._notifier.send_message_raw(text)
            notification = update_notification(
                notification["id"],
                delivery_status="sent" if result["success"] else "failed",
                telegram_message_id=result.get("message_id"),
                error_message=result.get("error")
            )
        else:
            notification = update_notification(
                notification["id"],
                delivery_status="skipped",
                error_message="Telegram not configured or disabled"
            )

        return notification

    def retry_notification(self, notification_id: str) -> Dict[str, Any]:
        """
        Retry sending a failed notification.

        Args:
            notification_id: ID of the notification to retry

        Returns:
            Updated notification record
        """
        notification = get_notification(notification_id)
        if not notification:
            raise ValueError(f"Notification {notification_id} not found")

        if notification["delivery_status"] not in ("failed", "pending"):
            raise ValueError(f"Cannot retry notification with status '{notification['delivery_status']}'")

        if not self._notifier or not self.enabled:
            return update_notification(
                notification_id,
                error_message="Telegram not configured or disabled",
                increment_retry=True
            )

        # Resend the raw content
        result = self._notifier.send_message_raw(notification["content"])

        return update_notification(
            notification_id,
            delivery_status="sent" if result["success"] else "failed",
            telegram_message_id=result.get("message_id"),
            error_message=result.get("error"),
            increment_retry=True
        )

    def get_history(
        self,
        simulation_id: Optional[str] = None,
        status: Optional[str] = None,
        notification_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get notification history with optional filters."""
        return list_notifications(
            simulation_id=simulation_id,
            delivery_status=status,
            notification_type=notification_type,
            limit=limit,
            offset=offset
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        return get_notification_stats()

    # ========================================================================
    # Private helper methods for Telegram sending
    # ========================================================================

    def _send_telegram_signal(
        self,
        symbol: str,
        interpretation: str,
        reasoning: Optional[str],
        include_reasoning: bool
    ) -> Dict[str, Any]:
        """Send signal via Telegram and return result dict."""
        emoji_map = {
            "Bullish": "\u2705",
            "Bearish": "\u274c",
            "Neutral": "\u26a0\ufe0f",
        }
        emoji = emoji_map.get(interpretation, "\u2753")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        message = f"\U0001F916 *AITrading Bot*\n\n"
        message += f"{emoji} *Trading Signal: {interpretation}*\n\n"
        message += f"*Symbol:* `{symbol}`\n"
        message += f"*Signal:* {interpretation}\n"
        message += f"*Time:* {timestamp}\n"

        if include_reasoning and reasoning:
            truncated = reasoning[:800] + "..." if len(reasoning) > 800 else reasoning
            message += f"\n*Reasoning:*\n{truncated}"

        return self._notifier.send_message_raw(message)

    def _send_telegram_trade_opened(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        is_paper: bool
    ) -> Dict[str, Any]:
        """Send trade opened via Telegram and return result dict."""
        emoji = "\U0001F7E2" if side.lower() == "buy" else "\U0001F534"
        paper_tag = " [PAPER]" if is_paper else ""

        message = f"\U0001F916 *AITrading Bot*\n\n"
        message += f"{emoji} *Position Opened{paper_tag}*\n\n"
        message += f"*Symbol:* `{symbol}`\n"
        message += f"*Side:* {side.upper()}\n"
        message += f"*Quantity:* {quantity:.6f}\n"
        message += f"*Entry Price:* ${price:,.2f}\n"
        message += f"*Value:* ${quantity * price:,.2f}"

        return self._notifier.send_message_raw(message)

    def _send_telegram_trade_closed(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        exit_price: float,
        pnl: float,
        is_paper: bool
    ) -> Dict[str, Any]:
        """Send trade closed via Telegram and return result dict."""
        emoji = "\U0001F4B0" if pnl >= 0 else "\U0001F4B8"
        paper_tag = " [PAPER]" if is_paper else ""
        pnl_emoji = "\u2705" if pnl >= 0 else "\u274c"

        message = f"\U0001F916 *AITrading Bot*\n\n"
        message += f"{emoji} *Position Closed{paper_tag}*\n\n"
        message += f"*Symbol:* `{symbol}`\n"
        message += f"*Side:* {side.upper()}\n"
        message += f"*Entry:* ${entry_price:,.2f}\n"
        message += f"*Exit:* ${exit_price:,.2f}\n"
        message += f"\n{pnl_emoji} *P&L:* ${pnl:,.2f}"

        return self._notifier.send_message_raw(message)

    def _send_telegram_error(
        self,
        run_name: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Send error via Telegram and return result dict."""
        message = f"\U0001F916 *AITrading Bot*\n\n"
        message += "\u26a0\ufe0f *Error Alert*\n\n"
        message += f"*Run:* {run_name}\n"
        message += f"*Error:* {error_message[:500]}"

        return self._notifier.send_message_raw(message)

    def _send_telegram_daily_summary(
        self,
        run_name: str,
        total_trades: int,
        winning_trades: int,
        total_pnl: float,
        balance: float
    ) -> Dict[str, Any]:
        """Send daily summary via Telegram and return result dict."""
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        pnl_emoji = "\U0001F4C8" if total_pnl >= 0 else "\U0001F4C9"

        message = f"\U0001F916 *AITrading Bot*\n\n"
        message += f"\U0001F4CA *Daily Summary*\n\n"
        message += f"*Run:* {run_name}\n"
        message += f"*Trades:* {total_trades}\n"
        message += f"*Win Rate:* {win_rate:.1f}%\n"
        message += f"{pnl_emoji} *P&L:* ${total_pnl:,.2f}\n"
        message += f"*Balance:* ${balance:,.2f}"

        return self._notifier.send_message_raw(message)


# Global instance for convenience
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def init_notification_service(
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    enabled: bool = True
) -> NotificationService:
    """Initialize the global notification service with config."""
    global _notification_service
    _notification_service = NotificationService(bot_token, chat_id, enabled)
    return _notification_service
