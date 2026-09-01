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
    """Find indexes with zero scans that are not primary keys or unique constraints."""
    query = """
        SELECT
            s.schemaname,
            s.relname AS table_name,
            s.indexrelname AS index_name,
            pg_relation_size(s.indexrelid) AS index_size_bytes,
            pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size_pretty,
            s.idx_scan,
            p.indisunique AS is_unique,
            p.indisprimary AS is_primary
        FROM pg_stat_user_indexes s
        JOIN pg_index p ON p.indexrelid = s.indexrelid
        WHERE s.idx_scan = 0
          AND s.schemaname = 'public'
        ORDER BY pg_relation_size(s.indexrelid) DESC
    """
    results = execute_query(query)

    unused = []
    for r in results:
        # Skip primary keys and unique indexes
        if r["is_primary"] or r["is_unique"]:
            continue

        # Get index columns
        columns = _get_index_columns(r["index_name"])

        drop_stmt = f"DROP INDEX CONCURRENTLY IF EXISTS {r['index_name']};"

        unused.append(UnusedIndex(
            table_name=r["table_name"],
            index_name=r["index_name"],
            index_size_bytes=r["index_size_bytes"],
            index_size_pretty=r["index_size_pretty"],
            is_unique=r["is_unique"],
            is_primary=r["is_primary"],
            columns=columns,
            drop_statement=drop_stmt,
        ))

    return unused


def _get_index_columns(index_name: str) -> list[str]:
    """Get the columns of an index."""
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


def get_index_usage_stats() -> list[dict]:
    """Get usage statistics for all user indexes."""
    query = """
        SELECT
            s.relname AS table_name,
            s.indexrelname AS index_name,
            s.idx_scan AS scans,
            s.idx_tup_read AS tuples_read,
            s.idx_tup_fetch AS tuples_fetched,
            pg_relation_size(s.indexrelid) AS index_size_bytes,
            pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size_pretty,
            p.indisunique AS is_unique,
            p.indisprimary AS is_primary
        FROM pg_stat_user_indexes s
        JOIN pg_index p ON p.indexrelid = s.indexrelid
        WHERE s.schemaname = 'public'
        ORDER BY s.idx_scan ASC, pg_relation_size(s.indexrelid) DESC
    """
    return execute_query(query)


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
