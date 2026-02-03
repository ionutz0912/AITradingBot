"""Discord webhook notifications for trading bot."""

import logging
from datetime import datetime, timezone
import requests


class DiscordNotifier:
    """Send trading notifications to Discord via webhook."""

    TIMEOUT = 10  # seconds

    def __init__(self, webhook_url: str):
        """
        Initialize Discord notifier.

        Args:
            webhook_url: Discord webhook URL

        Raises:
            ValueError: If webhook URL is invalid
        """
        if not webhook_url or webhook_url == "your_discord_webhook_here":
            raise ValueError("Invalid Discord webhook URL")

        if not webhook_url.startswith("https://discord.com/api/webhooks/"):
            raise ValueError("Discord webhook URL must start with https://discord.com/api/webhooks/")

        self.webhook_url = webhook_url

    def send_notification(
        self,
        run_name: str,
        interpretation: str,
        reason: str = "",
        include_reason: bool = True
    ) -> bool:
        """
        Send trading signal notification to Discord.

        Args:
            run_name: Name of the trading run
            interpretation: AI interpretation (Bullish/Bearish/Neutral)
            reason: AI reasoning for the interpretation
            include_reason: Whether to include reasoning in message

        Returns:
            True if notification sent successfully, False otherwise
        """
        # Choose emoji based on interpretation
        emoji_map = {
            "Bullish": "\u2705",   # Green checkmark
            "Bearish": "\u274c",   # Red X
            "Neutral": "\u26a0\ufe0f",   # Warning sign
        }
        emoji = emoji_map.get(interpretation, "\u2753")  # Question mark fallback

        # Build embed
        timestamp = datetime.now(timezone.utc).isoformat()

        embed = {
            "title": f"{emoji} Trading Signal: {interpretation}",
            "color": self._get_color(interpretation),
            "fields": [
                {"name": "Run", "value": run_name, "inline": True},
                {"name": "Signal", "value": interpretation, "inline": True},
            ],
            "timestamp": timestamp,
            "footer": {"text": "AI Trading Bot"}
        }

        if include_reason and reason:
            # Truncate reason if too long for Discord
            truncated_reason = reason[:1000] + "..." if len(reason) > 1000 else reason
            embed["fields"].append({
                "name": "Reasoning",
                "value": truncated_reason,
                "inline": False
            })

        payload = {"embeds": [embed]}

        try:
            r = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.TIMEOUT
            )
            r.raise_for_status()
            logging.info(f"Discord notification sent: {interpretation}")
            return True

        except requests.RequestException as e:
            logging.error(f"Discord notification failed: {e}")
            return False

    def _get_color(self, interpretation: str) -> int:
        """Get embed color based on interpretation."""
        colors = {
            "Bullish": 0x00FF00,   # Green
            "Bearish": 0xFF0000,   # Red
            "Neutral": 0xFFFF00,   # Yellow
        }
        return colors.get(interpretation, 0x808080)  # Gray fallback

    def send_error(self, run_name: str, error_message: str) -> bool:
        """
        Send error notification to Discord.

        Args:
            run_name: Name of the trading run
            error_message: Error description

        Returns:
            True if notification sent successfully, False otherwise
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        embed = {
            "title": "\u26a0\ufe0f Trading Bot Error",
            "color": 0xFF0000,  # Red
            "fields": [
                {"name": "Run", "value": run_name, "inline": True},
                {"name": "Error", "value": error_message[:1000], "inline": False},
            ],
            "timestamp": timestamp,
            "footer": {"text": "AI Trading Bot"}
        }

        payload = {"embeds": [embed]}

        try:
            r = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.TIMEOUT
            )
            r.raise_for_status()
            logging.info("Discord error notification sent")
            return True

        except requests.RequestException as e:
            logging.error(f"Discord error notification failed: {e}")
            return False
