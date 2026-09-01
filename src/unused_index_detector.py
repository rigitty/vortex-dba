"""Unused index detector for VortexDBA.

Identifies indexes that are never used (idx_scan = 0) and
recommends dropping them to reduce write overhead and storage.
Excludes primary keys and unique indexes from recommendations.
"""

from dataclasses import dataclass

from db_connection import execute_query


@dataclass
class UnusedIndex:
    """Represents an unused index."""
    table_name: str
    index_name: str
    index_size_bytes: int
    index_size_pretty: str
    is_unique: bool
    is_primary: bool
    columns: list[str]
    drop_statement: str


def get_unused_indexes() -> list[UnusedIndex]:
    """Find indexes with zero seeks/scans that are not primary keys or unique constraints."""
    query = """
        SELECT
            s.name AS schema_name,
            t.name AS table_name,
            i.name AS index_name,
            ISNULL(ps.used_page_count * 8192, 0) AS index_size_bytes,
            i.is_unique,
            i.is_primary_key AS is_primary
        FROM sys.indexes i
        JOIN sys.tables t ON t.object_id = i.object_id
        JOIN sys.schemas s ON s.schema_id = t.schema_id
        LEFT JOIN sys.dm_db_index_usage_stats ius ON ius.object_id = i.object_id AND ius.index_id = i.index_id AND ius.database_id = DB_ID()
        OUTER APPLY (
            SELECT SUM(used_page_count) AS used_page_count
            FROM sys.dm_db_partition_stats ps
            WHERE ps.object_id = i.object_id AND ps.index_id = i.index_id
        ) ps
        WHERE i.type_desc = 'NONCLUSTERED'
          AND i.is_primary_key = 0
          AND i.is_unique = 0
          AND i.is_unique_constraint = 0
          AND t.is_ms_shipped = 0
          AND ISNULL(ius.user_seeks + ius.user_scans + ius.user_lookups, 0) = 0
        ORDER BY index_size_bytes DESC
    """
    results = execute_query(query)

    unused = []
    for r in (results or []):
        if r["is_primary"] or r["is_unique"]:
            continue

        columns = _get_index_columns(r["index_name"])
        drop_stmt = f"DROP INDEX IF EXISTS {r['index_name']} ON {r['table_name']};"
        size_bytes = int(r["index_size_bytes"] or 0)

        unused.append(UnusedIndex(
            table_name=r["table_name"],
            index_name=r["index_name"],
            index_size_bytes=size_bytes,
            index_size_pretty=_format_size(size_bytes),
            is_unique=bool(r["is_unique"]),
            is_primary=bool(r["is_primary"]),
            columns=columns,
            drop_statement=drop_stmt,
        ))

    return unused


def _get_index_columns(index_name: str) -> list[str]:
    """Get the columns of a SQL Server index."""
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


def get_index_usage_stats() -> list[dict]:
    """Get usage statistics for all user indexes in SQL Server."""
    query = """
        SELECT
            t.name AS table_name,
            i.name AS index_name,
            ISNULL(ius.user_seeks + ius.user_scans + ius.user_lookups, 0) AS scans,
            ISNULL(ius.user_seeks, 0) AS tuples_read,
            ISNULL(ius.user_scans + ius.user_lookups, 0) AS tuples_fetched,
            ISNULL(ps.used_page_count * 8192, 0) AS index_size_bytes,
            i.is_unique,
            i.is_primary_key AS is_primary
        FROM sys.indexes i
        JOIN sys.tables t ON t.object_id = i.object_id
        LEFT JOIN sys.dm_db_index_usage_stats ius ON ius.object_id = i.object_id AND ius.index_id = i.index_id AND ius.database_id = DB_ID()
        OUTER APPLY (
            SELECT SUM(used_page_count) AS used_page_count
            FROM sys.dm_db_partition_stats ps
            WHERE ps.object_id = i.object_id AND ps.index_id = i.index_id
        ) ps
        WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL
        ORDER BY scans ASC, index_size_bytes DESC
    """
    results = execute_query(query)
    out = []
    for r in (results or []):
        size_bytes = int(r["index_size_bytes"] or 0)
        out.append({
            "table_name": r["table_name"],
            "index_name": r["index_name"],
            "scans": r["scans"],
            "tuples_read": r["tuples_read"],
            "tuples_fetched": r["tuples_fetched"],
            "index_size_bytes": size_bytes,
            "index_size_pretty": _format_size(size_bytes),
            "is_unique": bool(r["is_unique"]),
            "is_primary": bool(r["is_primary"]),
        })
    return out


def format_unused_indexes(unused: list[UnusedIndex]) -> str:
    """Format unused index report."""
    if not unused:
        return "No unused indexes found."

    lines = []
    lines.append("=" * 80)
    lines.append("UNUSED INDEXES")
    lines.append("=" * 80)
    lines.append(f"Found {len(unused)} unused indexes (excluding PKs and unique constraints)")
    lines.append("")

    total_size = 0
    for i, idx in enumerate(unused, 1):
        total_size += idx.index_size_bytes
        lines.append(f"[{i}] {idx.index_name}")
        lines.append(f"    Table: {idx.table_name}")
        lines.append(f"    Columns: {', '.join(idx.columns)}")
        lines.append(f"    Size: {idx.index_size_pretty}")
        lines.append(f"    Drop: {idx.drop_statement}")
        lines.append("")

    lines.append("-" * 80)
    lines.append(f"Total reclaimable space: {_format_size(total_size)}")
    lines.append("=" * 80)

    return "\n".join(lines)


def format_index_usage_stats(stats: list[dict]) -> str:
    """Format index usage statistics."""
    if not stats:
        return "No index statistics available."

    lines = []
    lines.append("=" * 100)
    lines.append("INDEX USAGE STATISTICS")
    lines.append("=" * 100)
    lines.append(f"{'Table':<20} {'Index':<30} {'Scans':>8} {'Size':>10} {'Unique':>8} {'Primary':>8}")
    lines.append("-" * 100)

    for s in stats:
        is_unique = "Yes" if s["is_unique"] else "No"
        is_primary = "Yes" if s["is_primary"] else "No"
        lines.append(
            f"{s['table_name']:<20} {s['index_name']:<30} "
            f"{s['scans']:>8} {s['index_size_pretty']:>10} "
            f"{is_unique:>8} {is_primary:>8}"
        )

    lines.append("=" * 100)
    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    """Format bytes to human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_drop_all_sql(unused: list[UnusedIndex]) -> str:
    """Generate SQL script to drop all unused indexes."""
    if not unused:
        return "-- No unused indexes to drop."

    lines = ["-- VortexDBA: Drop unused indexes", "-- Review carefully before applying!\n"]
    for idx in unused:
        lines.append(f"-- Size: {idx.index_size_pretty}, Table: {idx.table_name}")
        lines.append(idx.drop_statement)
        lines.append("")

    return "\n".join(lines)
