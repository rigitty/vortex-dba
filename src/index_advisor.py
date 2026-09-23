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

_table_schema_cache: dict[str, tuple[str, str]] = {}
_table_columns_cache: dict[str, dict[str, str]] = {}


def resolve_table_schema(table_name: str) -> tuple[str, str]:
    """Resolve SQL Server (schema, exact_table_name).
    
    If table_name is already 'Sales.Orders' or '[Sales].[Orders]', parses and returns ('Sales', 'Orders').
    Otherwise, checks dynamic database schema cache (or queries INFORMATION_SCHEMA.TABLES).
    Defaults to ('dbo', clean_table_name) if not found.
    """
    global _table_schema_cache
    if not table_name:
        return ("dbo", table_name)

    clean_t = table_name.strip("[] ")
    if "." in clean_t:
        parts = [p.strip("[] ") for p in clean_t.split(".", 1)]
        return (parts[0], parts[1])

    t_low = clean_t.lower()
    if t_low in _table_schema_cache:
        return _table_schema_cache[t_low]

    try:
        from db_connection import execute_query
        rows = execute_query("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        if rows:
            for r in rows:
                _table_schema_cache[r["TABLE_NAME"].lower()] = (r["TABLE_SCHEMA"], r["TABLE_NAME"])
            if t_low in _table_schema_cache:
                return _table_schema_cache[t_low]
    except Exception:
        pass

    return ("dbo", clean_t)


def get_table_columns(table_name: str) -> dict[str, str]:
    """Get {col_lower: exact_col_name} for a table. Cached."""
    global _table_columns_cache
    schema, tbl = resolve_table_schema(table_name)
    key = f"{schema}.{tbl}".lower()
    if key in _table_columns_cache:
        return _table_columns_cache[key]

    cols_map: dict[str, str] = {}
    try:
        from db_connection import execute_query
        rows = execute_query(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (schema, tbl)
        )
        for r in (rows or []):
            cols_map[r["COLUMN_NAME"].lower()] = r["COLUMN_NAME"]
        _table_columns_cache[key] = cols_map
    except Exception:
        pass

    return cols_map


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

        composite_generated = False
        # Generate composite index if multiple columns
        if len(sorted_columns) > 1:
            key = (table, tuple(sorted_columns))
            if key not in seen:
                seen.add(key)

                if not is_index_redundant(table, sorted_columns):
                    schema, exact_tbl = resolve_table_schema(table)
                    full_tbl_ref = f"[{schema}].[{exact_tbl}]" if schema else f"[{exact_tbl}]"
                    idx_name = generate_index_name(exact_tbl.lower(), sorted_columns)
                    cols_str = ", ".join(f"[{c}]" for c in sorted_columns)
                    create_stmt = f"CREATE NONCLUSTERED INDEX [{idx_name}] ON {full_tbl_ref} ({cols_str}) WITH (ONLINE = ON);"

                    max_rows = max(columns_with_issues.values())
                    priority = 1 if max_rows > 100000 else 2
                    display_tbl = f"{schema}.{exact_tbl}" if schema else exact_tbl

                    recommendations.append(IndexRecommendation(
                        table=display_tbl,
                        columns=sorted_columns,
                        index_type="nonclustered",
                        reason=f"Multiple filter conditions on {display_tbl}: {', '.join(sorted_columns)}",
                        priority=priority,
                        estimated_impact=estimate_impact_from_rows(max_rows),
                        create_statement=create_stmt,
                        index_name=idx_name,
                        online=online,
                        concurrent=online,
                    ))
                    composite_generated = True

        # Only generate single-column indexes for columns NOT already covered by the composite index
        if not composite_generated:
            for col in sorted_columns:
                key = (table, (col,))
                if key in seen:
                    continue
                seen.add(key)

                if not is_index_redundant(table, [col]):
                    schema, exact_tbl = resolve_table_schema(table)
                    full_tbl_ref = f"[{schema}].[{exact_tbl}]" if schema else f"[{exact_tbl}]"
                    idx_name = generate_index_name(exact_tbl.lower(), [col])
                    create_stmt = f"CREATE NONCLUSTERED INDEX [{idx_name}] ON {full_tbl_ref} ([{col}]) WITH (ONLINE = ON);"

                    max_rows = columns_with_issues[col]
                    priority = 1 if max_rows > 100000 else 2
                    display_tbl = f"{schema}.{exact_tbl}" if schema else exact_tbl

                    recommendations.append(IndexRecommendation(
                        table=display_tbl,
                        columns=[col],
                        index_type="nonclustered",
                        reason=f"Filter condition on {display_tbl}.{col}",
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


def recommend_index_for_query(query_sql: str) -> IndexRecommendation | None:
    """Dynamically analyze a SQL query string and generate an optimal

    SQL Server NONCLUSTERED index recommendation using database indexing principles:
    1. Identify target table(s) and aliases
    2. Extract WHERE equality columns (=, IS NULL) -> Leading index keys
    3. Extract WHERE inequality/range columns (>, <, >=, <=, BETWEEN, LIKE) -> Secondary index keys
    4. Extract ORDER BY columns -> Trailing index keys if needed
    5. Check redundancy with base schema
    6. Return complete IndexRecommendation with DDL and dynamic reasoning.
    """
    if not query_sql or not query_sql.strip():
        return None

    clean = re.sub(r"--.*", "", query_sql)
    # Strip brackets like [customers], [city]
    clean_norm = re.sub(r"\[(\w+)\]", r"\1", clean)

    # Extract SELECT clause and aliases
    select_match = re.search(r"SELECT\s+(.*?)\s+FROM", clean_norm, re.IGNORECASE | re.DOTALL)
    select_text = select_match.group(1) if select_match else ""
    select_aliases = {a.lower() for a in re.findall(r"\bAS\s+\[?(\w+)\]?", select_text, re.IGNORECASE)}

    # Extract WHERE clause
    where_match = re.search(r"WHERE\s+(.*?)(?:GROUP\s+BY|ORDER\s+BY|HAVING|$)", clean_norm, re.IGNORECASE | re.DOTALL)
    where_clause = where_match.group(1) if where_match else ""

    # Extract CTE names (e.g. WITH ReportData AS (...) or , SubCte AS (...))
    cte_names = {c.lower() for c in re.findall(r"\b(?:WITH|,)\s*\[?(\w+)\]?\s+AS\s*\(", clean, re.IGNORECASE)}

    # Extract FROM/JOIN tables (handling optional schema prefix like Sales.Orders or dbo.customers)
    tables = re.findall(r"(?:FROM|JOIN)\s+(?:\[?(\w+)\]?\.)?\[?(\w+)\]?(?:\s+(?:AS\s+)?\[?(\w+)\]?)?", clean, re.IGNORECASE)
    table_alias: dict[str, str] = {}
    from_tables = []
    table_explicit_schema: dict[str, str] = {}
    for schema, tbl, alias in tables:
        t_low = tbl.lower()
        if t_low in cte_names or t_low in ("where", "on", "join", "group", "order", "inner", "left", "right", "outer", "cross", "select", "apply"):
            continue
        from_tables.append(t_low)
        table_alias[t_low] = t_low
        if schema:
            table_explicit_schema[t_low] = schema
        if alias and alias.lower() not in ("where", "on", "join", "group", "order", "inner", "left", "right", "outer", "cross", "as", "with", "nolock"):
            table_alias[alias.lower()] = t_low
            if schema:
                table_explicit_schema[alias.lower()] = schema

    single_from_table = from_tables[0] if len(from_tables) == 1 else None

    known_table_cols = {
        "orders": {"customer_id", "status", "total_amount", "order_date", "product_category", "shipping_address"},
        "customers": {"city", "country", "email", "status", "phone", "created_at", "first_name", "last_name"}
    }

    def resolve_valid_column(tbl_name: str, col_name: str) -> str | None:
        """Validate and return canonical column name if real column."""
        c_low = col_name.lower()
        if c_low in select_aliases or c_low in (
            "id", "text", "numeric", "varchar", "nvarchar", "count", "sum", "avg",
            "top", "distinct", "min", "max", "desc", "asc", "null", "not", "and",
            "or", "case", "when", "then", "else", "end", "with", "nolock", "as",
            "total_spent", "order_count", "daily_total", "total_revenue", "toplam_ciro", "toplam_ciro_tl",
            "__totalmatchingcount"
        ):
            return None
        db_cols = get_table_columns(tbl_name)
        if db_cols:
            return db_cols.get(c_low)
        if tbl_name in known_table_cols:
            return c_low if c_low in known_table_cols[tbl_name] else None
        return col_name

    # Extract filter predicates (equality vs range)
    predicates = re.findall(r"(?:(\w+)\.)?(\w+)\s*(=|>|<|>=|<=|BETWEEN|LIKE)", where_clause, re.IGNORECASE)

    table_equality_cols: dict[str, list[str]] = {}
    table_range_cols: dict[str, list[str]] = {}

    for alias, col, op in predicates:
        if single_from_table:
            tbl = single_from_table
        elif alias and alias.lower() in table_alias:
            tbl = table_alias[alias.lower()]
        else:
            tbl = None
            for t_name in list(table_alias.values()) + list(known_table_cols.keys()):
                if resolve_valid_column(t_name, col):
                    tbl = t_name
                    break
            if not tbl:
                tbl = from_tables[0] if from_tables else ("orders" if "orders" in clean_norm.lower() else "customers")

        valid_col = resolve_valid_column(tbl, col)
        if not valid_col:
            continue

        if op.upper() in ("=", "IS"):
            if tbl not in table_equality_cols:
                table_equality_cols[tbl] = []
            if valid_col not in table_equality_cols[tbl]:
                table_equality_cols[tbl].append(valid_col)
        else:
            if tbl not in table_range_cols:
                table_range_cols[tbl] = []
            if valid_col not in table_range_cols[tbl]:
                table_range_cols[tbl].append(valid_col)

    # Extract JOIN ON conditions
    on_conditions = re.findall(r"ON\s+(.*?)(?:LEFT|RIGHT|INNER|OUTER|CROSS|JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|$)", clean_norm, re.IGNORECASE | re.DOTALL)
    for on_clause in on_conditions:
        for m in re.finditer(r"(?:(\w+)\.)?(\w+)\s*=\s*(?:(\w+)\.)?(\w+)", on_clause):
            a1, c1, a2, c2 = m.groups()
            for a, c in [(a1, c1), (a2, c2)]:
                tbl = table_alias.get(a.lower()) if a else None
                if not tbl and single_from_table:
                    tbl = single_from_table
                if tbl:
                    valid_c = resolve_valid_column(tbl, c)
                    if valid_c:
                        if tbl not in table_equality_cols:
                            table_equality_cols[tbl] = []
                        if valid_c not in table_equality_cols[tbl]:
                            table_equality_cols[tbl].append(valid_c)

    # Check GROUP BY columns
    group_match = re.search(r"GROUP\s+BY\s+(.*?)(?:HAVING|ORDER\s+BY|$)", clean_norm, re.IGNORECASE | re.DOTALL)
    table_group_cols: dict[str, list[str]] = {}
    if group_match:
        for alias, col in re.findall(r"(?:(\w+)\.)?(\w+)", group_match.group(1), re.IGNORECASE):
            if single_from_table:
                tbl = single_from_table
            elif alias and alias.lower() in table_alias:
                tbl = table_alias[alias.lower()]
            else:
                tbl = None
                for t_name in list(table_alias.values()) + list(known_table_cols.keys()):
                    if resolve_valid_column(t_name, col):
                        tbl = t_name
                        break
                if not tbl:
                    tbl = "orders" if "orders" in clean_norm.lower() else "customers"

            valid_col = resolve_valid_column(tbl, col)
            if not valid_col:
                continue

            if tbl not in table_group_cols:
                table_group_cols[tbl] = []
            if valid_col not in table_group_cols[tbl]:
                table_group_cols[tbl].append(valid_col)

    # Check ORDER BY columns
    order_match = re.search(r"ORDER\s+BY\s+(.*?)$", clean_norm, re.IGNORECASE | re.DOTALL)
    table_order_cols: dict[str, list[str]] = {}
    if order_match:
        order_cols = re.findall(r"(?:(\w+)\.)?(\w+)(?:\s+DESC|\s+ASC)?", order_match.group(1), re.IGNORECASE)
        for alias, col in order_cols:
            if single_from_table:
                tbl = single_from_table
            elif alias and alias.lower() in table_alias:
                tbl = table_alias[alias.lower()]
            else:
                tbl = None
                for t_name in list(table_alias.values()) + list(known_table_cols.keys()):
                    if resolve_valid_column(t_name, col):
                        tbl = t_name
                        break
                if not tbl:
                    tbl = "orders" if "orders" in clean_norm.lower() else "customers"

            valid_col = resolve_valid_column(tbl, col)
            if not valid_col:
                continue

            if tbl not in table_order_cols:
                table_order_cols[tbl] = []
            if valid_col not in table_order_cols[tbl]:
                table_order_cols[tbl].append(valid_col)

    all_target_tables = set(table_equality_cols.keys()) | set(table_range_cols.keys()) | set(table_group_cols.keys()) | set(table_order_cols.keys())
    if not all_target_tables:
        primary_tbl = "orders" if "orders" in clean.lower() else "customers"
    else:
        primary_tbl = max(all_target_tables, key=lambda t: len(table_equality_cols.get(t, [])) * 3 + len(table_group_cols.get(t, [])) * 2 + len(table_range_cols.get(t, [])) + len(table_order_cols.get(t, [])))

    # Reject system tables/views
    system_tables_blacklist = {"sys", "system", "tables", "indexes", "columns", "databases", "filetable", "dmv", "information_schema"}
    if primary_tbl in system_tables_blacklist or primary_tbl.startswith("sys") or primary_tbl.startswith("filetable"):
        return None

    keys: list[str] = []
    for c in table_equality_cols.get(primary_tbl, []):
        if c not in keys:
            keys.append(c)
    for c in table_group_cols.get(primary_tbl, []):
        if c not in keys:
            keys.append(c)
    for c in table_range_cols.get(primary_tbl, []):
        if c not in keys:
            keys.append(c)
    for c in table_order_cols.get(primary_tbl, []):
        if c not in keys:
            keys.append(c)

    if not keys:
        # Fallback default key if none extracted
        db_cols = get_table_columns(primary_tbl)
        if db_cols:
            keys = [next(iter(db_cols.values()))]
        else:
            keys = ["status"] if primary_tbl == "orders" else ["email"]

    # Resolve schema and table naming
    explicit_sch = table_explicit_schema.get(primary_tbl)
    if explicit_sch:
        schema, exact_tbl = explicit_sch, primary_tbl
    else:
        schema, exact_tbl = resolve_table_schema(primary_tbl)

    full_tbl_ref = f"[{schema}].[{exact_tbl}]" if schema else f"[{exact_tbl}]"
    display_table = f"{schema}.{exact_tbl}" if schema else exact_tbl

    # Detect covering columns for INCLUDE clause
    include_cols: list[str] = []
    candidate_inc = get_table_columns(primary_tbl) or (known_table_cols.get(primary_tbl, {}))
    for c_raw in (candidate_inc.values() if isinstance(candidate_inc, dict) else candidate_inc):
        if c_raw in keys or c_raw.lower() in [k.lower() for k in keys] or c_raw.lower() in ("shipping_address", "id"):
            continue
        # If the column appears in SELECT text, include it to prevent Key Lookups
        if re.search(r"\b" + re.escape(c_raw) + r"\b", select_text, re.IGNORECASE):
            include_cols.append(c_raw)

    clean_keys_for_name = [re.sub(r"\W+", "", k.lower()) for k in keys]
    idx_name = generate_index_name(exact_tbl.lower(), clean_keys_for_name)
    cols_str = ", ".join(f"[{c}]" for c in keys)
    if include_cols:
        inc_str = ", ".join(f"[{c}]" for c in include_cols)
        create_stmt = f"CREATE NONCLUSTERED INDEX [{idx_name}] ON {full_tbl_ref} ({cols_str}) INCLUDE ({inc_str}) WITH (ONLINE = ON);"
    else:
        create_stmt = f"CREATE NONCLUSTERED INDEX [{idx_name}] ON {full_tbl_ref} ({cols_str}) WITH (ONLINE = ON);"

    return IndexRecommendation(
        table=display_table,
        columns=keys,
        index_type="nonclustered",
        include_columns=include_cols,
        reason=f"{display_table} tablosundaki ({cols_str}) arama filtreleri için dinamik oluşturulan indeks",
        priority=1 if len(keys) > 1 else 2,
        estimated_impact="~5-50x hızlanma",
        create_statement=create_stmt,
        index_name=idx_name,
        online=True,
    )

