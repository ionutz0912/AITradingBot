#!/usr/bin/env python3
"""
AI Trading Bot Dashboard Entry Point

Starts the Flask web server for the trading bot dashboard.

Usage:
    python run_dashboard.py                    # Dev mode on localhost:5000
    python run_dashboard.py --port 8080        # Custom port
    python run_dashboard.py --host 0.0.0.0     # Allow external connections
"""

import argparse
import atexit
import logging
import os
import sys

# Ensure lib modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from dashboard import create_app

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the dashboard."""
    parser = argparse.ArgumentParser(
        description="AI Trading Bot Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_dashboard.py                  Start on localhost:5000
  python run_dashboard.py --port 8080      Start on localhost:8080
  python run_dashboard.py --host 0.0.0.0   Allow external connections
        """
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Flask debug mode"
    )
    parser.add_argument(
        "--no-simulations",
        action="store_true",
        help="Disable simulation manager (for testing)"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Initialize simulation manager (unless disabled)
    sim_manager = None
    if not args.no_simulations:
        try:
            from lib.simulation_manager import init_simulation_manager
            sim_manager = init_simulation_manager()
            logger.info("Simulation manager initialized")

            # Register shutdown handler
            atexit.register(sim_manager.shutdown)
        except Exception as e:
            logger.error(f"Failed to initialize simulation manager: {e}")
            logger.warning("Simulations will not be available")

    # Initialize notification service
    try:
        from lib.notification_service import init_notification_service
        telegram_enabled = bool(
            os.environ.get("TELEGRAM_BOT_TOKEN") and
            os.environ.get("TELEGRAM_CHAT_ID")
        )
        init_notification_service(enabled=telegram_enabled)
        if telegram_enabled:
            logger.info("Notification service initialized with Telegram")
        else:
            logger.info("Notification service initialized (Telegram disabled)")
    except Exception as e:
        logger.error(f"Failed to initialize notification service: {e}")

    # Create and run the app
    app = create_app()

    print(f"\n{'='*50}")
    print("  AI Trading Bot Dashboard")
    print(f"{'='*50}")
    print(f"  URL: http://{args.host}:{args.port}")
    print(f"  Debug: {'ON' if args.debug else 'OFF'}")
    print(f"  Simulations: {'ON' if sim_manager else 'OFF'}")
    print(f"  Telegram: {'ON' if telegram_enabled else 'OFF'}")
    print(f"{'='*50}")
    print(f"  Pages:")
    print(f"    - Dashboard:     http://{args.host}:{args.port}/")
    print(f"    - Simulations:   http://{args.host}:{args.port}/simulations")
    print(f"    - Notifications: http://{args.host}:{args.port}/notifications")
    print(f"{'='*50}\n")

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )


if __name__ == "__main__":
    main()
