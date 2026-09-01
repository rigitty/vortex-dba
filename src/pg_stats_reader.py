"""PostgreSQL statistics reader for VortexDBA.

Reads query performance data from pg_stat_statements and
table/index usage statistics from pg_stat_user_tables and
pg_stat_user_indexes.
"""

from dataclasses import dataclass

from db_connection import execute_query


@dataclass
class QueryStat:
    """Statistics for a single query from pg_stat_statements."""
    queryid: int
    query: str
    calls: int
    total_exec_time: float  # ms
    mean_exec_time: float   # ms
    min_exec_time: float    # ms
    max_exec_time: float    # ms
    rows: int
    shared_blks_hit: int
    shared_blks_read: int


@dataclass
class TableStat:
    """Table-level statistics from pg_stat_user_tables."""
    relname: str
    seq_scan: int
    seq_tup_read: int
    idx_scan: int
    idx_tup_fetch: int
    n_tup_ins: int
    n_tup_upd: int
    n_tup_del: int
    n_live_tup: int
    n_dead_tup: int


@dataclass
class IndexStat:
    """Index-level statistics from pg_stat_user_indexes."""
    relname: str
    indexrelname: str
    idx_scan: int
    idx_tup_read: int
    idx_tup_fetch: int


def get_top_queries_by_time(limit: int = 10) -> list[QueryStat]:
    """Get the slowest queries by mean execution time."""
    query = """
        SELECT
            queryid,
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            min_exec_time,
            max_exec_time,
            rows,
            shared_blks_hit,
            shared_blks_read
        FROM pg_stat_statements
        WHERE query NOT LIKE '%%pg_stat_statements%%'
        ORDER BY mean_exec_time DESC
        LIMIT %s
    """
    results = execute_query(query, (limit,))
    return [
        QueryStat(
            queryid=r["queryid"],
            query=r["query"],
            calls=r["calls"],
            total_exec_time=round(r["total_exec_time"], 2),
            mean_exec_time=round(r["mean_exec_time"], 2),
            min_exec_time=round(r["min_exec_time"], 2),
            max_exec_time=round(r["max_exec_time"], 2),
            rows=r["rows"],
            shared_blks_hit=r["shared_blks_hit"],
            shared_blks_read=r["shared_blks_read"],
        )
        for r in results
    ]


def get_top_queries_by_calls(limit: int = 10) -> list[QueryStat]:
    """Get the most frequently called queries."""
    query = """
        SELECT
            queryid,
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            min_exec_time,
            max_exec_time,
            rows,
            shared_blks_hit,
            shared_blks_read
        FROM pg_stat_statements
        WHERE query NOT LIKE '%%pg_stat_statements%%'
        ORDER BY calls DESC
        LIMIT %s
    """
    results = execute_query(query, (limit,))
    return [
        QueryStat(
            queryid=r["queryid"],
            query=r["query"],
            calls=r["calls"],
            total_exec_time=round(r["total_exec_time"], 2),
            mean_exec_time=round(r["mean_exec_time"], 2),
            min_exec_time=round(r["min_exec_time"], 2),
            max_exec_time=round(r["max_exec_time"], 2),
            rows=r["rows"],
            shared_blks_hit=r["shared_blks_hit"],
            shared_blks_read=r["shared_blks_read"],
        )
        for r in results
    ]


def get_top_queries_by_total_time(limit: int = 10) -> list[QueryStat]:
    """Get queries with highest total execution time."""
    query = """
        SELECT
            queryid,
            query,
            calls,
            total_exec_time,
            mean_exec_time,
            min_exec_time,
            max_exec_time,
            rows,
            shared_blks_hit,
            shared_blks_read
        FROM pg_stat_statements
        WHERE query NOT LIKE '%%pg_stat_statements%%'
        ORDER BY total_exec_time DESC
        LIMIT %s
    """
    results = execute_query(query, (limit,))
    return [
        QueryStat(
            queryid=r["queryid"],
            query=r["query"],
            calls=r["calls"],
            total_exec_time=round(r["total_exec_time"], 2),
            mean_exec_time=round(r["mean_exec_time"], 2),
            min_exec_time=round(r["min_exec_time"], 2),
            max_exec_time=round(r["max_exec_time"], 2),
            rows=r["rows"],
            shared_blks_hit=r["shared_blks_hit"],
            shared_blks_read=r["shared_blks_read"],
        )
        for r in results
    ]


def get_table_stats() -> list[TableStat]:
    """Get table-level scan and modification statistics."""
    query = """
        SELECT
            relname,
            seq_scan,
            seq_tup_read,
            idx_scan,
            idx_tup_fetch,
            n_tup_ins,
            n_tup_upd,
            n_tup_del,
            n_live_tup,
            n_dead_tup
        FROM pg_stat_user_tables
        ORDER BY seq_scan DESC
    """
    results = execute_query(query)
    return [
        TableStat(
            relname=r["relname"],
            seq_scan=r["seq_scan"],
            seq_tup_read=r["seq_tup_read"],
            idx_scan=r["idx_scan"] or 0,
            idx_tup_fetch=r["idx_tup_fetch"] or 0,
            n_tup_ins=r["n_tup_ins"],
            n_tup_upd=r["n_tup_upd"],
            n_tup_del=r["n_tup_del"],
            n_live_tup=r["n_live_tup"],
            n_dead_tup=r["n_dead_tup"],
        )
        for r in results
    ]


def get_index_stats() -> list[IndexStat]:
    """Get index usage statistics."""
    query = """
        SELECT
            relname,
            indexrelname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC
    """
    results = execute_query(query)
    return [
        IndexStat(
            relname=r["relname"],
            indexrelname=r["indexrelname"],
            idx_scan=r["idx_scan"],
            idx_tup_read=r["idx_tup_read"],
            idx_tup_fetch=r["idx_tup_fetch"],
        )
        for r in results
    ]


def format_query_stats(stats: list[QueryStat], title: str) -> str:
    """Format query statistics into a readable table."""
    if not stats:
        return f"{title}: No data available."

    lines = []
    lines.append("=" * 80)
    lines.append(title)
    lines.append("=" * 80)
    lines.append(f"{'Query':<50} {'Calls':>8} {'Mean(ms)':>10} {'Total(ms)':>12} {'Rows':>8}")
    lines.append("-" * 80)

    for s in stats:
        query_short = s.query[:47] + "..." if len(s.query) > 50 else s.query
        lines.append(f"{query_short:<50} {s.calls:>8} {s.mean_exec_time:>10.2f} {s.total_exec_time:>12.2f} {s.rows:>8}")

    lines.append("=" * 80)
    return "\n".join(lines)


def format_table_stats(stats: list[TableStat]) -> str:
    """Format table statistics into a readable table."""
    if not stats:
        return "No table statistics available."

    lines = []
    lines.append("=" * 80)
    lines.append("TABLE STATISTICS")
    lines.append("=" * 80)
    lines.append(f"{'Table':<20} {'Seq Scans':>10} {'Idx Scans':>10} {'Live Tup':>10} {'Dead Tup':>10} {'Scan Ratio':>12}")
    lines.append("-" * 80)

    for s in stats:
        total_scans = s.seq_scan + s.idx_scan
        seq_ratio = f"{(s.seq_scan / total_scans * 100):.1f}%" if total_scans > 0 else "N/A"
        lines.append(
            f"{s.relname:<20} {s.seq_scan:>10} {s.idx_scan:>10} "
            f"{s.n_live_tup:>10} {s.n_dead_tup:>10} {seq_ratio:>12}"
        )

    lines.append("=" * 80)
    return "\n".join(lines)


def format_index_stats(stats: list[IndexStat]) -> str:
    """Format index statistics into a readable table."""
    if not stats:
        return "No index statistics available."

    lines = []
    lines.append("=" * 80)
    lines.append("INDEX STATISTICS")
    lines.append("=" * 80)
    lines.append(f"{'Table':<15} {'Index':<25} {'Scans':>10} {'Tup Read':>10} {'Tup Fetch':>10}")
    lines.append("-" * 80)

    for s in stats:
        lines.append(
            f"{s.relname:<15} {s.indexrelname:<25} "
            f"{s.idx_scan:>10} {s.idx_tup_read:>10} {s.idx_tup_fetch:>10}"
        )

    lines.append("=" * 80)
    return "\n".join(lines)


def get_full_report() -> str:
    """Generate a comprehensive statistics report."""
    lines = []

    # Query statistics
    top_by_time = get_top_queries_by_time(5)
    lines.append(format_query_stats(top_by_time, "TOP 5 QUERIES BY MEAN EXECUTION TIME"))
    lines.append("")

    top_by_calls = get_top_queries_by_calls(5)
    lines.append(format_query_stats(top_by_calls, "TOP 5 QUERIES BY CALL COUNT"))
    lines.append("")

    # Table statistics
    table_stats = get_table_stats()
    lines.append(format_table_stats(table_stats))
    lines.append("")

    # Index statistics
    index_stats = get_index_stats()
    lines.append(format_index_stats(index_stats))

    return "\n".join(lines)
