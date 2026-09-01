"""Slow query simulation module for VortexDBA.

This module runs intentionally slow queries to generate performance data
for analysis. Each query demonstrates a common anti-pattern that causes
poor PostgreSQL performance.
"""

import time
from dataclasses import dataclass

from psycopg2.extras import RealDictCursor

from db_connection import get_connection


@dataclass
class QueryResult:
    """Container for query execution results."""
    name: str
    description: str
    query: str
    duration_ms: float
    row_count: int
    plan: str


SLOW_QUERIES = [
    {
        "name": "full_scan_no_index",
        "description": "Full table scan on customers.city (no index on city column)",
        "query": """
            SELECT id, first_name, last_name, email, city, country
            FROM customers
            WHERE city = %s
        """,
        "params": ("New York",),
    },
    {
        "name": "full_scan_status_filter",
        "description": "Full scan on orders.status (no index on status column)",
        "query": """
            SELECT id, customer_id, order_date, total_amount, status
            FROM orders
            WHERE status = 'completed'
            AND total_amount > 1000
        """,
        "params": None,
    },
    {
        "name": "heavy_join",
        "description": "Heavy JOIN between customers and orders without covering index",
        "query": """
            SELECT c.id, c.first_name, c.last_name, c.city,
                   COUNT(o.id) AS order_count,
                   SUM(o.total_amount) AS total_spent
            FROM customers c
            JOIN orders o ON o.customer_id = c.id
            WHERE c.country = %s
            GROUP BY c.id, c.first_name, c.last_name, c.city
            ORDER BY total_spent DESC
            LIMIT 100
        """,
        "params": ("United States",),
    },
    {
        "name": "like_search",
        "description": "LIKE pattern matching on non-indexed email column",
        "query": """
            SELECT id, first_name, last_name, email
            FROM customers
            WHERE email LIKE %s
        """,
        "params": ("%gmail.com",),
    },
    {
        "name": "subquery_aggregation",
        "description": "Subquery with aggregation causing repeated scans",
        "query": """
            SELECT c.id, c.first_name, c.last_name, c.city,
                   (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id) AS order_count,
                   (SELECT SUM(o2.total_amount) FROM orders o2 WHERE o2.customer_id = c.id) AS total_spent
            FROM customers c
            WHERE c.status = 'active'
            ORDER BY total_spent DESC NULLS LAST
            LIMIT 50
        """,
        "params": None,
    },
    {
        "name": "group_by_having",
        "description": "GROUP BY with HAVING on large dataset without supporting index",
        "query": """
            SELECT c.city, c.country,
                   COUNT(DISTINCT c.id) AS customer_count,
                   COUNT(o.id) AS order_count,
                   AVG(o.total_amount) AS avg_order_amount
            FROM customers c
            JOIN orders o ON o.customer_id = c.id
            WHERE c.created_at > %s
            GROUP BY c.city, c.country
            HAVING COUNT(o.id) > 100
            ORDER BY order_count DESC
        """,
        "params": ("2025-01-01",),
    },
    {
        "name": "range_scan_large",
        "description": "Large range scan on order_date without index",
        "query": """
            SELECT customer_id, SUM(total_amount) AS daily_total, COUNT(*) AS order_count
            FROM orders
            WHERE order_date BETWEEN %s AND %s
            GROUP BY customer_id
            ORDER BY daily_total DESC
            LIMIT 100
        """,
        "params": ("2025-01-01", "2025-12-31"),
    },
    {
        "name": "multi_condition_no_index",
        "description": "Multiple WHERE conditions without composite index",
        "query": """
            SELECT o.id, o.total_amount, o.status, o.product_category,
                   c.first_name, c.last_name, c.city
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            WHERE o.status = 'completed'
              AND o.product_category = 'Electronics'
              AND o.total_amount > 500
              AND c.city = %s
        """,
        "params": ("Lake Michael",),
    },
]


def get_execution_plan(cursor, query: str, params: tuple | None = None) -> str:
    """Retrieve the EXPLAIN ANALYZE output for a query."""
    explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {query}"
    cursor.execute(explain_query, params)
    rows = cursor.fetchall()
    return "\n".join(row["QUERY PLAN"] for row in rows)


def run_query(query_def: dict) -> QueryResult:
    """Execute a single slow query and capture its execution plan."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Run EXPLAIN ANALYZE
            plan = get_execution_plan(cur, query_def["query"], query_def.get("params"))

            # Run the actual query and measure time
            start = time.perf_counter()
            cur.execute(query_def["query"], query_def.get("params"))
            rows = cur.fetchall()
            duration_ms = (time.perf_counter() - start) * 1000

            return QueryResult(
                name=query_def["name"],
                description=query_def["description"],
                query=query_def["query"].strip(),
                duration_ms=round(duration_ms, 2),
                row_count=len(rows),
                plan=plan,
            )
    finally:
        conn.close()


def run_all_queries() -> list[QueryResult]:
    """Run all slow queries and return results."""
    results = []
    for qd in SLOW_QUERIES:
        print(f"\n{'=' * 60}")
        print(f"Running: {qd['name']}")
        print(f"Description: {qd['description']}")
        result = run_query(qd)
        print(f"Duration: {result.duration_ms:.2f} ms | Rows: {result.row_count}")
        results.append(result)
    return results


def print_summary(results: list[QueryResult]) -> None:
    """Print a summary table of all query results."""
    print("\n" + "=" * 80)
    print("SLOW QUERY SIMULATION SUMMARY")
    print("=" * 80)
    print(f"{'Query Name':<35} {'Duration (ms)':>15} {'Rows':>10}")
    print("-" * 80)
    for r in sorted(results, key=lambda x: x.duration_ms, reverse=True):
        print(f"{r.name:<35} {r.duration_ms:>15.2f} {r.row_count:>10}")
    print("=" * 80)


def main():
    """Main entry point for slow query simulation."""
    print("=" * 60)
    print("VortexDBA - Slow Query Simulation")
    print("=" * 60)

    results = run_all_queries()
    print_summary(results)

    # Print detailed execution plans
    print("\n" + "=" * 80)
    print("DETAILED EXECUTION PLANS")
    print("=" * 80)
    for r in results:
        print(f"\n--- {r.name} ---")
        print(f"Description: {r.description}")
        print(f"Duration: {r.duration_ms:.2f} ms")
        print(f"\nExecution Plan:\n{r.plan}")
        print("-" * 80)


if __name__ == "__main__":
    main()
