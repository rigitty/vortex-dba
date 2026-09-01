"""Index advisor module for VortexDBA (SQL Server).

Analyzes detected performance issues and generates actionable
SQL Server NONCLUSTERED index recommendations with ONLINE options.
Deduplicates and prioritizes suggestions to avoid redundant indexes.
"""

import re
from dataclasses import dataclass, field

from query_analyzer import Issue, Severity


@dataclass
class IndexRecommendation:
    """Represents a recommended index creation for SQL Server."""
    table: str
    columns: list[str]
    index_type: str = "nonclustered"
    include_columns: list[str] = field(default_factory=list)
    reason: str = ""
    priority: int = 1  # 1 = highest
    estimated_impact: str = ""
    create_statement: str = ""
    index_name: str = ""
    online: bool = True
    concurrent: bool = True  # Backward compatibility alias


# Known existing indexes (from schema)
EXISTING_INDEXES = {
    "idx_orders_customer_id": ("orders", ["customer_id"]),
    "idx_customers_email": ("customers", ["email"]),
}


def extract_columns_from_filter(filter_expr: str) -> list[str]:
    """Extract column names from a filter expression."""
    if not filter_expr:
        return []

    columns = []

    # Pattern: [column] = value
    for match in re.finditer(r"\[(\w+)\]\s*[=<>!~]", filter_expr):
        col = match.group(1)
        if col not in columns and col not in ("text", "numeric", "timestamp", "varchar", "nvarchar"):
            columns.append(col)

    # Pattern: (column)::text = 'value'::text
    for match in re.finditer(r"\((\w+)\)", filter_expr):
        col = match.group(1)
        if col not in columns and col not in ("text", "numeric", "timestamp", "varchar", "nvarchar"):
            columns.append(col)

    # Pattern: column = value or column > value
    for match in re.finditer(r"(\w+)\s*[=<>!]", filter_expr):
        col = match.group(1)
        if col not in columns and col not in ("text", "numeric", "timestamp", "varchar", "nvarchar"):
            columns.append(col)

    return columns


def extract_columns_from_condition(condition: str) -> list[str]:
    """Extract column names from join or index conditions."""
    if not condition:
        return []

    columns = []
    for match in re.finditer(r"\[?(\w+)\]?", condition):
        col = match.group(1)
        if col not in columns and col not in ("text", "numeric", "varchar", "nvarchar", "dbo", "vortex_db"):
            columns.append(col)

    return columns


def is_index_redundant(table: str, columns: list[str],
                       existing: dict[str, tuple[str, list[str]]] | None = None) -> bool:
    """Check if an index already exists or is redundant with existing ones."""
    indexes_to_check = existing if existing is not None else EXISTING_INDEXES
    for idx_name, (idx_table, idx_cols) in indexes_to_check.items():
        if idx_table == table:
            # Check if existing index covers these columns
            if all(c in idx_cols for c in columns):
                return True
            # Check if new index is a prefix of existing
            if columns == idx_cols[:len(columns)]:
                return True
    return False


def generate_index_name(table: str, columns: list[str]) -> str:
    """Generate a standard index name."""
    col_part = "_".join(columns[:3])  # Max 3 columns in name
    return f"idx_{table}_{col_part}"


def estimate_impact(issue: Issue) -> str:
    """Estimate the performance impact of adding an index."""
    if issue.rows > 500000:
        return "~50-100x faster"
    elif issue.rows > 100000:
        return "~10-50x faster"
    elif issue.rows > 10000:
        return "~5-10x faster"
    else:
        return "~2-5x faster"


def prioritize_recommendations(recommendations: list[IndexRecommendation]) -> list[IndexRecommendation]:
    """Sort recommendations by priority (highest first)."""
    return sorted(recommendations, key=lambda r: r.priority)


def generate_recommendations(issues: list[Issue], online: bool = True, concurrent: bool | None = None) -> list[IndexRecommendation]:
    """Generate SQL Server index recommendations from detected issues.

    Supports both single-column and composite indexes with optional ONLINE execution.

    Args:
        issues: List of detected performance issues.
        online: If True, use WITH (ONLINE = ON) where supported.
        concurrent: Alias for online (PostgreSQL compatibility).
    """
    if concurrent is not None:
        online = concurrent

    recommendations = []
    seen = set()

    # Group issues by table for composite index detection
    table_issues: dict[str, list[Issue]] = {}
    for issue in issues:
        if issue.severity == Severity.INFO or not issue.table:
            continue
        if issue.table not in table_issues:
            table_issues[issue.table] = []
        table_issues[issue.table].append(issue)

    # Process each table
    for table, table_issue_list in table_issues.items():
        columns_with_issues: dict[str, int] = {}  # column -> max severity rows

        for issue in table_issue_list:
            if issue.pattern in ("seq_scan_large_table", "table_scan_large_table", "high_filter_removal", "key_lookup_overhead"):
                cols = issue.columns
                if not cols:
                    col_match = re.search(r"(\w+)\((\w+)\)", issue.suggestion)
                    if col_match:
                        cols = [col_match.group(2)]
                for col in cols:
                    if col and col != "column":
                        columns_with_issues[col] = max(columns_with_issues.get(col, 0), issue.rows)

        if not columns_with_issues:
            continue

        # Sort columns by impact (most rows first)
        sorted_columns = sorted(columns_with_issues.keys(),
                                key=lambda c: columns_with_issues[c], reverse=True)

        # Generate composite index if multiple columns
        if len(sorted_columns) > 1:
            key = (table, tuple(sorted_columns))
            if key not in seen:
                seen.add(key)

                if not is_index_redundant(table, sorted_columns):
                    idx_name = generate_index_name(table, sorted_columns)
                    create_stmt = f"CREATE NONCLUSTERED INDEX {idx_name} ON {table} ({', '.join(sorted_columns)});"

                    max_rows = max(columns_with_issues.values())
                    priority = 1 if max_rows > 100000 else 2

                    recommendations.append(IndexRecommendation(
                        table=table,
                        columns=sorted_columns,
                        index_type="nonclustered",
                        reason=f"Multiple filter conditions on {table}: {', '.join(sorted_columns)}",
                        priority=priority,
                        estimated_impact=estimate_impact_from_rows(max_rows),
                        create_statement=create_stmt,
                        index_name=idx_name,
                        online=online,
                        concurrent=online,
                    ))

        # Also generate single-column indexes for high-impact columns
        for col in sorted_columns:
            key = (table, (col,))
            if key in seen:
                continue
            seen.add(key)

            if not is_index_redundant(table, [col]):
                idx_name = generate_index_name(table, [col])
                create_stmt = f"CREATE NONCLUSTERED INDEX {idx_name} ON {table} ({col});"

                max_rows = columns_with_issues[col]
                priority = 1 if max_rows > 100000 else 2

                recommendations.append(IndexRecommendation(
                    table=table,
                    columns=[col],
                    index_type="nonclustered",
                    reason=f"Filter condition on {table}.{col}",
                    priority=priority,
                    estimated_impact=estimate_impact_from_rows(max_rows),
                    create_statement=create_stmt,
                    index_name=idx_name,
                    online=online,
                    concurrent=online,
                ))

    return prioritize_recommendations(recommendations)


def estimate_impact_from_rows(rows: int) -> str:
    """Estimate performance impact based on row count."""
    if rows > 500000:
        return "~50-100x faster"
    elif rows > 100000:
        return "~10-50x faster"
    elif rows > 10000:
        return "~5-10x faster"
    else:
        return "~2-5x faster"


def format_recommendations(recommendations: list[IndexRecommendation]) -> str:
    """Format recommendations into a readable report."""
    if not recommendations:
        return "No index recommendations."

    lines = []
    lines.append("=" * 70)
    lines.append("INDEX RECOMMENDATIONS (SQL SERVER)")
    lines.append("=" * 70)

    for i, rec in enumerate(recommendations, 1):
        lines.append(f"\n[{i}] Table: {rec.table}")
        lines.append(f"    Columns: {', '.join(rec.columns)}")
        lines.append(f"    Type: {rec.index_type}")
        lines.append(f"    Reason: {rec.reason}")
        lines.append(f"    Impact: {rec.estimated_impact}")
        lines.append(f"    SQL: {rec.create_statement}")

    lines.append("\n" + "=" * 70)
    lines.append(f"Total recommendations: {len(recommendations)}")
    lines.append("=" * 70)

    return "\n".join(lines)


def get_apply_sql(recommendations: list[IndexRecommendation]) -> str:
    """Generate a SQL script to apply all recommendations."""
    lines = ["-- VortexDBA SQL Server Index Recommendations", "-- Apply with caution in production\n"]
    for rec in recommendations:
        lines.append(rec.create_statement)
    return "\n".join(lines)
