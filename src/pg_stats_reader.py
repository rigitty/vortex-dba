"""SQL Server statistics reader for VortexDBA.

Reads query performance data from sys.dm_exec_query_stats and
table/index usage statistics from sys.dm_db_index_usage_stats and
sys.tables.
"""

from dataclasses import dataclass

from db_connection import execute_query


@dataclass
class QueryStat:
    """Statistics for a single query from sys.dm_exec_query_stats."""
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
    """Table-level statistics from SQL Server sys views."""
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
    """Index-level statistics from sys.dm_db_index_usage_stats."""
    relname: str
    indexrelname: str
    idx_scan: int
    idx_tup_read: int
def get_top_queries_by_time(limit: int = 15) -> list[QueryStat]:
    """Get the slowest queries by mean execution time."""
    query = f"""
        SELECT TOP ({int(limit)})
            CHECKSUM(qs.sql_handle) AS queryid,
            CAST(SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
                ((CASE qs.statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE qs.statement_end_offset
                 END - qs.statement_start_offset)/2) + 1) AS NVARCHAR(MAX)) AS query,
            qs.execution_count AS calls,
            (qs.total_elapsed_time / 1000.0) AS total_exec_time,
            ((qs.total_elapsed_time / qs.execution_count) / 1000.0) AS mean_exec_time,
            (qs.min_elapsed_time / 1000.0) AS min_exec_time,
            (qs.max_elapsed_time / 1000.0) AS max_exec_time,
            qs.total_rows AS rows,
            qs.total_logical_reads AS shared_blks_hit,
            qs.total_physical_reads AS shared_blks_read
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE (st.text LIKE '%customers%' OR st.text LIKE '%orders%' OR (st.dbid = DB_ID() AND st.text NOT LIKE '%sys.%'))
          AND st.text NOT LIKE '%sys.dm_%'
          AND st.text NOT LIKE '%dm_exec_query_stats%'
          AND st.text NOT LIKE '%CHECKSUM%'
          AND st.text NOT LIKE '%sys.%'
          AND st.text NOT LIKE '%SHOWPLAN%'
          AND st.text NOT LIKE '%CREATE INDEX%'
          AND st.text NOT LIKE '%DROP INDEX%'
          AND st.text NOT LIKE '%DBCC%'
        ORDER BY qs.last_execution_time DESC, mean_exec_time DESC
    """
    results = execute_query(query)

    return [
        QueryStat(
            queryid=r["queryid"] or 0,
            query=(r["query"] or "").strip(),
            calls=r["calls"] or 0,
            total_exec_time=round(float(r["total_exec_time"] or 0), 2),
            mean_exec_time=round(float(r["mean_exec_time"] or 0), 2),
            min_exec_time=round(float(r["min_exec_time"] or 0), 2),
            max_exec_time=round(float(r["max_exec_time"] or 0), 2),
            rows=r["rows"] or 0,
            shared_blks_hit=r["shared_blks_hit"] or 0,
            shared_blks_read=r["shared_blks_read"] or 0,
        )
        for r in (results or [])
    ]


def get_top_queries_by_calls(limit: int = 15) -> list[QueryStat]:
    """Get the most frequently called queries."""
    query = f"""
        SELECT TOP ({int(limit)})
            CHECKSUM(qs.sql_handle) AS queryid,
            CAST(SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
                ((CASE qs.statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE qs.statement_end_offset
                 END - qs.statement_start_offset)/2) + 1) AS NVARCHAR(MAX)) AS query,
            qs.execution_count AS calls,
            (qs.total_elapsed_time / 1000.0) AS total_exec_time,
            ((qs.total_elapsed_time / qs.execution_count) / 1000.0) AS mean_exec_time,
            (qs.min_elapsed_time / 1000.0) AS min_exec_time,
            (qs.max_elapsed_time / 1000.0) AS max_exec_time,
            qs.total_rows AS rows,
            qs.total_logical_reads AS shared_blks_hit,
            qs.total_physical_reads AS shared_blks_read
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE (st.text LIKE '%customers%' OR st.text LIKE '%orders%' OR (st.dbid = DB_ID() AND st.text NOT LIKE '%sys.%'))
          AND st.text NOT LIKE '%sys.dm_%'
          AND st.text NOT LIKE '%dm_exec_query_stats%'
          AND st.text NOT LIKE '%CHECKSUM%'
          AND st.text NOT LIKE '%sys.%'
          AND st.text NOT LIKE '%SHOWPLAN%'
          AND st.text NOT LIKE '%CREATE INDEX%'
          AND st.text NOT LIKE '%DROP INDEX%'
          AND st.text NOT LIKE '%DBCC%'
        ORDER BY qs.execution_count DESC, mean_exec_time DESC
    """
    results = execute_query(query)
    return [

        QueryStat(
            queryid=r["queryid"] or 0,
            query=(r["query"] or "").strip(),
            calls=r["calls"] or 0,
            total_exec_time=round(float(r["total_exec_time"] or 0), 2),
            mean_exec_time=round(float(r["mean_exec_time"] or 0), 2),
            min_exec_time=round(float(r["min_exec_time"] or 0), 2),
            max_exec_time=round(float(r["max_exec_time"] or 0), 2),
            rows=r["rows"] or 0,
            shared_blks_hit=r["shared_blks_hit"] or 0,
            shared_blks_read=r["shared_blks_read"] or 0,
        )
        for r in (results or [])
    ]


def get_top_queries_by_total_time(limit: int = 10) -> list[QueryStat]:
    """Get queries with highest total execution time."""
    query = f"""
        SELECT TOP ({int(limit)})
            CHECKSUM(qs.sql_handle) AS queryid,
            CAST(SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
                ((CASE qs.statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE qs.statement_end_offset
                 END - qs.statement_start_offset)/2) + 1) AS NVARCHAR(MAX)) AS query,
            qs.execution_count AS calls,
            (qs.total_elapsed_time / 1000.0) AS total_exec_time,
            ((qs.total_elapsed_time / qs.execution_count) / 1000.0) AS mean_exec_time,
            (qs.min_elapsed_time / 1000.0) AS min_exec_time,
            (qs.max_elapsed_time / 1000.0) AS max_exec_time,
            qs.total_rows AS rows,
            qs.total_logical_reads AS shared_blks_hit,
            qs.total_physical_reads AS shared_blks_read
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE st.text NOT LIKE '%sys.dm_%'
          AND st.text NOT LIKE '%SHOWPLAN%'
          AND st.text NOT LIKE '%CREATE INDEX%'
          AND st.text NOT LIKE '%DROP INDEX%'
        ORDER BY total_exec_time DESC
    """
    results = execute_query(query)
    return [
        QueryStat(
            queryid=r["queryid"] or 0,
            query=(r["query"] or "").strip(),
            calls=r["calls"] or 0,
            total_exec_time=round(float(r["total_exec_time"] or 0), 2),
            mean_exec_time=round(float(r["mean_exec_time"] or 0), 2),
            min_exec_time=round(float(r["min_exec_time"] or 0), 2),
            max_exec_time=round(float(r["max_exec_time"] or 0), 2),
            rows=r["rows"] or 0,
            shared_blks_hit=r["shared_blks_hit"] or 0,
            shared_blks_read=r["shared_blks_read"] or 0,
        )
        for r in (results or [])
    ]


def get_table_stats() -> list[TableStat]:
    """Get table-level scan and modification statistics."""
    query = """
        SELECT
            t.name AS relname,
            ISNULL(SUM(CASE WHEN i.type_desc = 'HEAP' THEN ius.user_scans ELSE 0 END), 0) AS seq_scan,
            ISNULL(SUM(p.rows), 0) AS seq_tup_read,
            ISNULL(SUM(CASE WHEN i.type_desc != 'HEAP' THEN (ius.user_seeks + ius.user_scans + ius.user_lookups) ELSE 0 END), 0) AS idx_scan,
            ISNULL(SUM(CASE WHEN i.type_desc != 'HEAP' THEN ius.user_seeks ELSE 0 END), 0) AS idx_tup_fetch,
            0 AS n_tup_ins,
            ISNULL(SUM(ius.user_updates), 0) AS n_tup_upd,
            0 AS n_tup_del,
            ISNULL(SUM(p.rows), 0) AS n_live_tup,
            0 AS n_dead_tup
        FROM sys.tables t
        LEFT JOIN sys.indexes i ON t.object_id = i.object_id
        LEFT JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0, 1)
        LEFT JOIN sys.dm_db_index_usage_stats ius ON t.object_id = ius.object_id AND i.index_id = ius.index_id AND ius.database_id = DB_ID()
        WHERE t.is_ms_shipped = 0
        GROUP BY t.name
        ORDER BY n_live_tup DESC
    """
    results = execute_query(query)
    return [
        TableStat(
            relname=r["relname"],
            seq_scan=int(r["seq_scan"] or 0),
            seq_tup_read=int(r["seq_tup_read"] or 0),
            idx_scan=int(r["idx_scan"] or 0),
            idx_tup_fetch=int(r["idx_tup_fetch"] or 0),
            n_tup_ins=int(r["n_tup_ins"] or 0),
            n_tup_upd=int(r["n_tup_upd"] or 0),
            n_tup_del=int(r["n_tup_del"] or 0),
            n_live_tup=int(r["n_live_tup"] or 0),
            n_dead_tup=int(r["n_dead_tup"] or 0),
        )
        for r in (results or [])
    ]


def get_index_stats() -> list[IndexStat]:
    """Get index usage statistics."""
    query = """
        SELECT
            t.name AS relname,
            i.name AS indexrelname,
            ISNULL(ius.user_seeks + ius.user_scans + ius.user_lookups, 0) AS idx_scan,
            ISNULL(ius.user_seeks, 0) AS idx_tup_read,
            ISNULL(ius.user_scans + ius.user_lookups, 0) AS idx_tup_fetch
        FROM sys.indexes i
        JOIN sys.tables t ON t.object_id = i.object_id
        LEFT JOIN sys.dm_db_index_usage_stats ius ON i.object_id = ius.object_id AND i.index_id = ius.index_id AND ius.database_id = DB_ID()
        WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL
        ORDER BY idx_scan DESC
    """
    results = execute_query(query)
    return [
        IndexStat(
            relname=r["relname"],
            indexrelname=r["indexrelname"],
            idx_scan=int(r["idx_scan"] or 0),
            idx_tup_read=int(r["idx_tup_read"] or 0),
            idx_tup_fetch=int(r["idx_tup_fetch"] or 0),
        )
        for r in (results or [])
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


def get_live_workload_matrix(limit: int = 15) -> list[dict]:
    """Dynamically extract real slow queries from SQL Server DMVs and format as performance matrix items."""
    from index_advisor import recommend_index_for_query

    raw_stats = get_top_queries_by_time(limit=limit)
    if not raw_stats:
        return []

    DEFAULT_SCHEMA_INDEXES = {"idx_orders_customer_id", "idx_customers_email"}
    q_idx = """
        SELECT 
            t.name AS table_name,
            i.name AS index_name,
            STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
        FROM sys.indexes i
        JOIN sys.tables t ON t.object_id = i.object_id
        JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
        JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
        WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL 
          AND i.is_primary_key = 0 AND i.is_unique_constraint = 0 AND ic.is_included_column = 0
        GROUP BY t.name, i.name
    """
    all_active_rows = execute_query(q_idx) or []
    active_custom_rows = [r for r in all_active_rows if r["index_name"] not in DEFAULT_SCHEMA_INDEXES]

    matrix_items = []
    for idx, stat in enumerate(raw_stats, 1):
        sql_text = stat.query
        if not sql_text or len(sql_text) < 10:
            continue

        rec = recommend_index_for_query(sql_text)
        target_table = rec.table if rec else ("orders" if "orders" in sql_text.lower() else ("customers" if "customers" in sql_text.lower() else "Table"))
        target_cols = set(rec.columns) if rec else set()
        recommended_sql = rec.create_statement if rec else None
        reason = rec.reason if rec else f"Canlı DMV Yavaş Sorgu: Ort. {stat.mean_exec_time:.2f} ms ({stat.calls} çağrı)"

        matching_indexes = []
        matching_sqls = []
        for row in active_custom_rows:
            tbl = row["table_name"]
            idx_name = row["index_name"]
            idx_cols = set([c.strip() for c in row["columns"].split(",")] if row["columns"] else [])
            if tbl == target_table and (target_cols.issubset(idx_cols) or (target_cols and target_cols.intersection(idx_cols))):
                matching_indexes.append(idx_name)
                matching_sqls.append(f"CREATE NONCLUSTERED INDEX [{idx_name}] ON [{tbl}] ({row['columns']});")

        has_index = len(matching_indexes) > 0
        status_label = "⚡ İndeksli" if has_index else ("🐢 Kritik Yavaş" if stat.mean_exec_time > 500 else "⏳ İndeks Bekliyor")
        status_class = "badge-success" if has_index else ("badge-danger" if stat.mean_exec_time > 500 else "badge-warning")

        matrix_items.append({
            "name": f"live_query_{stat.queryid}_{idx}",
            "title": f"Canlı DMV Sorgusu #{idx} ({target_table})",
            "table": target_table,
            "columns": ", ".join(rec.columns) if rec else "-",
            "active_indexes": matching_indexes,
            "applied_index_sqls": matching_sqls,
            "has_index": has_index,
            "description": f"Canlı SQL Server DMV ({stat.calls} çağrı, {stat.total_exec_time:.1f}ms toplam süre)",
            "recommended_sql": recommended_sql or "",
            "reason": reason,
            "query_sql": sql_text,
            "baseline_ms": None if has_index else stat.mean_exec_time,
            "current_ms": stat.mean_exec_time if has_index else None,
            "speedup_pct": None,
            "multiplier": None,
            "status_label": status_label,
            "status_class": status_class,
        })

    return matrix_items

