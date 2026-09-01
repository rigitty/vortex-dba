"""Dynamic query discovery from pg_stat_statements.

Discovers slow queries from PostgreSQL's pg_stat_statements,
normalizes them, and runs EXPLAIN ANALYZE to generate execution
plans for analysis.
"""

import re
from dataclasses import dataclass

from config import get_config
from db_connection import get_connection


@dataclass
class DiscoveredQuery:
    """A query discovered from sys.dm_exec_query_stats."""
    queryid: int
    query: str
    normalized_query: str
    calls: int
    mean_exec_time: float
    total_exec_time: float
    rows: int
    plan: str = ""
    plan_error: str = ""


def discover_slow_queries(limit: int | None = None) -> list[DiscoveredQuery]:
    """Discover slow queries from SQL Server sys.dm_exec_query_stats."""
    config = get_config()
    if limit is None:
        limit = config.detection.top_queries_limit

    query = f"""
        SELECT TOP ({int(limit)})
            CHECKSUM(qs.sql_handle) AS queryid,
            CAST(SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
                ((CASE qs.statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE qs.statement_end_offset
                 END - qs.statement_start_offset)/2) + 1) AS NVARCHAR(MAX)) AS query,
            qs.execution_count AS calls,
            ((qs.total_elapsed_time / qs.execution_count) / 1000.0) AS mean_exec_time,
            (qs.total_elapsed_time / 1000.0) AS total_exec_time,
            qs.total_rows AS rows
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE st.text NOT LIKE '%sys.dm_%'
          AND st.text NOT LIKE '%SHOWPLAN%'
          AND st.text NOT LIKE '%CREATE INDEX%'
          AND st.text NOT LIKE '%DROP INDEX%'
          AND ((qs.total_elapsed_time / qs.execution_count) / 1000.0) >= {float(config.detection.min_mean_exec_time_ms)}
          AND (qs.total_elapsed_time / 1000.0) >= {float(config.detection.min_total_exec_time_ms)}
          AND qs.execution_count >= {int(config.detection.min_calls)}
        ORDER BY total_exec_time DESC
    """

    conn = get_connection(autocommit=True)
    try:
        with conn.cursor(as_dict=True) as cur:
            cur.execute(query)
            rows = cur.fetchall()
    finally:
        conn.close()

    discovered = []
    for row in (rows or []):
        raw_query = (row["query"] or "").strip()
        normalized = normalize_query(raw_query)
        discovered.append(DiscoveredQuery(
            queryid=row["queryid"] or 0,
            query=raw_query,
            normalized_query=normalized,
            calls=row["calls"] or 0,
            mean_exec_time=round(float(row["mean_exec_time"] or 0), 2),
            total_exec_time=round(float(row["total_exec_time"] or 0), 2),
            rows=row["rows"] or 0,
        ))

    return discovered


def normalize_query(query: str) -> str:
    """Normalize a query for deduplication.

    Replaces literal values with placeholders while preserving
    structure for analysis.
    """
    # Replace string literals
    normalized = re.sub(r"'[^']*'", "'?'", query)

    # Replace numeric literals (but not in column names or keywords)
    normalized = re.sub(r"\b\d+\.?\d*\b", "?", normalized)

    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def get_explain_plan(query: str, params: tuple | None = None) -> tuple[str, str]:
    """Run SHOWPLAN_TEXT on a query in SQL Server and return (plan, error)."""
    clean_query = _replace_parameters(query)
    conn = get_connection(autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SET SHOWPLAN_TEXT ON")
            cur.execute(clean_query)
            plan_lines = []
            while True:
                try:
                    rows = cur.fetchall()
                    for row in (rows or []):
                        text = row[0] if isinstance(row, (tuple, list)) else (row.get("StmtText") or str(row))
                        plan_lines.append(str(text))
                    if not cur.nextset():
                        break
                except Exception:
                    break
            cur.execute("SET SHOWPLAN_TEXT OFF")
            return "\n".join(plan_lines), ""
    except Exception as e:
        try:
            with conn.cursor() as cur:
                cur.execute("SET SHOWPLAN_TEXT OFF")
        except Exception:
            pass
        return "", str(e)
    finally:
        conn.close()


def _replace_parameters(query: str) -> str:
    """Replace $1, $2, etc. with representative default values.

    This is a best-effort approach to make parameterized queries
    executable for EXPLAIN ANALYZE.
    """
    result = query
    params = re.findall(r'\$(\d+)', query)
    if not params:
        return result

    # Context values mapped to typical columns
    column_defaults = {
        'id': '1',
        'customer_id': '1',
        'created_at': "'2024-01-01'::timestamp",
        'order_date': "'2024-01-01'::timestamp",
        'status': "'completed'",
        'city': "'New York'",
        'country': "'United States'",
        'total_amount': '100',
        'email': "'test@example.com'",
        'product_category': "'Electronics'",
    }

    # Match each parameter with surrounding column context if available
    for param_num in sorted(set(params), key=int, reverse=True):
        param_pattern = rf'\${param_num}\b'
        # Look for pattern: column = $1 or column > $1
        col_match = re.search(rf'(\w+)\s*[=<>!~]+\s*\${param_num}\b', query, re.IGNORECASE)
        if col_match:
            col = col_match.group(1).lower()
            val = column_defaults.get(col)
            if not val:
                if 'id' in col:
                    val = '1'
                elif 'date' in col or 'time' in col:
                    val = "'2024-01-01'::timestamp"
                elif 'amount' in col or 'price' in col or 'total' in col:
                    val = '100'
                else:
                    val = "'value'"
            result = re.sub(param_pattern, val, result)
        else:
            # Fallback based on param context
            result = re.sub(param_pattern, "'value'", result)

    return result


def discover_and_analyze(limit: int | None = None) -> list[DiscoveredQuery]:
    """Discover slow queries and get their execution plans."""
    queries = discover_slow_queries(limit)

    for dq in queries:
        plan, error = get_explain_plan(dq.query)
        dq.plan = plan
        dq.plan_error = error

    return queries


def format_discovered_queries(queries: list[DiscoveredQuery]) -> str:
    """Format discovered queries into a readable report."""
    if not queries:
        return "No slow queries discovered."

    lines = []
    lines.append("=" * 80)
    lines.append("DISCOVERED SLOW QUERIES")
    lines.append("=" * 80)
    lines.append(f"{'#':<4} {'QueryID':<12} {'Calls':<8} {'Mean(ms)':<12} {'Total(ms)':<12} {'Query':<40}")
    lines.append("-" * 80)

    for i, dq in enumerate(queries, 1):
        query_short = dq.normalized_query[:37] + "..." if len(dq.normalized_query) > 40 else dq.normalized_query
        lines.append(
            f"{i:<4} {dq.queryid:<12} {dq.calls:<8} "
            f"{dq.mean_exec_time:<12.2f} {dq.total_exec_time:<12.2f} {query_short:<40}"
        )

    lines.append("=" * 80)
    return "\n".join(lines)
