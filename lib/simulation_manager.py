"""
Simulation Manager for AI Trading Bot

Manages up to 5 parallel trading simulations using multiprocessing.
Provides start/stop/pause/resume controls and status tracking.
"""

import atexit
import logging
import signal
from datetime import datetime, timezone
from multiprocessing import Process, Queue
from threading import Thread, Lock
from typing import Any, Dict, List, Optional

from .config import SimulationConfig
from .database import (
    create_simulation,
    get_simulation,
    list_simulations,
    update_simulation,
    delete_simulation,
    get_simulation_stats,
    init_database,
)
from .simulation_worker import run_worker, CMD_STOP, CMD_PAUSE, CMD_RESUME

logger = logging.getLogger(__name__)

# Maximum number of concurrent simulations
MAX_SIMULATIONS = 5


class SimulationManager:
    """
    Manages multiple trading simulations running in parallel.

    Features:
    - Start/stop/pause/resume individual simulations
    - SQLite-backed state persistence
    - Process lifecycle management
    - Status monitoring
    """

    _instance: Optional["SimulationManager"] = None
    _lock = Lock()

    def __new__(cls):
        """Singleton pattern for global access."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the simulation manager."""
        if self._initialized:
            return

        self._initialized = True
        self._processes: Dict[str, Process] = {}
        self._control_queues: Dict[str, Queue] = {}
        self._status_queue = Queue()
        self._running = False

        # Initialize database
        init_database()

        # Start status monitor thread
        self._status_thread: Optional[Thread] = None

        # Register cleanup on exit
        atexit.register(self.shutdown)

        logger.info("SimulationManager initialized")

    def start(self):
        """Start the manager and recover any running simulations."""
        if self._running:
            return

        self._running = True

        # Start status monitor thread
        self._status_thread = Thread(target=self._monitor_status, daemon=True)
        self._status_thread.start()

        # Recover simulations that were running before restart
        self._recover_simulations()

        logger.info("SimulationManager started")

    def shutdown(self):
        """Shutdown all simulations and cleanup."""
        if not self._running:
            return

        logger.info("Shutting down SimulationManager...")
        self._running = False

        # Stop all running simulations
        for sim_id in list(self._processes.keys()):
            try:
                self._stop_simulation_process(sim_id)
            except Exception as e:
                logger.error(f"Error stopping simulation {sim_id}: {e}")

        # Wait for processes to terminate
        for sim_id, process in list(self._processes.items()):
            try:
                process.join(timeout=5)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)
            except Exception as e:
                logger.error(f"Error joining process {sim_id}: {e}")

        self._processes.clear()
        self._control_queues.clear()

        logger.info("SimulationManager shutdown complete")

    def _recover_simulations(self):
        """Recover simulations that were running before restart."""
        # Get simulations that should be running
        running_sims = list_simulations(status="running")
        paused_sims = list_simulations(status="paused")

        for sim in running_sims + paused_sims:
            logger.info(f"Recovering simulation: {sim['name']} ({sim['status']})")
            # Mark as stopped - user can restart manually
            update_simulation(sim["id"], status="stopped", error_message="Recovered after restart")

    def create_simulation(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new simulation.

        Args:
            name: Display name for the simulation
            config: Simulation configuration dict

        Returns:
            Created simulation record

        Raises:
            ValueError: If max simulations reached or invalid config
        """
        # Check limit
        all_sims = list_simulations()
        active_count = len([s for s in all_sims if s["status"] in ("pending", "running", "paused")])

        if active_count >= MAX_SIMULATIONS:
            raise ValueError(f"Maximum of {MAX_SIMULATIONS} simulations allowed")

        # Validate config
        try:
            SimulationConfig(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")

        # Create in database
        simulation = create_simulation(name, config)
        logger.info(f"Created simulation: {name} ({simulation['id']})")

        return simulation

    def start_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """
        Start a simulation.

        Args:
            simulation_id: ID of the simulation to start

        Returns:
            Updated simulation record

        Raises:
            ValueError: If simulation not found or already running
        """
        simulation = get_simulation(simulation_id)
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")

        if simulation["status"] == "running":
            raise ValueError(f"Simulation {simulation['name']} is already running")

        if simulation_id in self._processes:
            raise ValueError(f"Simulation {simulation['name']} has an active process")

        # Check running count
        running_count = len([p for p in self._processes.values() if p.is_alive()])
        if running_count >= MAX_SIMULATIONS:
            raise ValueError(f"Maximum of {MAX_SIMULATIONS} concurrent simulations")

        # Create queues
        control_queue = Queue()
        self._control_queues[simulation_id] = control_queue

        # Start worker process
        process = Process(
            target=run_worker,
            args=(simulation_id, simulation["config"], control_queue, self._status_queue),
            daemon=True,
            name=f"sim-{simulation['name']}"
        )
        process.start()

        self._processes[simulation_id] = process

        # Update database
        simulation = update_simulation(
            simulation_id,
            status="running",
            pid=process.pid
        )

        logger.info(f"Started simulation: {simulation['name']} (PID: {process.pid})")
        return simulation

    def stop_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """
        Stop a running simulation.

        Args:
            simulation_id: ID of the simulation to stop

        Returns:
            Updated simulation record
        """
        simulation = get_simulation(simulation_id)
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")

        if simulation["status"] not in ("running", "paused"):
            raise ValueError(f"Simulation {simulation['name']} is not running")

        self._stop_simulation_process(simulation_id)

        simulation = update_simulation(simulation_id, status="stopped")
        logger.info(f"Stopped simulation: {simulation['name']}")
        return simulation

    def pause_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """
        Pause a running simulation.

        Args:
            simulation_id: ID of the simulation to pause

        Returns:
            Updated simulation record
        """
        simulation = get_simulation(simulation_id)
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")

        if simulation["status"] != "running":
            raise ValueError(f"Simulation {simulation['name']} is not running")

        # Send pause command
        if simulation_id in self._control_queues:
            self._control_queues[simulation_id].put(CMD_PAUSE)

        simulation = update_simulation(simulation_id, status="paused")
        logger.info(f"Paused simulation: {simulation['name']}")
        return simulation

    def resume_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """
        Resume a paused simulation.

        Args:
            simulation_id: ID of the simulation to resume

        Returns:
            Updated simulation record
        """
        simulation = get_simulation(simulation_id)
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")

        if simulation["status"] != "paused":
            raise ValueError(f"Simulation {simulation['name']} is not paused")

        # If process exists, send resume command
        if simulation_id in self._control_queues:
            self._control_queues[simulation_id].put(CMD_RESUME)
            simulation = update_simulation(simulation_id, status="running")
        else:
            # Process died, need to restart
            simulation = self.start_simulation(simulation_id)

        logger.info(f"Resumed simulation: {simulation['name']}")
        return simulation

    def delete_simulation(self, simulation_id: str) -> bool:
        """
        Delete a simulation.

        Args:
            simulation_id: ID of the simulation to delete

        Returns:
            True if deleted successfully
        """
        simulation = get_simulation(simulation_id)
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")

        # Stop if running
        if simulation["status"] in ("running", "paused"):
            self._stop_simulation_process(simulation_id)

        # Delete from database
        result = delete_simulation(simulation_id)
        logger.info(f"Deleted simulation: {simulation['name']}")
        return result

    def get_simulation(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Get a simulation by ID with live status."""
        simulation = get_simulation(simulation_id)
        if simulation:
            simulation = self._enrich_simulation(simulation)
        return simulation

    def list_simulations(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all simulations with live status."""
        simulations = list_simulations(status)
        return [self._enrich_simulation(s) for s in simulations]

    def get_simulation_stats(self, simulation_id: str) -> Dict[str, Any]:
        """Get statistics for a simulation."""
        return get_simulation_stats(simulation_id)

    def _enrich_simulation(self, simulation: Dict[str, Any]) -> Dict[str, Any]:
        """Add live process status to simulation record."""
        sim_id = simulation["id"]

        # Check if process is actually running
        if sim_id in self._processes:
            process = self._processes[sim_id]
            simulation["process_alive"] = process.is_alive()

            # Update status if process died unexpectedly
            if not process.is_alive() and simulation["status"] in ("running", "paused"):
                update_simulation(sim_id, status="stopped", error_message="Process terminated unexpectedly")
                simulation["status"] = "stopped"
                self._cleanup_process(sim_id)
        else:
            simulation["process_alive"] = False

        return simulation

    def _stop_simulation_process(self, simulation_id: str):
        """Stop a simulation's process."""
        # Send stop command
        if simulation_id in self._control_queues:
            try:
                self._control_queues[simulation_id].put(CMD_STOP)
            except Exception:
                pass

        # Wait for graceful shutdown
        if simulation_id in self._processes:
            process = self._processes[simulation_id]
            process.join(timeout=10)

            # Force terminate if still alive
            if process.is_alive():
                logger.warning(f"Force terminating simulation {simulation_id}")
                process.terminate()
                process.join(timeout=5)

                if process.is_alive():
                    process.kill()

        self._cleanup_process(simulation_id)

    def _cleanup_process(self, simulation_id: str):
        """Cleanup process resources."""
        self._processes.pop(simulation_id, None)
        self._control_queues.pop(simulation_id, None)

    def _monitor_status(self):
        """Background thread to monitor worker status updates."""
        while self._running:
            try:
                # Non-blocking get with timeout
                status = self._status_queue.get(timeout=1)

                sim_id = status.get("simulation_id")
                status_value = status.get("status")
                message = status.get("message")

                logger.debug(f"Status update: {sim_id} -> {status_value}")

                # Handle status updates
                if status_value == "error":
                    update_simulation(sim_id, status="error", error_message=message)
                    self._cleanup_process(sim_id)
                elif status_value == "stopped":
                    self._cleanup_process(sim_id)

            except Exception:
                # Queue.get timeout or other error
                pass

            # Check for dead processes
            self._check_processes()

    def _check_processes(self):
        """Check for dead processes and cleanup."""
        for sim_id in list(self._processes.keys()):
            process = self._processes[sim_id]
            if not process.is_alive():
                simulation = get_simulation(sim_id)
                if simulation and simulation["status"] in ("running", "paused"):
                    update_simulation(
                        sim_id,
                        status="stopped",
                        error_message="Process terminated unexpectedly"
                    )
                self._cleanup_process(sim_id)


# Global manager instance
_manager: Optional[SimulationManager] = None


def get_simulation_manager() -> SimulationManager:
    """Get or create the global simulation manager instance."""
    global _manager
    if _manager is None:
        _manager = SimulationManager()
    return _manager


def init_simulation_manager() -> SimulationManager:
    """Initialize and start the simulation manager."""
    manager = get_simulation_manager()
    manager.start()
    return manager
