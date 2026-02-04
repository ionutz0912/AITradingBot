"""
Simulation Worker for AI Trading Bot

Worker process that runs a single trading simulation.
Communicates with the manager via multiprocessing queues.
"""

import logging
import os
import signal
import time
from datetime import datetime, timezone
from multiprocessing import Queue
from typing import Any, Dict, Optional

from .ai import get_provider, AIOutlook, AIResponseError, AIProviderError
from .config import SimulationConfig
from .database import (
    update_simulation,
    create_trade,
    update_trade,
    get_simulation,
)
from .forward_tester import ForwardTester
from .market_data import get_market_data, format_market_context, MarketDataError
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


# Command types for control queue
CMD_STOP = "stop"
CMD_PAUSE = "pause"
CMD_RESUME = "resume"


class SimulationWorker:
    """
    Worker that runs a trading simulation in a separate process.

    Handles:
    - AI signal generation
    - Paper trading via ForwardTester
    - Notification sending
    - Status updates to database
    """

    def __init__(
        self,
        simulation_id: str,
        config: SimulationConfig,
        control_queue: Queue,
        status_queue: Queue
    ):
        """
        Initialize the simulation worker.

        Args:
            simulation_id: Database ID for this simulation
            config: Simulation configuration
            control_queue: Queue for receiving control commands
            status_queue: Queue for sending status updates
        """
        self.simulation_id = simulation_id
        self.config = config
        self.control_queue = control_queue
        self.status_queue = status_queue

        self.running = False
        self.paused = False
        self.current_trade_id: Optional[str] = None

        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize the trading components."""
        # Forward tester for paper trading
        self.tester = ForwardTester({
            "initial_capital": self.config.initial_capital,
            "fees": self.config.fees,
            "run_name": f"sim_{self.simulation_id[:8]}"
        })

        # AI provider
        api_key = self._get_api_key()
        self.ai_provider = get_provider(self.config.ai_provider, api_key)

        # Notification service
        self.notifier = NotificationService(
            enabled=self.config.telegram_enabled
        )

    def _get_api_key(self) -> str:
        """Get the appropriate API key based on provider."""
        provider = self.config.ai_provider.lower()

        key_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "xai": "XAI_API_KEY",
            "grok": "XAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }

        env_var = key_map.get(provider, "DEEPSEEK_API_KEY")
        api_key = os.environ.get(env_var)

        if not api_key:
            raise AIProviderError(f"Missing API key: {env_var}")

        return api_key

    def run(self):
        """Main worker loop."""
        self.running = True
        self.paused = False

        # Send started status
        self._send_status("started")
        self.notifier.send_simulation_status(
            self.config.name,
            "started",
            simulation_id=self.simulation_id
        )

        logger.info(f"Simulation {self.config.name} started")

        try:
            while self.running:
                # Check for control commands
                self._process_commands()

                if self.paused:
                    time.sleep(1)
                    continue

                # Run one trading cycle
                try:
                    self._trading_cycle()
                except Exception as e:
                    logger.error(f"Trading cycle error: {e}")
                    self._send_status("error", str(e))

                # Wait for next cycle
                self._wait_with_interrupt(self.config.check_interval_seconds)

        except Exception as e:
            logger.error(f"Simulation error: {e}")
            self._send_status("error", str(e))
            update_simulation(
                self.simulation_id,
                status="error",
                error_message=str(e)
            )
            self.notifier.send_simulation_status(
                self.config.name,
                "error",
                message=str(e),
                simulation_id=self.simulation_id
            )

        finally:
            self._cleanup()

    def _process_commands(self):
        """Process any pending control commands."""
        while not self.control_queue.empty():
            try:
                cmd = self.control_queue.get_nowait()
                self._handle_command(cmd)
            except Exception:
                break

    def _handle_command(self, cmd: str):
        """Handle a control command."""
        if cmd == CMD_STOP:
            logger.info(f"Received stop command for {self.config.name}")
            self.running = False
            self._send_status("stopped")
            update_simulation(self.simulation_id, status="stopped")
            self.notifier.send_simulation_status(
                self.config.name,
                "stopped",
                simulation_id=self.simulation_id
            )

        elif cmd == CMD_PAUSE:
            logger.info(f"Received pause command for {self.config.name}")
            self.paused = True
            self._send_status("paused")
            update_simulation(self.simulation_id, status="paused")
            self.notifier.send_simulation_status(
                self.config.name,
                "paused",
                simulation_id=self.simulation_id
            )

        elif cmd == CMD_RESUME:
            logger.info(f"Received resume command for {self.config.name}")
            self.paused = False
            self._send_status("running")
            update_simulation(self.simulation_id, status="running")
            self.notifier.send_simulation_status(
                self.config.name,
                "resumed",
                simulation_id=self.simulation_id
            )

    def _trading_cycle(self):
        """Execute one trading cycle."""
        symbol = self.config.symbol
        crypto_name = self.config.crypto_name

        # Get market data
        try:
            market_data = get_market_data(symbol)
            market_context = format_market_context(market_data)
        except MarketDataError as e:
            logger.warning(f"Market data unavailable: {e}")
            market_context = ""

        # Build prompt
        prompt = self._build_prompt(crypto_name, market_context)

        # Get AI signal
        try:
            outlook = self.ai_provider.send_request(prompt, crypto_name)
            logger.info(f"{self.config.name}: AI signal = {outlook.interpretation}")
        except (AIResponseError, Exception) as e:
            logger.error(f"AI request failed: {e}")
            self.notifier.send_error(
                self.config.name,
                f"AI request failed: {e}",
                simulation_id=self.simulation_id
            )
            return

        # Send signal notification
        self.notifier.send_signal(
            symbol=symbol,
            interpretation=outlook.interpretation,
            reasoning=outlook.reasons,
            include_reasoning=self.config.telegram_include_reasoning,
            simulation_id=self.simulation_id
        )

        # Execute trading logic
        self._execute_trading_logic(outlook, symbol, market_data.price if market_data else None)

    def _build_prompt(self, crypto_name: str, market_context: str) -> str:
        """Build the AI prompt."""
        prompt = f"""You are a professional cryptocurrency analyst. Analyze {crypto_name} and provide your outlook for the next 24 hours.

Consider:
- Technical analysis and chart patterns
- Market sentiment and momentum
- Recent price action and trends
- Support and resistance levels

{market_context if market_context else ""}

Provide your analysis as either:
- Bullish: You expect the price to increase
- Bearish: You expect the price to decrease
- Neutral: No clear directional bias

Be decisive and provide clear reasoning for your outlook."""

        return prompt

    def _execute_trading_logic(
        self,
        outlook: AIOutlook,
        symbol: str,
        current_price: Optional[float]
    ):
        """Execute trading logic based on AI signal."""
        interpretation = outlook.interpretation
        position = self.tester.get_pending_positions(symbol)

        # Get current price if not provided
        if current_price is None:
            current_price = self.tester.get_current_price(symbol)

        # Calculate position size
        position_size = self._calculate_position_size(current_price)

        # Trading logic
        if position is None:
            # No position - check for entry
            if interpretation == "Bullish":
                self._open_position(symbol, "BUY", position_size, current_price, outlook)
            elif interpretation == "Bearish":
                self._open_position(symbol, "SELL", position_size, current_price, outlook)
            # Neutral = no action

        else:
            # Have position - check for exit
            position_side = position.side
            entry_price = position.avgOpenPrice

            if position_side == "BUY" and interpretation == "Bearish":
                self._close_position(symbol, position, current_price, outlook)
            elif position_side == "SELL" and interpretation == "Bullish":
                self._close_position(symbol, position, current_price, outlook)
            # Same direction or neutral = hold

    def _calculate_position_size(self, price: float) -> float:
        """Calculate the position size in base currency."""
        pos_size = self.config.position_size

        if isinstance(pos_size, str) and pos_size.endswith('%'):
            # Percentage of capital
            percent = float(pos_size[:-1])
            usd_amount = self.tester.current_capital * (percent / 100)
        else:
            # Fixed USD amount
            usd_amount = float(pos_size)

        # Calculate quantity
        if price > 0:
            return usd_amount / price
        return 0

    def _open_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        outlook: AIOutlook
    ):
        """Open a new position."""
        try:
            result = self.tester.place_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                trade_side="OPEN",
                order_type="MARKET",
                interpretation=outlook.interpretation
            )

            # Record trade in database
            trade = create_trade(
                simulation_id=self.simulation_id,
                symbol=symbol,
                side=side,
                action=f"OPEN_{side}",
                quantity=quantity,
                entry_price=price,
                fees=quantity * price * self.config.fees,
                interpretation=outlook.interpretation
            )
            self.current_trade_id = trade["id"]

            logger.info(f"{self.config.name}: Opened {side} position for {symbol}")

            # Send notification
            self.notifier.send_trade_opened(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                is_paper=True,
                simulation_id=self.simulation_id
            )

        except Exception as e:
            logger.error(f"Failed to open position: {e}")
            self.notifier.send_error(
                self.config.name,
                f"Failed to open position: {e}",
                simulation_id=self.simulation_id
            )

    def _close_position(
        self,
        symbol: str,
        position: Any,
        exit_price: float,
        outlook: AIOutlook
    ):
        """Close an existing position."""
        try:
            entry_price = position.avgOpenPrice
            quantity = position.qty
            side = position.side

            result = self.tester.flash_close_position(
                position_id=position.positionId,
                interpretation=outlook.interpretation
            )

            # Calculate PnL
            if side == "BUY":
                pnl = (exit_price - entry_price) * quantity
            else:
                pnl = (entry_price - exit_price) * quantity

            # Subtract fees
            fees = quantity * exit_price * self.config.fees
            pnl -= fees

            # Update trade in database
            if self.current_trade_id:
                update_trade(
                    self.current_trade_id,
                    exit_price=exit_price,
                    pnl=pnl,
                    closed_at=datetime.now(timezone.utc).isoformat()
                )
                self.current_trade_id = None

            logger.info(f"{self.config.name}: Closed {side} position for {symbol}, PnL: {pnl:.2f}")

            # Send notification
            self.notifier.send_trade_closed(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=pnl,
                is_paper=True,
                simulation_id=self.simulation_id
            )

        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            self.notifier.send_error(
                self.config.name,
                f"Failed to close position: {e}",
                simulation_id=self.simulation_id
            )

    def _wait_with_interrupt(self, seconds: int):
        """Wait for specified seconds but check for commands periodically."""
        interval = 5  # Check every 5 seconds
        elapsed = 0

        while elapsed < seconds and self.running and not self.paused:
            time.sleep(min(interval, seconds - elapsed))
            elapsed += interval
            self._process_commands()

    def _send_status(self, status: str, message: str = None):
        """Send status update to manager."""
        self.status_queue.put({
            "simulation_id": self.simulation_id,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def _cleanup(self):
        """Cleanup when worker exits."""
        logger.info(f"Simulation {self.config.name} cleanup")
        self._send_status("stopped")


def run_worker(
    simulation_id: str,
    config_dict: Dict[str, Any],
    control_queue: Queue,
    status_queue: Queue
):
    """
    Entry point for worker process.

    This function is called by multiprocessing.Process.
    """
    # Set up logging for this process
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s - SIM[{simulation_id[:8]}] - %(levelname)s - %(message)s"
    )

    # Handle SIGTERM gracefully
    def handle_sigterm(signum, frame):
        logger.info("Received SIGTERM, stopping...")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Parse config
    config = SimulationConfig(**config_dict)

    # Create and run worker
    worker = SimulationWorker(
        simulation_id=simulation_id,
        config=config,
        control_queue=control_queue,
        status_queue=status_queue
    )

    try:
        worker.run()
    except SystemExit:
        logger.info("Worker exiting due to signal")
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        status_queue.put({
            "simulation_id": simulation_id,
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
