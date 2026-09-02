"""Safety guardrails for VortexDBA auto-remediation.

Enforces policies to prevent dangerous operations in production:
- Maximum index count limits
- Cooldown between changes
- Index name validation
- Dynamic existing index discovery
"""

from datetime import datetime, timedelta

from config import get_config
from db_connection import execute_query
from state_store import (
    get_index_count_for_table,
    get_total_active_index_count,
    was_index_applied,
    get_last_change_time,
)


class SafetyViolation(Exception):
    """Raised when a safety policy is violated."""
    pass


def get_existing_indexes_from_db() -> dict[str, list[str]]:
    """Query SQL Server sys.indexes to get all existing indexes dynamically."""
    query = """
        SELECT i.name AS indexname, t.name AS tablename
        FROM sys.indexes i
        JOIN sys.tables t ON t.object_id = i.object_id
        WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL
    """
    results = execute_query(query)
    index_map: dict[str, list[str]] = {}
    for r in (results or []):
        idx_name = r["indexname"]
        tbl_name = r["tablename"]
        if tbl_name not in index_map:
            index_map[tbl_name] = []
        index_map[tbl_name].append(idx_name)
    return index_map


def get_index_columns_from_db(index_name: str) -> list[str]:
    """Get the columns of an existing SQL Server index."""
    query = """
        SELECT c.name AS attname
        FROM sys.index_columns ic
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        JOIN sys.indexes i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
        WHERE i.name = %s AND ic.is_included_column = 0
        ORDER BY ic.key_ordinal
    """
    results = execute_query(query, (index_name,))
    return [r["attname"] for r in (results or [])]


def can_apply_index(table_name: str, index_name: str, ignore_cooldown: bool = False) -> tuple[bool, str]:
    """Check if an index can be safely applied.

    Returns (allowed, reason).
    """
    config = get_config()

    # Check if remediation is enabled
    if not config.remediation.enabled:
        return False, "Remediation is disabled in configuration"

    # Check if already applied
    if was_index_applied(index_name):
        return False, f"Index {index_name} was already applied"

    # Check if exists in database
    existing = get_existing_indexes_from_db()
    for tbl, indexes in existing.items():
        if index_name in indexes:
            return False, f"Index {index_name} already exists in database"

    # Check max indexes per table (in SQL Server)
    db_table_indexes = len(existing.get(table_name, []))
    if db_table_indexes >= config.remediation.max_indexes_per_table:
        return False, (
            f"Table {table_name} already has {db_table_indexes} indexes "
            f"(max: {config.remediation.max_indexes_per_table})"
        )

    # Check total index limit (in SQL Server)
    total_db_indexes = sum(len(idxs) for idxs in existing.values())
    if total_db_indexes >= config.remediation.max_indexes_total:
        return False, (
            f"Total database indexes: {total_db_indexes} "
            f"(max: {config.remediation.max_indexes_total})"
        )

    # Check cooldown
    if not ignore_cooldown:
        last_change = get_last_change_time(table_name)
        if last_change:
            cooldown = timedelta(minutes=config.remediation.cooldown_minutes)
            now = datetime.now()
            if now - last_change < cooldown:
                remaining = cooldown - (now - last_change)
                return False, (
                    f"Cooldown active for {table_name}. "
                    f"Wait {remaining.seconds // 60} more minutes"
                )

    return True, "OK"


def validate_index_name(index_name: str) -> bool:
    """Validate that an index name follows conventions."""
    if not index_name:
        return False
    if not index_name.startswith("idx_"):
        return False
    if len(index_name) > 128:  # SQL Server identifier limit
        return False
    # Check for valid characters
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_")
    if not all(c in allowed for c in index_name.lower()):
        return False
    return True


def check_safety(table_name: str, index_name: str, ignore_cooldown: bool = False) -> None:
    """Run all safety checks. Raises SafetyViolation if any fail."""
    allowed, reason = can_apply_index(table_name, index_name, ignore_cooldown=ignore_cooldown)
    if not allowed:
        raise SafetyViolation(reason)

    if not validate_index_name(index_name):
        raise SafetyViolation(f"Invalid index name: {index_name}")


def get_safety_report() -> str:
    """Generate a safety status report."""
    config = get_config()
    existing = get_existing_indexes_from_db()
    total_active = get_total_active_index_count()

    lines = []
    lines.append("=" * 60)
    lines.append("SAFETY STATUS REPORT")
    lines.append("=" * 60)
    lines.append(f"Remediation enabled: {config.remediation.enabled}")
    lines.append(f"Dry-run default: {config.remediation.dry_run_default}")
    lines.append(f"Max indexes per table: {config.remediation.max_indexes_per_table}")
    lines.append(f"Max indexes total: {config.remediation.max_indexes_total}")
    lines.append(f"Cooldown: {config.remediation.cooldown_minutes} minutes")
    lines.append(f"Rollback policy: {config.remediation.rollback_policy}")
    lines.append(f"\nActive indexes (state_store): {total_active}")
    lines.append(f"\nIndexes in database:")
    for tbl, indexes in sorted(existing.items()):
        lines.append(f"  {tbl}: {len(indexes)} indexes")
        for idx in indexes:
            lines.append(f"    - {idx}")
    lines.append("=" * 60)
    return "\n".join(lines)
