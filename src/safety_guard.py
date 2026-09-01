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
    """Query pg_indexes to get all existing indexes dynamically."""
    query = """
        SELECT indexname, tablename
        FROM pg_indexes
        WHERE schemaname = 'public'
    """
    results = execute_query(query)
    index_map: dict[str, list[str]] = {}
    for r in results:
        idx_name = r["indexname"]
        tbl_name = r["tablename"]
        if tbl_name not in index_map:
            index_map[tbl_name] = []
        index_map[tbl_name].append(idx_name)
    return index_map


def get_index_columns_from_db(index_name: str) -> list[str]:
    """Get the columns of an existing index."""
    query = """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        JOIN pg_class c ON c.oid = i.indexrelid
        WHERE c.relname = %s
        ORDER BY array_position(i.indkey, a.attnum)
    """
    results = execute_query(query, (index_name,))
    return [r["attname"] for r in results]


def can_apply_index(table_name: str, index_name: str) -> tuple[bool, str]:
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

    # Check max indexes per table
    table_count = get_index_count_for_table(table_name)
    if table_count >= config.remediation.max_indexes_per_table:
        return False, (
            f"Table {table_name} already has {table_count} indexes "
            f"(max: {config.remediation.max_indexes_per_table})"
        )

    # Check total index limit
    total_count = get_total_active_index_count()
    if total_count >= config.remediation.max_indexes_total:
        return False, (
            f"Total active indexes: {total_count} "
            f"(max: {config.remediation.max_indexes_total})"
        )

    # Check cooldown
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
    if len(index_name) > 63:  # PostgreSQL identifier limit
        return False
    # Check for valid characters
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_")
    if not all(c in allowed for c in index_name.lower()):
        return False
    return True


def check_safety(table_name: str, index_name: str) -> None:
    """Run all safety checks. Raises SafetyViolation if any fail."""
    allowed, reason = can_apply_index(table_name, index_name)
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
