"""
Notification API Routes for Dashboard

REST endpoints for notification history and management.
"""

from flask import Blueprint, jsonify, request
import logging

from lib.notification_service import get_notification_service
from lib.database import get_notification, list_notifications, get_notification_stats

logger = logging.getLogger(__name__)

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/notifications", methods=["GET"])
def list_all_notifications():
    """
    List notifications with optional filters.

    Query params:
        simulation_id: Filter by simulation
        status: Filter by delivery status (pending, sent, failed, skipped)
        type: Filter by notification type
        limit: Number of results (default: 100)
        offset: Pagination offset (default: 0)
    """
    try:
        simulation_id = request.args.get("simulation_id")
        status = request.args.get("status")
        notification_type = request.args.get("type")
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        notifications = list_notifications(
            simulation_id=simulation_id,
            delivery_status=status,
            notification_type=notification_type,
            limit=limit,
            offset=offset
        )

        return jsonify({
            "success": True,
            "notifications": notifications,
            "count": len(notifications)
        })

    except Exception as e:
        logger.error(f"Error listing notifications: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/notifications/<notification_id>", methods=["GET"])
def get_notification_detail(notification_id: str):
    """Get a notification by ID."""
    try:
        notification = get_notification(notification_id)

        if not notification:
            return jsonify({"success": False, "error": "Notification not found"}), 404

        return jsonify({
            "success": True,
            "notification": notification
        })

    except Exception as e:
        logger.error(f"Error getting notification: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/notifications/<notification_id>/retry", methods=["POST"])
def retry_notification(notification_id: str):
    """
    Retry sending a failed notification.

    Only works for notifications with status 'failed' or 'pending'.
    """
    try:
        notification = get_notification(notification_id)

        if not notification:
            return jsonify({"success": False, "error": "Notification not found"}), 404

        service = get_notification_service()
        updated = service.retry_notification(notification_id)

        return jsonify({
            "success": True,
            "notification": updated
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error retrying notification: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/notifications/stats", methods=["GET"])
def notifications_stats():
    """Get notification statistics."""
    try:
        stats = get_notification_stats()

        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Error getting notification stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/notifications/test", methods=["POST"])
def test_notification():
    """
    Send a test notification.

    Request body (optional):
        message: Custom test message
    """
    try:
        data = request.get_json() or {}
        message = data.get("message", "This is a test notification from AITrading Bot Dashboard")

        service = get_notification_service()

        # Create a test notification
        from lib.database import create_notification, update_notification

        notification = create_notification(
            notification_type="test",
            content=message
        )

        # Try to send via Telegram
        if service._notifier and service.enabled:
            text = f"\U0001F916 *AITrading Bot*\n\n\u2705 *Test Notification*\n\n{message}"
            result = service._notifier.send_message_raw(text)

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

        return jsonify({
            "success": True,
            "notification": notification
        })

    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@notifications_bp.route("/notifications/types", methods=["GET"])
def get_notification_types():
    """Get available notification types."""
    types = [
        {"id": "signal", "name": "Trading Signal", "description": "AI trading signals (Bullish/Bearish/Neutral)"},
        {"id": "trade_opened", "name": "Trade Opened", "description": "Position opened notifications"},
        {"id": "trade_closed", "name": "Trade Closed", "description": "Position closed notifications with P&L"},
        {"id": "error", "name": "Error", "description": "Error and warning notifications"},
        {"id": "daily_summary", "name": "Daily Summary", "description": "End of day trading summaries"},
        {"id": "simulation_status", "name": "Simulation Status", "description": "Simulation start/stop/pause notifications"},
        {"id": "test", "name": "Test", "description": "Test notifications"}
    ]

    return jsonify({
        "success": True,
        "types": types
    })
