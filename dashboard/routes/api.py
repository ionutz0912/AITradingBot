"""
REST API Endpoints for Dashboard

Provides JSON API endpoints for:
- /api/status - Bot configuration and status
- /api/metrics - Performance metrics
- /api/trades - Recent trade history
- /api/market - Live market prices
- /api/positions - Current open positions
- /api/ai-history - Recent AI interpretations
- /api/fear-greed - Fear & Greed Index
- /api/balance - Account balance
"""

from flask import Blueprint, jsonify, request

from ..services.data_service import get_data_service

api_bp = Blueprint("api", __name__)


@api_bp.route("/status")
def get_status():
    """Get bot status and configuration."""
    service = get_data_service()
    return jsonify(service.get_status())


@api_bp.route("/metrics")
def get_metrics():
    """Get performance metrics."""
    service = get_data_service()
    return jsonify(service.get_metrics())


@api_bp.route("/trades")
def get_trades():
    """Get recent trades."""
    count = request.args.get("count", 10, type=int)
    count = min(count, 100)  # Limit to 100 max

    service = get_data_service()
    return jsonify(service.get_recent_trades(count))


@api_bp.route("/market")
def get_market():
    """Get market data for enabled symbols."""
    service = get_data_service()
    return jsonify(service.get_market_data())


@api_bp.route("/positions")
def get_positions():
    """Get current open positions."""
    service = get_data_service()
    return jsonify(service.get_positions())


@api_bp.route("/ai-history")
def get_ai_history():
    """Get recent AI interpretations."""
    count = request.args.get("count", 10, type=int)
    count = min(count, 50)  # Limit to 50 max

    service = get_data_service()
    return jsonify(service.get_ai_history(count))


@api_bp.route("/fear-greed")
def get_fear_greed():
    """Get Fear & Greed Index."""
    service = get_data_service()
    return jsonify(service.get_fear_greed())


@api_bp.route("/balance")
def get_balance():
    """Get account balance."""
    service = get_data_service()
    return jsonify(service.get_account_balance())


@api_bp.route("/summary")
def get_summary():
    """
    Get combined summary of all dashboard data.

    Returns all data in a single request for initial page load.
    """
    service = get_data_service()

    return jsonify({
        "status": service.get_status(),
        "metrics": service.get_metrics(),
        "trades": service.get_recent_trades(5),
        "market": service.get_market_data(),
        "positions": service.get_positions(),
        "ai_history": service.get_ai_history(5),
        "fear_greed": service.get_fear_greed(),
        "balance": service.get_account_balance(),
        "simulations": service.get_simulations_summary()
    })


@api_bp.route("/simulations-summary")
def get_simulations_summary():
    """Get aggregated performance data from all simulations."""
    service = get_data_service()
    return jsonify(service.get_simulations_summary())


@api_bp.route("/positions/close", methods=["POST"])
def close_position():
    """Close an open position."""
    data = request.get_json() or {}
    symbol = data.get("symbol")
    position_id = data.get("position_id")

    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400

    service = get_data_service()
    result = service.close_position(symbol, position_id)

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400
