"""
Database Module for AI Trading Bot

SQLite database setup with WAL mode for ACID transactions.
Manages simulations and notification history storage.
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
import json
import uuid

# Database configuration
DATABASE_DIR = Path("data")
DATABASE_FILE = DATABASE_DIR / "trading_bot.db"

logger = logging.getLogger(__name__)


def get_database_path() -> Path:
    """Get the database file path, ensuring directory exists."""
    DATABASE_DIR.mkdir(exist_ok=True)
    return DATABASE_FILE


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.

    Uses WAL mode for better concurrent access and ACID compliance.
    """
    db_path = get_database_path()
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    """Initialize the database with required tables."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Simulations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                config_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                pid INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                stopped_at TIMESTAMP,
                paused_at TIMESTAMP,
                error_message TEXT
            )
        """)

        # Simulation trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_trades (
                id TEXT PRIMARY KEY,
                simulation_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL,
                exit_price REAL,
                pnl REAL,
                fees REAL,
                interpretation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (simulation_id) REFERENCES simulations(id) ON DELETE CASCADE
            )
        """)

        # Notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                simulation_id TEXT,
                type TEXT NOT NULL,
                symbol TEXT,
                content TEXT NOT NULL,
                delivery_status TEXT NOT NULL DEFAULT 'pending',
                telegram_message_id TEXT,
                sent_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (simulation_id) REFERENCES simulations(id) ON DELETE SET NULL
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_simulations_status
            ON simulations(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_simulation
            ON notifications(simulation_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_status
            ON notifications(delivery_status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_simulation_trades_simulation
            ON simulation_trades(simulation_id)
        """)

        logger.info(f"Database initialized at {get_database_path()}")


def generate_id() -> str:
    """Generate a unique ID for database records."""
    return str(uuid.uuid4())


def now_utc() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# Simulation CRUD Operations
# ============================================================================

def create_simulation(name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new simulation record.

    Args:
        name: Display name for the simulation
        config: Configuration dictionary for the simulation

    Returns:
        The created simulation record
    """
    sim_id = generate_id()
    now = now_utc()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO simulations (id, name, config_json, status, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
        """, (sim_id, name, json.dumps(config), now, now))

    return get_simulation(sim_id)


def get_simulation(sim_id: str) -> Optional[Dict[str, Any]]:
    """Get a simulation by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM simulations WHERE id = ?", (sim_id,))
        row = cursor.fetchone()

        if row:
            return _row_to_simulation(row)
        return None


def list_simulations(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all simulations, optionally filtered by status.

    Args:
        status: Optional status filter (pending, running, paused, stopped, error)
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        if status:
            cursor.execute(
                "SELECT * FROM simulations WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM simulations ORDER BY created_at DESC")

        return [_row_to_simulation(row) for row in cursor.fetchall()]


def update_simulation(
    sim_id: str,
    status: Optional[str] = None,
    pid: Optional[int] = None,
    error_message: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Update a simulation record."""
    updates = ["updated_at = ?"]
    params = [now_utc()]

    if status is not None:
        updates.append("status = ?")
        params.append(status)

        # Set timestamp fields based on status
        if status == "running":
            updates.append("started_at = ?")
            params.append(now_utc())
        elif status == "stopped":
            updates.append("stopped_at = ?")
            params.append(now_utc())
        elif status == "paused":
            updates.append("paused_at = ?")
            params.append(now_utc())

    if pid is not None:
        updates.append("pid = ?")
        params.append(pid)

    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    if config is not None:
        updates.append("config_json = ?")
        params.append(json.dumps(config))

    params.append(sim_id)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE simulations SET {', '.join(updates)} WHERE id = ?",
            params
        )

    return get_simulation(sim_id)


def delete_simulation(sim_id: str) -> bool:
    """Delete a simulation and its related data."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM simulations WHERE id = ?", (sim_id,))
        return cursor.rowcount > 0


def _row_to_simulation(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a database row to a simulation dictionary."""
    return {
        "id": row["id"],
        "name": row["name"],
        "config": json.loads(row["config_json"]),
        "status": row["status"],
        "pid": row["pid"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "started_at": row["started_at"],
        "stopped_at": row["stopped_at"],
        "paused_at": row["paused_at"],
        "error_message": row["error_message"],
    }


# ============================================================================
# Simulation Trades Operations
# ============================================================================

def create_trade(
    simulation_id: str,
    symbol: str,
    side: str,
    action: str,
    quantity: float,
    entry_price: Optional[float] = None,
    exit_price: Optional[float] = None,
    pnl: Optional[float] = None,
    fees: Optional[float] = None,
    interpretation: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new trade record for a simulation."""
    trade_id = generate_id()
    now = now_utc()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO simulation_trades
            (id, simulation_id, symbol, side, action, quantity, entry_price,
             exit_price, pnl, fees, interpretation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (trade_id, simulation_id, symbol, side, action, quantity,
              entry_price, exit_price, pnl, fees, interpretation, now))

    return get_trade(trade_id)


def get_trade(trade_id: str) -> Optional[Dict[str, Any]]:
    """Get a trade by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM simulation_trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None


def get_simulation_trades(
    simulation_id: str,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get trades for a simulation."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM simulation_trades
            WHERE simulation_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (simulation_id, limit, offset))

        return [dict(row) for row in cursor.fetchall()]


def update_trade(
    trade_id: str,
    exit_price: Optional[float] = None,
    pnl: Optional[float] = None,
    closed_at: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update a trade record (typically when closing)."""
    updates = []
    params = []

    if exit_price is not None:
        updates.append("exit_price = ?")
        params.append(exit_price)

    if pnl is not None:
        updates.append("pnl = ?")
        params.append(pnl)

    if closed_at is not None:
        updates.append("closed_at = ?")
        params.append(closed_at)

    if not updates:
        return get_trade(trade_id)

    params.append(trade_id)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE simulation_trades SET {', '.join(updates)} WHERE id = ?",
            params
        )

    return get_trade(trade_id)


# ============================================================================
# Notification Operations
# ============================================================================

def create_notification(
    notification_type: str,
    content: str,
    simulation_id: Optional[str] = None,
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new notification record.

    Args:
        notification_type: Type of notification (signal, trade_opened, trade_closed, error, daily_summary)
        content: The notification content/message
        simulation_id: Optional associated simulation
        symbol: Optional trading symbol
    """
    notif_id = generate_id()
    now = now_utc()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notifications
            (id, simulation_id, type, symbol, content, delivery_status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (notif_id, simulation_id, notification_type, symbol, content, now))

    return get_notification(notif_id)


def get_notification(notif_id: str) -> Optional[Dict[str, Any]]:
    """Get a notification by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notifications WHERE id = ?", (notif_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None


def list_notifications(
    simulation_id: Optional[str] = None,
    delivery_status: Optional[str] = None,
    notification_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List notifications with optional filters.

    Args:
        simulation_id: Filter by simulation
        delivery_status: Filter by status (pending, sent, failed)
        notification_type: Filter by type
        limit: Maximum number of results
        offset: Pagination offset
    """
    conditions = []
    params = []

    if simulation_id:
        conditions.append("simulation_id = ?")
        params.append(simulation_id)

    if delivery_status:
        conditions.append("delivery_status = ?")
        params.append(delivery_status)

    if notification_type:
        conditions.append("type = ?")
        params.append(notification_type)

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    params.extend([limit, offset])

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * FROM notifications
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params)

        return [dict(row) for row in cursor.fetchall()]


def update_notification(
    notif_id: str,
    delivery_status: Optional[str] = None,
    telegram_message_id: Optional[str] = None,
    error_message: Optional[str] = None,
    increment_retry: bool = False
) -> Optional[Dict[str, Any]]:
    """Update a notification record."""
    updates = []
    params = []

    if delivery_status is not None:
        updates.append("delivery_status = ?")
        params.append(delivery_status)

        if delivery_status == "sent":
            updates.append("sent_at = ?")
            params.append(now_utc())

    if telegram_message_id is not None:
        updates.append("telegram_message_id = ?")
        params.append(telegram_message_id)

    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    if increment_retry:
        updates.append("retry_count = retry_count + 1")

    if not updates:
        return get_notification(notif_id)

    params.append(notif_id)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE notifications SET {', '.join(updates)} WHERE id = ?",
            params
        )

    return get_notification(notif_id)


def get_notification_stats() -> Dict[str, Any]:
    """Get notification statistics."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Total counts by status
        cursor.execute("""
            SELECT delivery_status, COUNT(*) as count
            FROM notifications
            GROUP BY delivery_status
        """)
        status_counts = {row["delivery_status"]: row["count"] for row in cursor.fetchall()}

        # Counts by type
        cursor.execute("""
            SELECT type, COUNT(*) as count
            FROM notifications
            GROUP BY type
        """)
        type_counts = {row["type"]: row["count"] for row in cursor.fetchall()}

        # Recent failures
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM notifications
            WHERE delivery_status = 'failed'
            AND created_at > datetime('now', '-24 hours')
        """)
        recent_failures = cursor.fetchone()["count"]

        return {
            "by_status": status_counts,
            "by_type": type_counts,
            "total": sum(status_counts.values()),
            "recent_failures_24h": recent_failures,
        }


def get_simulation_stats(simulation_id: str) -> Dict[str, Any]:
    """Get statistics for a specific simulation."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Trade stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(COALESCE(pnl, 0)) as total_pnl,
                SUM(COALESCE(fees, 0)) as total_fees,
                AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
            FROM simulation_trades
            WHERE simulation_id = ?
        """, (simulation_id,))

        row = cursor.fetchone()

        total_trades = row["total_trades"] or 0
        winning_trades = row["winning_trades"] or 0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": row["losing_trades"] or 0,
            "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": row["total_pnl"] or 0,
            "total_fees": row["total_fees"] or 0,
            "avg_win": row["avg_win"] or 0,
            "avg_loss": row["avg_loss"] or 0,
        }
