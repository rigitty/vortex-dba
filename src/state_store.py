"""State persistence layer for VortexDBA.

Stores applied indexes, benchmark history, and agent decisions
in a SQLite database for tracking and deduplication.
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

from config import get_config


DB_PATH = Path(__file__).parent.parent / "data" / "vortex_state.db"


@dataclass
class AppliedIndex:
    index_name: str
    table_name: str
    columns: list[str]
    create_sql: str
    applied_at: str
    rolled_back_at: str | None = None
    reason: str = ""


@dataclass
class BenchmarkRecord:
    query_name: str
    mean_ms: float
    median_ms: float
    measured_at: str
    index_snapshot: str


@dataclass
class AgentDecision:
    decision_type: str
    details: str
    created_at: str


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """Ensure that the state tables and indexes exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS applied_indexes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            index_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            columns TEXT NOT NULL,
            create_sql TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            rolled_back_at TEXT,
            reason TEXT
        );

        CREATE TABLE IF NOT EXISTS benchmark_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_name TEXT NOT NULL,
            mean_ms REAL NOT NULL,
            median_ms REAL,
            measured_at TEXT NOT NULL,
            index_snapshot TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_type TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_applied_indexes_name
            ON applied_indexes(index_name);
        CREATE INDEX IF NOT EXISTS idx_applied_indexes_table
            ON applied_indexes(table_name);
        CREATE INDEX IF NOT EXISTS idx_benchmark_history_query
            ON benchmark_history(query_name);
        CREATE INDEX IF NOT EXISTS idx_agent_decisions_type
            ON agent_decisions(decision_type);
    """)
    conn.commit()


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite state database, ensuring tables exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    return conn


def init_db() -> None:
    """Initialize the state database schema."""
    conn = _get_connection()
    conn.close()


def record_index_applied(index_name: str, table_name: str, columns: list[str],
                         create_sql: str, reason: str = "") -> None:
    """Record that an index was applied."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO applied_indexes
               (index_name, table_name, columns, create_sql, applied_at, reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (index_name, table_name, json.dumps(columns), create_sql,
             datetime.now().isoformat(), reason),
        )
        conn.commit()
    finally:
        conn.close()


def record_index_rolled_back(index_name: str) -> None:
    """Record that an index was rolled back."""
    conn = _get_connection()
    try:
        conn.execute(
            """UPDATE applied_indexes
               SET rolled_back_at = ?
               WHERE index_name = ? AND rolled_back_at IS NULL""",
            (datetime.now().isoformat(), index_name),
        )
        conn.commit()
    finally:
        conn.close()


def record_benchmark(query_name: str, mean_ms: float, median_ms: float,
                     index_snapshot: str = "") -> None:
    """Record a benchmark measurement."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO benchmark_history
               (query_name, mean_ms, median_ms, measured_at, index_snapshot)
               VALUES (?, ?, ?, ?, ?)""",
            (query_name, mean_ms, median_ms, datetime.now().isoformat(), index_snapshot),
        )
        conn.commit()
    finally:
        conn.close()


def record_baseline(query_name: str, mean_ms: float) -> None:
    """Record or update measured unindexed baseline execution time."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO benchmark_history
               (query_name, mean_ms, median_ms, measured_at, index_snapshot)
               VALUES (?, ?, ?, ?, 'baseline')""",
            (query_name, mean_ms, mean_ms, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_baseline(query_name: str) -> float | None:
    """Get the most recent unindexed baseline measurement."""
    conn = _get_connection()
    try:
        row = conn.execute(
            """SELECT mean_ms FROM benchmark_history
               WHERE query_name = ? AND index_snapshot = 'baseline'
               ORDER BY id DESC LIMIT 1""",
            (query_name,)
        ).fetchone()
        return row["mean_ms"] if row else None
    finally:
        conn.close()


def record_decision(decision_type: str, details: str) -> None:
    """Record an agent decision."""
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO agent_decisions
               (decision_type, details, created_at)
               VALUES (?, ?, ?)""",
            (decision_type, details, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_active_indexes() -> list[AppliedIndex]:
    """Get all currently active (non-rolled-back) indexes."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT index_name, table_name, columns, create_sql,
                      applied_at, rolled_back_at, reason
               FROM applied_indexes
               WHERE rolled_back_at IS NULL
               ORDER BY applied_at DESC"""
        ).fetchall()
        return [
            AppliedIndex(
                index_name=r["index_name"],
                table_name=r["table_name"],
                columns=json.loads(r["columns"]),
                create_sql=r["create_sql"],
                applied_at=r["applied_at"],
                rolled_back_at=r["rolled_back_at"],
                reason=r["reason"],
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_index_count_for_table(table_name: str) -> int:
    """Get the number of active indexes for a table."""
    conn = _get_connection()
    try:
        row = conn.execute(
            """SELECT COUNT(*) as cnt
               FROM applied_indexes
               WHERE table_name = ? AND rolled_back_at IS NULL""",
            (table_name,),
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_total_active_index_count() -> int:
    """Get the total number of active indexes."""
    conn = _get_connection()
    try:
        row = conn.execute(
            """SELECT COUNT(*) as cnt
               FROM applied_indexes
               WHERE rolled_back_at IS NULL"""
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def was_index_applied(index_name: str) -> bool:
    """Check if an index was previously applied (and not rolled back)."""
    conn = _get_connection()
    try:
        row = conn.execute(
            """SELECT COUNT(*) as cnt
               FROM applied_indexes
               WHERE index_name = ? AND rolled_back_at IS NULL""",
            (index_name,),
        ).fetchone()
        return row["cnt"] > 0 if row else False
    finally:
        conn.close()


def get_last_change_time(table_name: str) -> datetime | None:
    """Get the time of the last index change for a table."""
    conn = _get_connection()
    try:
        row = conn.execute(
            """SELECT applied_at
               FROM applied_indexes
               WHERE table_name = ?
               ORDER BY applied_at DESC
               LIMIT 1""",
            (table_name,),
        ).fetchone()
        if row:
            return datetime.fromisoformat(row["applied_at"])
        return None
    finally:
        conn.close()


def get_benchmark_history(query_name: str, limit: int = 10) -> list[BenchmarkRecord]:
    """Get benchmark history for a query."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT query_name, mean_ms, median_ms, measured_at, index_snapshot
               FROM benchmark_history
               WHERE query_name = ?
               ORDER BY measured_at DESC
               LIMIT ?""",
            (query_name, limit),
        ).fetchall()
        return [
            BenchmarkRecord(
                query_name=r["query_name"],
                mean_ms=r["mean_ms"],
                median_ms=r["median_ms"],
                measured_at=r["measured_at"],
                index_snapshot=r["index_snapshot"],
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_recent_decisions(limit: int = 20) -> list[AgentDecision]:
    """Get recent agent decisions."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT decision_type, details, created_at
               FROM agent_decisions
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            AgentDecision(
                decision_type=r["decision_type"],
                details=r["details"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_index_snapshot() -> str:
    """Get a snapshot of currently active index names."""
    indexes = get_active_indexes()
    return ",".join(sorted(idx.index_name for idx in indexes))
