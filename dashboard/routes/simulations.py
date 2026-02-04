"""
Simulation API Routes for Dashboard

REST endpoints for managing trading simulations.
"""

from flask import Blueprint, jsonify, request
import logging

from lib.simulation_manager import get_simulation_manager
from lib.database import get_simulation_trades

logger = logging.getLogger(__name__)

simulations_bp = Blueprint("simulations", __name__)


@simulations_bp.route("/simulations", methods=["GET"])
def list_simulations():
    """
    List all simulations.

    Query params:
        status: Optional filter by status (pending, running, paused, stopped, error)
    """
    try:
        manager = get_simulation_manager()
        status = request.args.get("status")

        simulations = manager.list_simulations(status=status)
        return jsonify({
            "success": True,
            "simulations": simulations,
            "count": len(simulations)
        })

    except Exception as e:
        logger.error(f"Error listing simulations: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations", methods=["POST"])
def create_simulation():
    """
    Create a new simulation.

    Request body:
        name: Display name for the simulation
        config: SimulationConfig object
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "Request body required"}), 400

        name = data.get("name")
        config = data.get("config")

        if not name:
            return jsonify({"success": False, "error": "name is required"}), 400
        if not config:
            return jsonify({"success": False, "error": "config is required"}), 400

        manager = get_simulation_manager()
        simulation = manager.create_simulation(name, config)

        return jsonify({
            "success": True,
            "simulation": simulation
        }), 201

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating simulation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations/<simulation_id>", methods=["GET"])
def get_simulation(simulation_id: str):
    """Get a simulation by ID."""
    try:
        manager = get_simulation_manager()
        simulation = manager.get_simulation(simulation_id)

        if not simulation:
            return jsonify({"success": False, "error": "Simulation not found"}), 404

        return jsonify({
            "success": True,
            "simulation": simulation
        })

    except Exception as e:
        logger.error(f"Error getting simulation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations/<simulation_id>", methods=["DELETE"])
def delete_simulation(simulation_id: str):
    """Delete a simulation."""
    try:
        manager = get_simulation_manager()
        manager.delete_simulation(simulation_id)

        return jsonify({
            "success": True,
            "message": "Simulation deleted"
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting simulation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations/<simulation_id>/start", methods=["POST"])
def start_simulation(simulation_id: str):
    """Start a simulation."""
    try:
        manager = get_simulation_manager()
        simulation = manager.start_simulation(simulation_id)

        return jsonify({
            "success": True,
            "simulation": simulation
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error starting simulation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations/<simulation_id>/stop", methods=["POST"])
def stop_simulation(simulation_id: str):
    """Stop a running simulation."""
    try:
        manager = get_simulation_manager()
        simulation = manager.stop_simulation(simulation_id)

        return jsonify({
            "success": True,
            "simulation": simulation
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error stopping simulation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations/<simulation_id>/pause", methods=["POST"])
def pause_simulation(simulation_id: str):
    """Pause a running simulation."""
    try:
        manager = get_simulation_manager()
        simulation = manager.pause_simulation(simulation_id)

        return jsonify({
            "success": True,
            "simulation": simulation
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error pausing simulation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations/<simulation_id>/resume", methods=["POST"])
def resume_simulation(simulation_id: str):
    """Resume a paused simulation."""
    try:
        manager = get_simulation_manager()
        simulation = manager.resume_simulation(simulation_id)

        return jsonify({
            "success": True,
            "simulation": simulation
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error resuming simulation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations/<simulation_id>/stats", methods=["GET"])
def get_simulation_stats(simulation_id: str):
    """Get statistics for a simulation."""
    try:
        manager = get_simulation_manager()
        simulation = manager.get_simulation(simulation_id)

        if not simulation:
            return jsonify({"success": False, "error": "Simulation not found"}), 404

        stats = manager.get_simulation_stats(simulation_id)

        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Error getting simulation stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations/<simulation_id>/trades", methods=["GET"])
def get_trades(simulation_id: str):
    """
    Get trades for a simulation.

    Query params:
        limit: Number of trades to return (default: 100)
        offset: Pagination offset (default: 0)
    """
    try:
        manager = get_simulation_manager()
        simulation = manager.get_simulation(simulation_id)

        if not simulation:
            return jsonify({"success": False, "error": "Simulation not found"}), 404

        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        trades = get_simulation_trades(simulation_id, limit=limit, offset=offset)

        return jsonify({
            "success": True,
            "trades": trades,
            "count": len(trades)
        })

    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulations_bp.route("/simulations/presets", methods=["GET"])
def get_presets():
    """Get preset simulation configurations."""
    presets = [
        {
            "id": "btc_conservative",
            "name": "BTC Conservative",
            "description": "Conservative Bitcoin trading with tight risk management",
            "config": {
                "name": "BTC Conservative",
                "symbol": "BTCUSDT",
                "crypto_name": "Bitcoin",
                "initial_capital": 10000,
                "position_size": 5.0,
                "fees": 0.0006,
                "ai_provider": "anthropic",
                "stop_loss_percent": 5.0,
                "max_daily_trades": 5,
                "check_interval_seconds": 600,
                "telegram_enabled": True,
                "telegram_include_reasoning": False
            }
        },
        {
            "id": "eth_moderate",
            "name": "ETH Moderate",
            "description": "Moderate Ethereum trading strategy",
            "config": {
                "name": "ETH Moderate",
                "symbol": "ETHUSDT",
                "crypto_name": "Ethereum",
                "initial_capital": 10000,
                "position_size": "5%",
                "fees": 0.0006,
                "ai_provider": "anthropic",
                "stop_loss_percent": 10.0,
                "max_daily_trades": 10,
                "check_interval_seconds": 300,
                "telegram_enabled": True,
                "telegram_include_reasoning": False
            }
        },
        {
            "id": "sol_aggressive",
            "name": "SOL Aggressive",
            "description": "Aggressive Solana trading for higher volatility",
            "config": {
                "name": "SOL Aggressive",
                "symbol": "SOLUSDT",
                "crypto_name": "Solana",
                "initial_capital": 5000,
                "position_size": "10%",
                "fees": 0.0006,
                "ai_provider": "anthropic",
                "stop_loss_percent": 15.0,
                "max_daily_trades": 15,
                "check_interval_seconds": 180,
                "telegram_enabled": True,
                "telegram_include_reasoning": True
            }
        },
        {
            "id": "xrp_swing",
            "name": "XRP Swing",
            "description": "XRP swing trading strategy",
            "config": {
                "name": "XRP Swing",
                "symbol": "XRPUSDT",
                "crypto_name": "XRP",
                "initial_capital": 5000,
                "position_size": 10.0,
                "fees": 0.0006,
                "ai_provider": "anthropic",
                "stop_loss_percent": 8.0,
                "max_daily_trades": 8,
                "check_interval_seconds": 600,
                "telegram_enabled": True,
                "telegram_include_reasoning": False
            }
        },
        {
            "id": "ada_long_term",
            "name": "ADA Long Term",
            "description": "Cardano longer-term position trading",
            "config": {
                "name": "ADA Long Term",
                "symbol": "ADAUSDT",
                "crypto_name": "Cardano",
                "initial_capital": 5000,
                "position_size": "8%",
                "fees": 0.0006,
                "ai_provider": "anthropic",
                "stop_loss_percent": 12.0,
                "max_daily_trades": 3,
                "check_interval_seconds": 1800,
                "telegram_enabled": True,
                "telegram_include_reasoning": False
            }
        }
    ]

    return jsonify({
        "success": True,
        "presets": presets
    })
