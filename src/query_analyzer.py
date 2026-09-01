"""Query execution plan analyzer for VortexDBA.

Parses EXPLAIN ANALYZE output and detects common PostgreSQL
performance anti-patterns such as sequential scans on large tables,
missing indexes, external sorts, and correlated subqueries.
"""

import re
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Issue severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Issue:
    """Represents a detected performance issue."""
    severity: Severity
    pattern: str
    description: str
    node_type: str
    table: str
    rows: int
    suggestion: str
    line_number: int = 0


@dataclass
class PlanNode:
    """Represents a single node in the execution plan tree."""
    node_type: str
    relation: str = ""
    alias: str = ""
    startup_time: float = 0.0
    total_time: float = 0.0
    plan_rows: int = 0
    actual_rows: int = 0
    loops: int = 1
    filter: str = ""
    rows_removed: int = 0
    sort_method: str = ""
    sort_space: str = ""
    hash_cond: str = ""
    index_cond: str = ""
    join_type: str = ""
    subplan_name: str = ""
    buffers_hit: int = 0
    buffers_read: int = 0
    temp_read: int = 0
    temp_written: int = 0
    children: list = field(default_factory=list)


# Regex patterns for parsing EXPLAIN ANALYZE output
# Matches both root nodes and child nodes (with ->)
NODE_PATTERN = re.compile(
    r"^(\s*)(?:->\s+)?([\w\s]+?)(?:\s+on\s+(\w+))?(?:\s+(\w+))?\s+\("
    r"cost=([\d.]+)\.\.([\d.]+)\s+rows=(\d+)\s+width=(\d+)\)"
    r"(?:\s+\(actual time=([\d.]+)\.\.([\d.]+)\s+rows=(\d+)\s+loops=(\d+)\))?"
)

ACTUAL_TIME_PATTERN = re.compile(
    r"actual time=([\d.]+)\.\.([\d.]+)\s+rows=(\d+)\s+loops=(\d+)"
)

FILTER_PATTERN = re.compile(r"^\s+Filter:\s+(.+)")
ROWS_REMOVED_PATTERN = re.compile(r"Rows Removed by Filter:\s+(\d+)")
SORT_METHOD_PATTERN = re.compile(r"Sort Method:\s+(\w+)(?:\s+(\w+))?")
HASH_COND_PATTERN = re.compile(r"Hash Cond:\s+\((.+)\)")
INDEX_COND_PATTERN = re.compile(r"Index Cond:\s+\((.+)\)")
SUBPLAN_PATTERN = re.compile(r"SubPlan\s+(\d+)")
BUFFERS_HIT_PATTERN = re.compile(r"Buffers:\s+shared hit=(\d+)")
BUFFERS_READ_PATTERN = re.compile(r"(?:read)=(\d+)")
TEMP_READ_PATTERN = re.compile(r"temp read=(\d+)")
TEMP_WRITTEN_PATTERN = re.compile(r"written=(\d+)")


def parse_plan_text(plan_text: str) -> list[PlanNode]:
    """Parse EXPLAIN ANALYZE text output into a list of PlanNode objects."""
    lines = plan_text.strip().split("\n")
    nodes = []
    current_node = None

    for line in lines:
        line = line.rstrip()

        # Match node header
        node_match = NODE_PATTERN.match(line)
        if node_match:
            if current_node:
                nodes.append(current_node)

            indent = len(node_match.group(1))
            node_type = node_match.group(2).strip()
            relation = node_match.group(3) or ""
            alias = node_match.group(4) or ""

            current_node = PlanNode(
                node_type=node_type,
                relation=relation,
                alias=alias,
            )

            if node_match.group(9) and node_match.group(10):
                current_node.startup_time = float(node_match.group(9))
                current_node.total_time = float(node_match.group(10))
                current_node.actual_rows = int(node_match.group(11))
                current_node.loops = int(node_match.group(12))

            current_node.plan_rows = int(node_match.group(7))
            continue

        if current_node is None:
            continue

        # Parse filter
        filter_match = FILTER_PATTERN.search(line)
        if filter_match:
            current_node.filter = filter_match.group(1)

        # Parse rows removed
        removed_match = ROWS_REMOVED_PATTERN.search(line)
        if removed_match:
            current_node.rows_removed = int(removed_match.group(1))

        # Parse sort method
        sort_match = SORT_METHOD_PATTERN.search(line)
        if sort_match:
            current_node.sort_method = sort_match.group(1)
            current_node.sort_space = sort_match.group(2) or ""

        # Parse hash condition
        hash_match = HASH_COND_PATTERN.search(line)
        if hash_match:
            current_node.hash_cond = hash_match.group(1)

        # Parse index condition
        index_match = INDEX_COND_PATTERN.search(line)
        if index_match:
            current_node.index_cond = index_match.group(1)

        # Parse subplan
        subplan_match = SUBPLAN_PATTERN.search(line)
        if subplan_match:
            current_node.subplan_name = f"SubPlan {subplan_match.group(1)}"

        # Parse buffers
        hit_match = BUFFERS_HIT_PATTERN.search(line)
        if hit_match:
            current_node.buffers_hit = int(hit_match.group(1))

        read_match = BUFFERS_READ_PATTERN.search(line)
        if read_match:
            current_node.buffers_read = int(read_match.group(1))

        temp_r_match = TEMP_READ_PATTERN.search(line)
        if temp_r_match:
            current_node.temp_read = int(temp_r_match.group(1))

        temp_w_match = TEMP_WRITTEN_PATTERN.search(line)
        if temp_w_match:
            current_node.temp_written = int(temp_w_match.group(1))

    if current_node:
        nodes.append(current_node)

    return nodes


def detect_issues(nodes: list[PlanNode]) -> list[Issue]:
    """Analyze plan nodes and detect performance anti-patterns."""
    issues = []

    for i, node in enumerate(nodes):
        # Skip nodes without a table name
        if not node.relation:
            continue

        # 1. Sequential Scan on large table
        if node.node_type == "Seq Scan" and node.plan_rows > 10000:
            severity = Severity.CRITICAL if node.plan_rows > 100000 else Severity.WARNING
            table = node.relation
            col = _extract_column(node.filter)
            if col == "column":
                continue  # Skip if we can't extract column
            suggestion = f"CREATE INDEX idx_{table}_{col} ON {table}({col})"
            issues.append(Issue(
                severity=severity,
                pattern="seq_scan_large_table",
                description=f"Sequential scan on {table} with {node.plan_rows:,} estimated rows",
                node_type=node.node_type,
                table=table,
                rows=node.plan_rows,
                suggestion=suggestion,
                line_number=i,
            ))

        # 2. High rows removed by filter (missing index)
        if node.rows_removed > 10000:
            table = node.relation
            col = _extract_column(node.filter)
            if col == "column":
                continue  # Skip if we can't extract column
            severity = Severity.CRITICAL if node.rows_removed > 100000 else Severity.WARNING
            issues.append(Issue(
                severity=severity,
                pattern="high_filter_removal",
                description=f"{node.rows_removed:,} rows removed by filter on {table}",
                node_type=node.node_type,
                table=table,
                rows=node.rows_removed,
                suggestion=f"Consider adding index on {table}({col}) for filter condition",
                line_number=i,
            ))

        # 3. External merge sort (disk usage)
        if node.sort_method == "external merge":
            table = node.relation
            issues.append(Issue(
                severity=Severity.WARNING,
                pattern="external_sort",
                description=f"External merge sort on {table} using disk ({node.sort_space})",
                node_type=node.node_type,
                table=table,
                rows=node.plan_rows,
                suggestion=f"Increase work_mem or add index to avoid sorting",
                line_number=i,
            ))

        # 4. Nested Loop with high actual time
        if node.node_type == "Nested Loop" and node.total_time > 100:
            issues.append(Issue(
                severity=Severity.WARNING,
                pattern="slow_nested_loop",
                description=f"Nested loop took {node.total_time:.1f}ms",
                node_type=node.node_type,
                table=node.relation,
                rows=node.actual_rows,
                suggestion="Consider adding indexes on join columns or using hash join",
                line_number=i,
            ))

        # 5. Correlated subquery (SubPlan with repeated scans)
        if node.subplan_name and node.loops > 1000:
            issues.append(Issue(
                severity=Severity.CRITICAL,
                pattern="correlated_subquery",
                description=f"Correlated subquery executed {node.loops:,} times",
                node_type=node.node_type,
                table=node.relation,
                rows=node.actual_rows,
                suggestion="Rewrite as JOIN or use CTE to avoid repeated execution",
                line_number=i,
            ))

        # 6. High buffer usage
        if node.buffers_hit > 100000:
            issues.append(Issue(
                severity=Severity.WARNING,
                pattern="high_buffer_usage",
                description=f"High buffer usage: {node.buffers_hit:,} hits",
                node_type=node.node_type,
                table=node.relation,
                rows=node.actual_rows,
                suggestion="Query accesses many pages; consider adding selective indexes",
                line_number=i,
            ))

        # 7. Temp file usage
        if node.temp_written > 0:
            issues.append(Issue(
                severity=Severity.WARNING,
                pattern="temp_file_usage",
                description=f"Query used temp files: {node.temp_written:,} written",
                node_type=node.node_type,
                table=node.relation,
                rows=node.actual_rows,
                suggestion="Increase work_mem or optimize query to reduce memory pressure",
                line_number=i,
            ))

    return issues


def _extract_column(filter_expr: str) -> str:
    """Extract column name from a filter expression."""
    if not filter_expr:
        return "column"

    # Skip HAVING clauses (aggregate functions)
    if "count(" in filter_expr.lower() or "sum(" in filter_expr.lower():
        return "column"

    # Handle patterns like ((column)::text = 'value'::text)
    # Extract the first word after opening parenthesis
    match = re.search(r"\(\(?(\w+)\)", filter_expr)
    if match:
        col = match.group(1)
        # Skip type casts like text, numeric, timestamp
        if col not in ("text", "numeric", "timestamp", "integer", "varchar"):
            return col

    # Handle patterns like column = value
    match = re.search(r"(\w+)\s*[=<>!]", filter_expr)
    if match:
        col = match.group(1)
        if col not in ("text", "numeric", "timestamp", "integer", "varchar"):
            return col

    return "column"


def analyze_plan(plan_text: str) -> list[Issue]:
    """Main entry point: parse plan text and return detected issues."""
    nodes = parse_plan_text(plan_text)
    return detect_issues(nodes)


def format_issues(issues: list[Issue]) -> str:
    """Format issues into a readable report."""
    if not issues:
        return "No performance issues detected."

    lines = []
    lines.append("=" * 70)
    lines.append("PERFORMANCE ANALYSIS REPORT")
    lines.append("=" * 70)

    for severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
        severity_issues = [i for i in issues if i.severity == severity]
        if not severity_issues:
            continue

        lines.append(f"\n[{severity.value}] ({len(severity_issues)} issues)")
        lines.append("-" * 70)

        for issue in severity_issues:
            lines.append(f"  Pattern: {issue.pattern}")
            lines.append(f"  Table: {issue.table}")
            lines.append(f"  Rows: {issue.rows:,}")
            lines.append(f"  Description: {issue.description}")
            lines.append(f"  Suggestion: {issue.suggestion}")
            lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)
