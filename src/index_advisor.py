"""Index advisor module for VortexDBA.

Analyzes detected performance issues and generates actionable
index recommendations. Deduplicates and prioritizes suggestions
to avoid redundant or conflicting indexes.
"""

import re
from dataclasses import dataclass

from query_analyzer import Issue, Severity


@dataclass
class IndexRecommendation:
    """Represents a recommended index creation."""
    table: str
    columns: list[str]
    index_type: str  # btree, hash, gin, gist
    reason: str
    priority: int  # 1 = highest
    estimated_impact: str
    create_statement: str


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

    # Pattern: (column)::text = 'value'::text
    for match in re.finditer(r"\((\w+)\)", filter_expr):
        col = match.group(1)
        if col not in columns:
            columns.append(col)

    # Pattern: column = value or column > value
    for match in re.finditer(r"(\w+)\s*[=<>!]", filter_expr):
        col = match.group(1)
        if col not in columns and col not in ("text", "numeric", "timestamp"):
            columns.append(col)

    return columns


def extract_columns_from_condition(condition: str) -> list[str]:
    """Extract column names from join or index conditions."""
    if not condition:
        return []

    columns = []
    for match in re.finditer(r"(\w+\.\w+|\w+)", condition):
        col = match.group(1)
        # Remove table prefix
        if "." in col:
            col = col.split(".")[-1]
        if col not in columns and col not in ("text", "numeric"):
            columns.append(col)

    return columns


def is_index_redundant(table: str, columns: list[str]) -> bool:
    """Check if an index already exists or is redundant with existing ones."""
    for idx_name, (idx_table, idx_cols) in EXISTING_INDEXES.items():
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


def generate_recommendations(issues: list[Issue]) -> list[IndexRecommendation]:
    """Generate index recommendations from detected issues."""
    recommendations = []
    seen = set()

    for issue in issues:
        if issue.severity == Severity.INFO:
            continue

        table = issue.table
        if not table:
            continue

        # Extract columns based on issue type
        columns = []
        if issue.pattern in ("seq_scan_large_table", "high_filter_removal"):
            # Extract from the issue description/suggestion
            col_match = re.search(r"(\w+)\((\w+)\)", issue.suggestion)
            if col_match:
                columns = [col_match.group(2)]
            else:
                # Try to extract from pattern name
                col_match = re.search(r"idx_\w+_(\w+)", issue.suggestion)
                if col_match:
                    columns = [col_match.group(1)]

        if not columns:
            continue

        # Create dedup key
        key = (table, tuple(columns))
        if key in seen:
            continue
        seen.add(key)

        # Check if redundant
        if is_index_redundant(table, columns):
            continue

        # Determine priority
        priority = 1 if issue.severity == Severity.CRITICAL else 2
        if issue.rows > 100000:
            priority = 1

        idx_name = generate_index_name(table, columns)
        create_stmt = f"CREATE INDEX {idx_name} ON {table} ({', '.join(columns)});"

        recommendations.append(IndexRecommendation(
            table=table,
            columns=columns,
            index_type="btree",
            reason=issue.description,
            priority=priority,
            estimated_impact=estimate_impact(issue),
            create_statement=create_stmt,
        ))

    return prioritize_recommendations(recommendations)


def format_recommendations(recommendations: list[IndexRecommendation]) -> str:
    """Format recommendations into a readable report."""
    if not recommendations:
        return "No index recommendations."

    lines = []
    lines.append("=" * 70)
    lines.append("INDEX RECOMMENDATIONS")
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
    lines = ["-- VortexDBA Index Recommendations", "-- Apply with caution in production\n"]
    for rec in recommendations:
        lines.append(rec.create_statement)
    return "\n".join(lines)
