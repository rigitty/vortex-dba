"""Dynamic query discovery from pg_stat_statements.

Discovers slow queries from PostgreSQL's pg_stat_statements,
normalizes them, and runs EXPLAIN ANALYZE to generate execution
plans for analysis.
"""

import re
from dataclasses import dataclass

from psycopg2.extras import RealDictCursor

from config import get_config
from db_connection import get_connection


@dataclass
class DiscoveredQuery:
    """A query discovered from pg_stat_statements."""
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
    """Discover slow queries from pg_stat_statements.

    Queries are filtered by:
    - min_mean_exec_time_ms
    - min_total_exec_time_ms
    - min_calls
    """
    config = get_config()
    if limit is None:
        limit = config.detection.top_queries_limit

    query = """
        SELECT
            queryid,
            query,
            calls,
            mean_exec_time,
            total_exec_time,
            rows
        FROM pg_stat_statements
        WHERE query NOT LIKE '%%pg_stat_statements%%'
          AND query NOT LIKE '%%EXPLAIN%%'
          AND query NOT LIKE '%%DISCARD%%'
          AND query NOT LIKE '%%SET%%'
          AND query NOT LIKE '%%BEGIN%%'
          AND query NOT LIKE '%%COMMIT%%'
          AND query NOT LIKE '%%ROLLBACK%%'
          AND mean_exec_time >= %s
          AND total_exec_time >= %s
          AND calls >= %s
        ORDER BY total_exec_time DESC
        LIMIT %s
    """

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (
                config.detection.min_mean_exec_time_ms,
                config.detection.min_total_exec_time_ms,
                config.detection.min_calls,
                limit,
            ))
            rows = cur.fetchall()
    finally:
        conn.close()

    discovered = []
    for row in rows:
        normalized = normalize_query(row["query"])
        discovered.append(DiscoveredQuery(
            queryid=row["queryid"],
            query=row["query"],
            normalized_query=normalized,
            calls=row["calls"],
            mean_exec_time=round(row["mean_exec_time"], 2),
            total_exec_time=round(row["total_exec_time"], 2),
            rows=row["rows"],
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
    """Run EXPLAIN ANALYZE on a query and return (plan, error).

    Returns:
        Tuple of (plan_text, error_message). If successful, error is empty.
    """
    # Replace parameterized placeholders with default values
    explain_query = _replace_parameters(query)
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {explain_query}"

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(explain_query)
                rows = cur.fetchall()
                plan = "\n".join(row["QUERY PLAN"] for row in rows)
                conn.commit()
                return plan, ""
            except Exception as e:
                conn.rollback()
                return "", str(e)
    finally:
        conn.close()


def _replace_parameters(query: str) -> str:
    """Replace $1, $2, etc. with representative default values.

    This is a best-effort approach to make parameterized queries
    executable for EXPLAIN ANALYZE. We analyze the query context
    to provide reasonable default values.
    """
    import re

    result = query
    # Find all parameter references
    params = re.findall(r'\$(\d+)', query)
    if not params:
        return result

    # Analyze query context to determine appropriate values
    query_lower = query.lower()

    # Common value mappings based on column context
    context_values = {
        'created_at': "'2024-01-01'::timestamp",
        'order_date': "'2024-01-01'::timestamp",
        'status': "'completed'",
        'city': "'New York'",
        'country': "'United States'",
        'total_amount': '100',
        'email': "'test@example.com'",
    }

    # Try to find context from WHERE clause
    where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
    if where_match:
        where_clause = where_match.group(1).lower()

        # Determine value based on column in WHERE clause
        for col, value in context_values.items():
            if col in where_clause:
                # Replace first parameter with appropriate value
                result = re.sub(r'\$1', value, result, count=1)
                # Replace remaining parameters with generic values
                for i in range(2, max(int(p) for p in params) + 1):
                    result = result.replace(f'${i}', f"'2024-01-01'::timestamp" if 'date' in col else f"'value{i}'")
                return result

    # Default: replace with generic values that will return results
    for param_num in sorted(set(params), key=int, reverse=True):
        result = result.replace(f'${param_num}', "'2024-01-01'::timestamp")

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
