"""Auto-remediation module for VortexDBA.

Applies recommended indexes, benchmarks before/after performance,
and rolls back indexes that cause degradation.
"""

import re
import sys
import time
from dataclasses import dataclass, field

from db_connection import get_connection, execute_query
from slow_queries import SLOW_QUERIES
from query_analyzer import analyze_plan, Severity
from index_advisor import generate_recommendations, IndexRecommendation
from benchmark import (
    run_benchmark_suite, compare_results, format_benchmark_results,
    format_comparison, BenchmarkResult, ComparisonResult,
)
from safety_guard import check_safety, SafetyViolation
from state_store import (
    record_decision, record_index_applied, record_index_rolled_back, record_benchmark
)


@dataclass
class RemediationResult:
    """Result of applying a single index."""
    index_name: str
    table: str
    columns: list[str]
    create_sql: str
    applied: bool
    duration_ms: float
    error: str = ""


@dataclass
class RemediationReport:
    """Full report of the auto-remediation process."""
    dry_run: bool
    before_benchmarks: list[BenchmarkResult] = field(default_factory=list)
    after_benchmarks: list[BenchmarkResult] = field(default_factory=list)
    comparisons: list[ComparisonResult] = field(default_factory=list)
    applied_indexes: list[RemediationResult] = field(default_factory=list)
    rolled_back: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def get_slow_queries_for_benchmark() -> list[dict]:
    """Extract benchmarkable queries from slow_queries module."""
    queries = []
    for q in SLOW_QUERIES:
        queries.append({
            "name": q["name"],
            "query": q["query"],
            "params": q.get("params"),
        })
    return queries


def _extract_index_name(create_statement: str) -> str:
    """Extract index name from CREATE [NONCLUSTERED] INDEX statement."""
    match = re.search(
        r"CREATE\s+(?:UNIQUE\s+)?(?:NONCLUSTERED\s+|CLUSTERED\s+)?INDEX\s+(?:CONCURRENTLY\s+)?([^\s\(\)]+)",
        create_statement,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip("[] ")
    return "unknown_index"


def apply_index(rec: IndexRecommendation) -> RemediationResult:
    """Apply a single index recommendation in SQL Server."""
    start = time.perf_counter()
    try:
        conn = get_connection(autocommit=True)
        with conn.cursor() as cur:
            cur.execute(rec.create_statement)
        elapsed_ms = (time.perf_counter() - start) * 1000
        conn.close()

        return RemediationResult(
            index_name=rec.index_name or _extract_index_name(rec.create_statement),
            table=rec.table,
            columns=rec.columns,
            create_sql=rec.create_statement,
            applied=True,
            duration_ms=round(elapsed_ms, 2),
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return RemediationResult(
            index_name=rec.index_name or _extract_index_name(rec.create_statement),
            table=rec.table,
            columns=rec.columns,
            create_sql=rec.create_statement,
            applied=False,
            duration_ms=round(elapsed_ms, 2),
            error=str(e),
        )


def drop_index(index_name: str, table_name: str | None = None) -> bool:
    """Drop an index by name in SQL Server with schema qualification."""
    try:
        conn = get_connection(autocommit=True)
        with conn.cursor(as_dict=True) as cur:
            target_schema = None
            target_table = None

            cur.execute("""
                SELECT SCHEMA_NAME(t.schema_id) AS schemaname, t.name AS tablename
                FROM sys.indexes i
                JOIN sys.tables t ON t.object_id = i.object_id
                WHERE i.name = %s
            """, (index_name,))
            rows = cur.fetchall()
            if rows:
                target_schema = rows[0]["schemaname"]
                target_table = rows[0]["tablename"]
            elif table_name:
                from index_advisor import resolve_table_schema
                target_schema, target_table = resolve_table_schema(table_name)

            if target_schema and target_table:
                cur.execute(f"DROP INDEX IF EXISTS [{index_name}] ON [{target_schema}].[{target_table}]")
            elif target_table:
                cur.execute(f"DROP INDEX IF EXISTS [{index_name}] ON [{target_table}]")
            else:
                cur.execute(f"DROP INDEX IF EXISTS [{index_name}]")
        conn.close()
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to drop {index_name}: {e}")
        return False


def run_full_analysis() -> list[dict]:
    """Run slow queries and analyze plans to get recommendations."""
    from slow_queries import run_all_queries

    results = run_all_queries()
    all_issues = []
    for r in results:
        issues = analyze_plan(r.plan)
        all_issues.extend(issues)

    recommendations = generate_recommendations(all_issues)
    return recommendations


def run_remediation(dry_run: bool = False, apply: bool = True,
                    compare: bool = True, rollback: bool = True,
                    benchmark_runs: int = 3,
                    degradation_threshold: float = 10.0) -> RemediationReport:
    """Run the full auto-remediation pipeline.

    Args:
        dry_run: If True, only report what would be done.
        apply: If True, apply recommended indexes.
        compare: If True, run before/after benchmarks.
        rollback: If True, rollback degraded indexes.
        benchmark_runs: Number of benchmark runs per query.
        degradation_threshold: % threshold to consider an index degraded.
    """
    report = RemediationReport(dry_run=dry_run)

    # Step 1: Get recommendations
    print("\n[1/5] Analyzing queries and generating recommendations...")
    recommendations = run_full_analysis()

    if not recommendations:
        print("  No index recommendations generated.")
        return report

    print(f"  Found {len(recommendations)} index recommendations.")

    if dry_run:
        print("\n[DRY RUN] Would apply the following indexes:")
        for rec in recommendations:
            print(f"  - {rec.create_statement}")
        return report

    # Step 2: Before benchmarks
    if compare:
        print(f"\n[2/5] Running BEFORE benchmarks ({benchmark_runs} runs each)...")
        queries = get_slow_queries_for_benchmark()
        report.before_benchmarks = run_benchmark_suite(queries, benchmark_runs)
        print(format_benchmark_results(report.before_benchmarks))
    else:
        print("\n[2/5] Skipping benchmarks (compare=False)")

    # Step 3: Apply indexes
    if apply:
        print("\n[3/5] Applying index recommendations...")
        for rec in recommendations:
            idx_name = _extract_index_name(rec.create_statement)

            # Safety check before applying
            try:
                check_safety(rec.table, idx_name, ignore_cooldown=True)
            except SafetyViolation as e:
                print(f"  [SKIP] {idx_name}: {e}")
                record_decision("safety_skip", f"{idx_name}: {e}")
                continue

            print(f"  Applying: {rec.create_statement}")
            result = apply_index(rec)
            report.applied_indexes.append(result)

            if result.applied:
                print(f"    [OK] Applied in {result.duration_ms:.0f} ms")
                record_index_applied(
                    result.index_name, result.table, result.columns,
                    result.create_sql, rec.reason
                )
                record_decision("applied", f"Applied [{result.index_name}] on [{result.table}]")
            else:
                print(f"    [FAIL] {result.error}")
                report.errors.append(f"Failed to apply {result.index_name}: {result.error}")
    else:
        print("\n[3/5] Skipping index application (apply=False)")

    # Step 4: After benchmarks
    if compare and apply:
        print(f"\n[4/5] Running AFTER benchmarks ({benchmark_runs} runs each)...")
        queries = get_slow_queries_for_benchmark()
        report.after_benchmarks = run_benchmark_suite(queries, benchmark_runs)
        print(format_benchmark_results(report.after_benchmarks))

        # Record benchmark history
        for b in report.after_benchmarks:
            record_benchmark(b.name, b.mean_ms, b.median_ms)

        # Compare
        report.comparisons = compare_results(
            report.before_benchmarks,
            report.after_benchmarks,
            threshold_pct=degradation_threshold,
        )
        print(format_comparison(report.comparisons))
    else:
        print("\n[4/5] Skipping after benchmarks")

    # Step 5: Rollback degraded indexes
    if rollback and compare and apply:
        print("\n[5/5] Checking for degraded indexes...")
        degraded = [c for c in report.comparisons if c.verdict == "degraded"]

        if degraded:
            print(f"  Found {len(degraded)} degraded queries:")
            for d in degraded:
                print(f"    - {d.name}: {d.improvement_pct:.2f}% slower")

            applied_names = [r.index_name for r in report.applied_indexes if r.applied]

            if applied_names:
                print(f"\n  Rolling back {len(applied_names)} indexes...")
                for idx_name in applied_names:
                    print(f"    Dropping: {idx_name}")
                    if drop_index(idx_name):
                        report.rolled_back.append(idx_name)
                        record_index_rolled_back(idx_name)
                        record_decision("rollback", f"Rolled back degraded index [{idx_name}]")
                        print(f"      [OK] Dropped")
                    else:
                        report.errors.append(f"Failed to drop {idx_name}")

                # Re-run benchmarks after rollback
                print(f"\n  Re-running benchmarks after rollback...")
                queries = get_slow_queries_for_benchmark()
                after_rollback = run_benchmark_suite(queries, benchmark_runs)
                rollback_comparison = compare_results(
                    report.before_benchmarks,
                    after_rollback,
                    threshold_pct=5.0,
                )
                print(format_comparison(rollback_comparison))
            else:
                print("  No indexes to rollback.")
        else:
            print("  No degradation detected. All indexes kept.")
    else:
        print("\n[5/5] Skipping rollback check")

    return report


def format_report(report: RemediationReport) -> str:
    """Format the full remediation report."""
    lines = []
    lines.append("=" * 80)
    lines.append("AUTO-REMEDIATION REPORT")
    lines.append("=" * 80)

    if report.dry_run:
        lines.append("\nMode: DRY RUN (no changes applied)")
    else:
        lines.append("\nMode: LIVE")

    # Applied indexes
    if report.applied_indexes:
        lines.append(f"\nApplied Indexes ({len(report.applied_indexes)}):")
        lines.append("-" * 60)
        for r in report.applied_indexes:
            status = "OK" if r.applied else "FAIL"
            lines.append(f"  [{status}] {r.index_name} ({r.duration_ms:.0f} ms)")
            if r.error:
                lines.append(f"        Error: {r.error}")

    # Rolled back
    if report.rolled_back:
        lines.append(f"\nRolled Back Indexes ({len(report.rolled_back)}):")
        lines.append("-" * 60)
        for name in report.rolled_back:
            lines.append(f"  - {name}")

    # Errors
    if report.errors:
        lines.append(f"\nErrors ({len(report.errors)}):")
        lines.append("-" * 60)
        for err in report.errors:
            lines.append(f"  - {err}")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


def main():
    """CLI entry point for auto-remediation."""
    import argparse

    parser = argparse.ArgumentParser(description="VortexDBA Auto-Remediation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only report, do not apply changes")
    parser.add_argument("--no-compare", action="store_true",
                        help="Skip before/after benchmarks")
    parser.add_argument("--no-rollback", action="store_true",
                        help="Do not rollback degraded indexes")
    parser.add_argument("--runs", type=int, default=3,
                        help="Number of benchmark runs (default: 3)")
    parser.add_argument("--threshold", type=float, default=10.0,
                        help="Degradation threshold %% (default: 10.0)")

    args = parser.parse_args()

    print("=" * 80)
    print("VortexDBA - Auto-Remediation Engine")
    print("=" * 80)

    report = run_remediation(
        dry_run=args.dry_run,
        apply=not args.dry_run,
        compare=not args.no_compare,
        rollback=not args.no_rollback,
        benchmark_runs=args.runs,
        degradation_threshold=args.threshold,
    )

    print(format_report(report))


if __name__ == "__main__":
    main()
