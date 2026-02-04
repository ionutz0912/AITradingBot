"""
Tests for lib/database.py - Database operations module
"""

import pytest
import json
from datetime import datetime, timezone

from lib.database import (
    init_database,
    create_simulation,
    get_simulation,
    list_simulations,
    update_simulation,
    delete_simulation,
    create_trade,
    get_trade,
    get_simulation_trades,
    update_trade,
    create_notification,
    get_notification,
    list_notifications,
    update_notification,
    get_notification_stats,
    get_simulation_stats,
    generate_id,
    now_utc,
)


class TestDatabaseInitialization:
    """Test database initialization."""

    def test_init_database(self, test_db):
        """Test database initialization creates all tables."""
        with get_connection() as conn:
            cursor = conn.cursor()

            # Check simulations table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='simulations'"
            )
            assert cursor.fetchone() is not None

            # Check simulation_trades table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='simulation_trades'"
            )
            assert cursor.fetchone() is not None

            # Check notifications table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'"
            )
            assert cursor.fetchone() is not None


class TestSimulationCRUD:
    """Test simulation CRUD operations."""

    def test_create_simulation(self, test_db):
        """Test creating a simulation."""
        config = {"symbol": "BTCUSDT", "initial_capital": 10000}
        sim = create_simulation("Test Simulation", config)

        assert sim["id"] is not None
        assert sim["name"] == "Test Simulation"
        assert sim["status"] == "pending"
        assert json.loads(sim["config_json"])["symbol"] == "BTCUSDT"

    def test_get_simulation(self, test_db):
        """Test getting a simulation by ID."""
        config = {"symbol": "ETHUSDT"}
        created_sim = create_simulation("Test", config)

        fetched_sim = get_simulation(created_sim["id"])

        assert fetched_sim is not None
        assert fetched_sim["id"] == created_sim["id"]
        assert fetched_sim["name"] == "Test"

    def test_get_nonexistent_simulation(self, test_db):
        """Test getting a non-existent simulation."""
        sim = get_simulation("nonexistent-id")

        assert sim is None

    def test_list_simulations(self, test_db):
        """Test listing all simulations."""
        create_simulation("Sim 1", {})
        create_simulation("Sim 2", {})

        sims = list_simulations()

        assert len(sims) == 2

    def test_list_simulations_with_status_filter(self, test_db):
        """Test listing simulations filtered by status."""
        sim1 = create_simulation("Running Sim", {})
        sim2 = create_simulation("Stopped Sim", {})

        update_simulation(sim1["id"], status="running")
        update_simulation(sim2["id"], status="stopped")

        running_sims = list_simulations(status="running")

        assert len(running_sims) == 1
        assert running_sims[0]["status"] == "running"

    def test_update_simulation_status(self, test_db):
        """Test updating simulation status."""
        sim = create_simulation("Test", {})

        updated_sim = update_simulation(sim["id"], status="running")

        assert updated_sim["status"] == "running"
        assert updated_sim["started_at"] is not None

    def test_update_simulation_multiple_fields(self, test_db):
        """Test updating multiple simulation fields."""
        sim = create_simulation("Test", {})

        updated_sim = update_simulation(
            sim["id"],
            status="error",
            error_message="Test error",
            pid=12345
        )

        assert updated_sim["status"] == "error"
        assert updated_sim["error_message"] == "Test error"
        assert updated_sim["pid"] == 12345

    def test_delete_simulation(self, test_db):
        """Test deleting a simulation."""
        sim = create_simulation("Test", {})

        result = delete_simulation(sim["id"])

        assert result is True
        assert get_simulation(sim["id"]) is None


class TestTradeCRUD:
    """Test trade CRUD operations."""

    def test_create_trade(self, test_db):
        """Test creating a trade record."""
        sim = create_simulation("Test", {})

        trade = create_trade(
            simulation_id=sim["id"],
            symbol="BTCUSDT",
            side="buy",
            action="OPEN_LONG",
            quantity=0.1,
            entry_price=50000.0,
            fees=5.0,
            interpretation="Bullish"
        )

        assert trade["id"] is not None
        assert trade["symbol"] == "BTCUSDT"
        assert trade["quantity"] == 0.1

    def test_get_trade(self, test_db):
        """Test getting a trade by ID."""
        sim = create_simulation("Test", {})
        created_trade = create_trade(
            simulation_id=sim["id"],
            symbol="ETHUSDT",
            side="sell",
            action="CLOSE_LONG",
            quantity=1.0,
            exit_price=3000.0,
            pnl=100.0
        )

        fetched_trade = get_trade(created_trade["id"])

        assert fetched_trade is not None
        assert fetched_trade["symbol"] == "ETHUSDT"
        assert fetched_trade["pnl"] == 100.0

    def test_get_simulation_trades(self, test_db):
        """Test getting trades for a simulation."""
        sim = create_simulation("Test", {})

        # Create multiple trades
        for i in range(5):
            create_trade(
                simulation_id=sim["id"],
                symbol="BTCUSDT",
                side="buy",
                action="OPEN_LONG",
                quantity=0.1
            )

        trades = get_simulation_trades(sim["id"])

        assert len(trades) == 5

    def test_get_simulation_trades_pagination(self, test_db):
        """Test trade pagination."""
        sim = create_simulation("Test", {})

        # Create 10 trades
        for i in range(10):
            create_trade(
                simulation_id=sim["id"],
                symbol="BTCUSDT",
                side="buy",
                action="OPEN_LONG",
                quantity=0.1
            )

        # Get first 5 trades
        trades_page1 = get_simulation_trades(sim["id"], limit=5, offset=0)
        trades_page2 = get_simulation_trades(sim["id"], limit=5, offset=5)

        assert len(trades_page1) == 5
        assert len(trades_page2) == 5
        assert trades_page1[0]["id"] != trades_page2[0]["id"]

    def test_update_trade(self, test_db):
        """Test updating a trade record."""
        sim = create_simulation("Test", {})
        trade = create_trade(
            simulation_id=sim["id"],
            symbol="BTCUSDT",
            side="buy",
            action="OPEN_LONG",
            quantity=0.1,
            entry_price=50000.0
        )

        updated_trade = update_trade(
            trade["id"],
            exit_price=52000.0,
            pnl=200.0,
            closed_at=now_utc()
        )

        assert updated_trade["exit_price"] == 52000.0
        assert updated_trade["pnl"] == 200.0
        assert updated_trade["closed_at"] is not None


class TestNotificationCRUD:
    """Test notification CRUD operations."""

    def test_create_notification(self, test_db):
        """Test creating a notification."""
        sim = create_simulation("Test", {})

        notif = create_notification(
            notification_type="signal",
            content="Test notification",
            simulation_id=sim["id"],
            symbol="BTCUSDT"
        )

        assert notif["id"] is not None
        assert notif["type"] == "signal"
        assert notif["delivery_status"] == "pending"

    def test_get_notification(self, test_db):
        """Test getting a notification by ID."""
        created_notif = create_notification(
            notification_type="trade_opened",
            content="Trade opened"
        )

        fetched_notif = get_notification(created_notif["id"])

        assert fetched_notif is not None
        assert fetched_notif["type"] == "trade_opened"

    def test_list_notifications(self, test_db):
        """Test listing notifications."""
        create_notification("signal", "Notification 1")
        create_notification("trade_opened", "Notification 2")

        notifs = list_notifications()

        assert len(notifs) == 2

    def test_list_notifications_with_filters(self, test_db):
        """Test listing notifications with filters."""
        sim = create_simulation("Test", {})

        create_notification("signal", "Notif 1", simulation_id=sim["id"])
        create_notification("error", "Notif 2")

        # Filter by simulation
        sim_notifs = list_notifications(simulation_id=sim["id"])
        assert len(sim_notifs) == 1

        # Filter by type
        error_notifs = list_notifications(notification_type="error")
        assert len(error_notifs) == 1

    def test_update_notification(self, test_db):
        """Test updating a notification."""
        notif = create_notification("signal", "Test")

        updated_notif = update_notification(
            notif["id"],
            delivery_status="sent",
            telegram_message_id="12345"
        )

        assert updated_notif["delivery_status"] == "sent"
        assert updated_notif["telegram_message_id"] == "12345"
        assert updated_notif["sent_at"] is not None

    def test_update_notification_retry_increment(self, test_db):
        """Test incrementing notification retry count."""
        notif = create_notification("signal", "Test")

        # Increment retry count
        updated_notif = update_notification(
            notif["id"],
            delivery_status="failed",
            error_message="Connection timeout",
            increment_retry=True
        )

        assert updated_notif["retry_count"] == 1
        assert updated_notif["error_message"] == "Connection timeout"


class TestStatistics:
    """Test statistics functions."""

    def test_get_simulation_stats(self, test_db):
        """Test getting simulation statistics."""
        sim = create_simulation("Test", {})

        # Create winning and losing trades
        create_trade(
            simulation_id=sim["id"],
            symbol="BTCUSDT",
            side="buy",
            action="CLOSE_LONG",
            quantity=0.1,
            pnl=100.0,
            fees=1.0
        )
        create_trade(
            simulation_id=sim["id"],
            symbol="BTCUSDT",
            side="buy",
            action="CLOSE_LONG",
            quantity=0.1,
            pnl=-50.0,
            fees=1.0
        )

        stats = get_simulation_stats(sim["id"])

        assert stats["total_trades"] == 2
        assert stats["winning_trades"] == 1
        assert stats["losing_trades"] == 1
        assert stats["win_rate"] == 50.0
        assert stats["total_pnl"] == 50.0
        assert stats["total_fees"] == 2.0

    def test_get_simulation_stats_empty(self, test_db):
        """Test statistics for simulation with no trades."""
        sim = create_simulation("Test", {})

        stats = get_simulation_stats(sim["id"])

        assert stats["total_trades"] == 0
        assert stats["win_rate"] == 0.0
        assert stats["total_pnl"] == 0.0

    def test_get_notification_stats(self, test_db):
        """Test getting notification statistics."""
        create_notification("signal", "Test 1")
        create_notification("trade_opened", "Test 2")

        notif1 = create_notification("signal", "Test 3")
        update_notification(notif1["id"], delivery_status="sent")

        notif2 = create_notification("error", "Test 4")
        update_notification(notif2["id"], delivery_status="failed")

        stats = get_notification_stats()

        assert stats["total"] == 4
        assert stats["by_status"]["pending"] == 2
        assert stats["by_status"]["sent"] == 1
        assert stats["by_status"]["failed"] == 1
        assert stats["by_type"]["signal"] == 2


class TestHelperFunctions:
    """Test utility helper functions."""

    def test_generate_id(self):
        """Test ID generation."""
        id1 = generate_id()
        id2 = generate_id()

        assert id1 != id2
        assert len(id1) > 0

    def test_now_utc(self):
        """Test UTC timestamp generation."""
        timestamp = now_utc()

        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format


class TestForeignKeys:
    """Test foreign key constraints."""

    def test_cascade_delete_simulation_trades(self, test_db):
        """Test that deleting simulation cascades to trades."""
        sim = create_simulation("Test", {})

        # Create trade
        trade = create_trade(
            simulation_id=sim["id"],
            symbol="BTCUSDT",
            side="buy",
            action="OPEN_LONG",
            quantity=0.1
        )

        # Delete simulation
        delete_simulation(sim["id"])

        # Trade should be deleted too
        fetched_trade = get_trade(trade["id"])
        assert fetched_trade is None

    def test_set_null_simulation_notifications(self, test_db):
        """Test that deleting simulation sets notification simulation_id to NULL."""
        sim = create_simulation("Test", {})

        # Create notification
        notif = create_notification(
            "signal",
            "Test",
            simulation_id=sim["id"]
        )

        # Delete simulation
        delete_simulation(sim["id"])

        # Notification should still exist but with NULL simulation_id
        fetched_notif = get_notification(notif["id"])
        assert fetched_notif is not None
        assert fetched_notif["simulation_id"] is None
