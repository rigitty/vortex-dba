"""VortexDBA Performance Analysis Pipeline.

Integrates slow query simulation, execution plan analysis,
index recommendations, and PostgreSQL statistics into a
unified analysis report.
"""

from slow_queries import run_all_queries, QueryResult
from query_analyzer import analyze_plan, format_issues
from index_advisor import generate_recommendations, format_recommendations, get_apply_sql
from pg_stats_reader import get_full_report


def analyze_query_results(results: list[QueryResult]) -> None:
    """Analyze each query result and generate recommendations."""
    all_issues = []

    print("\n" + "=" * 80)
    print("EXECUTION PLAN ANALYSIS")
    print("=" * 80)

    for result in results:
        print(f"\n--- {result.name} ---")
        print(f"Duration: {result.duration_ms:.2f} ms | Rows: {result.row_count}")

        issues = analyze_plan(result.plan)
        if issues:
            all_issues.extend(issues)
            for issue in issues:
                print(f"  [{issue.severity.value}] {issue.pattern}: {issue.description}")
                print(f"    → {issue.suggestion}")
        else:
            print("  No issues detected.")

    # Generate index recommendations
    recommendations = generate_recommendations(all_issues)
    print("\n" + format_recommendations(recommendations))

    # Generate SQL script
    if recommendations:
        print("\n" + "=" * 80)
        print("SQL SCRIPT TO APPLY RECOMMENDATIONS")
        print("=" * 80)
        print(get_apply_sql(recommendations))


def main():
    """Main entry point for the analysis pipeline."""
    print("=" * 80)
    print("VortexDBA - Performance Analysis Pipeline")
    print("=" * 80)

    # Step 1: Run slow queries
    print("\n[1/4] Running slow query simulation...")
    results = run_all_queries()

    # Step 2: Analyze execution plans
    print("\n[2/4] Analyzing execution plans...")
    analyze_query_results(results)

    # Step 3: Get PostgreSQL statistics
    print("\n[3/4] Reading PostgreSQL statistics...")
    stats_report = get_full_report()
    print("\n" + stats_report)

    # Step 4: Summary
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("Review the recommendations above and apply indexes as needed.")
    print("Monitor performance after applying changes.")


if __name__ == "__main__":
    main()
