"""Self-Healing Agent for VortexDBA.

Continuous monitoring and auto-remediation loop:
1. Discover slow queries from pg_stat_statements
2. Analyze execution plans
3. Generate index recommendations
4. Validate against safety policies
5. Benchmark before/after
6. Apply or rollback based on results
7. Record decisions and notify
"""

import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

from config import get_config, load_config
from db_connection import execute_query
from query_discovery import discover_and_analyze, DiscoveredQuery
from query_analyzer import analyze_plan, Issue, Severity
from index_advisor import generate_recommendations, IndexRecommendation
from benchmark import run_benchmark, compare_results, BenchmarkResult, ComparisonResult
from safety_guard import check_safety, SafetyViolation, get_safety_report
from state_store import (
    init_db, record_index_applied, record_index_rolled_back,
    record_benchmark, record_decision, get_active_indexes,
    get_index_snapshot,
)
from notification import (
    setup_logging, notify_index_applied, notify_index_rolled_back,
    notify_critical_issue, notify_analysis_complete,
    notify_agent_started, notify_agent_stopped,
)
from slow_queries import SLOW_QUERIES


@dataclass
class AgentCycleResult:
    """Result of a single agent cycle."""
    cycle_number: int
    queries_discovered: int
    issues_found: int
    recommendations_made: int
    indexes_applied: int
    indexes_rolled_back: int
    improved: int
    degraded: int
    neutral: int
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


# Graceful shutdown flag
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    _shutdown_requested = True
    print("\nShutdown requested. Finishing current cycle...")


class SelfHealingAgent:
    """The main self-healing agent."""

    def __init__(self, dry_run: bool = False):
        self.config = get_config()
        self.dry_run = dry_run or self.config.remediation.dry_run_default
        self.cycle_count = 0
        self.running = True

    def _extract_index_name(self, create_statement: str) -> str:
        """Extract index name from CREATE INDEX statement.

        Handles both:
        - CREATE INDEX idx_name ON ...
        - CREATE INDEX CONCURRENTLY idx_name ON ...
        """
        parts = create_statement.split()
        # Find the index name (after INDEX, skipping CONCURRENTLY if present)
        for i, part in enumerate(parts):
            if part.upper() == "INDEX" and i + 1 < len(parts):
                next_part = parts[i + 1]
                if next_part.upper() == "CONCURRENTLY":
                    return parts[i + 2].split("(")[0]
                else:
                    return next_part.split("(")[0]
        return "unknown_index"

    def _get_static_queries(self) -> list[DiscoveredQuery]:
        """Get static slow queries from slow_queries module for testing."""
        from slow_queries import run_all_queries, QueryResult

        queries = []
        results = run_all_queries()

        for r in results:
            queries.append(DiscoveredQuery(
                queryid=hash(r.name) % 1000000,
                query=r.query,
                normalized_query=r.query,
                calls=1,
                mean_exec_time=r.duration_ms,
                total_exec_time=r.duration_ms,
                rows=r.row_count,
                plan=r.plan,
            ))

        return queries

    def run_once(self) -> AgentCycleResult:
        """Run a single analysis and remediation cycle."""
        self.cycle_count += 1
        start_time = time.time()

        result = AgentCycleResult(
            cycle_number=self.cycle_count,
            queries_discovered=0,
            issues_found=0,
            recommendations_made=0,
            indexes_applied=0,
            indexes_rolled_back=0,
            improved=0,
            degraded=0,
            neutral=0,
        )

        try:
            # Step 1: Discover slow queries (dynamic + static)
            print(f"\n[Cycle {self.cycle_count}] [1/6] Discovering slow queries...")

            # Try dynamic discovery from pg_stat_statements
            discovered = discover_and_analyze()

            # Also use static slow queries for testing
            static_queries = self._get_static_queries()
            discovered.extend(static_queries)

            result.queries_discovered = len(discovered)

            if not discovered:
                print("  No slow queries found.")
                result.duration_seconds = time.time() - start_time
                return result

            print(f"  Found {len(discovered)} slow queries.")

            # Step 2: Analyze execution plans
            print(f"[Cycle {self.cycle_count}] [2/6] Analyzing execution plans...")
            all_issues = []
            for dq in discovered:
                if dq.plan:
                    issues = analyze_plan(dq.plan)
                    all_issues.extend(issues)

            result.issues_found = len(all_issues)
            critical = [i for i in all_issues if i.severity == Severity.CRITICAL]
            if critical:
                print(f"  Found {len(all_issues)} issues ({len(critical)} critical)")
                for issue in critical:
                    notify_critical_issue(issue.pattern, issue.description)
            else:
                print(f"  Found {len(all_issues)} issues (no critical)")

            # Step 3: Generate recommendations
            print(f"[Cycle {self.cycle_count}] [3/6] Generating recommendations...")
            recommendations = generate_recommendations(all_issues)
            result.recommendations_made = len(recommendations)

            if not recommendations:
                print("  No index recommendations.")
                result.duration_seconds = time.time() - start_time
                return result

            print(f"  Generated {len(recommendations)} recommendations.")

            # Step 4: Validate against safety policies
            print(f"[Cycle {self.cycle_count}] [4/6] Validating safety policies...")
            safe_recommendations = []
            for rec in recommendations:
                idx_name = self._extract_index_name(rec.create_statement)
                try:
                    check_safety(rec.table, idx_name)
                    safe_recommendations.append(rec)
                    print(f"  [OK] {idx_name}")
                except SafetyViolation as e:
                    print(f"  [SKIP] {idx_name}: {e}")
                    record_decision("safety_skip", f"{idx_name}: {e}")

            if not safe_recommendations:
                print("  No safe recommendations to apply.")
                result.duration_seconds = time.time() - start_time
                return result

            # Step 5: Benchmark and apply
            if self.dry_run:
                print(f"[Cycle {self.cycle_count}] [5/6] DRY RUN - would apply:")
                for rec in safe_recommendations:
                    print(f"  - {rec.create_statement}")
                result.duration_seconds = time.time() - start_time
                return result

            print(f"[Cycle {self.cycle_count}] [5/6] Benchmarking and applying...")
            before_results, after_results, comparisons = self._benchmark_and_apply(
                safe_recommendations, discovered
            )

            # Count results
            for comp in comparisons:
                if comp.verdict == "improved":
                    result.improved += 1
                elif comp.verdict == "degraded":
                    result.degraded += 1
                else:
                    result.neutral += 1

            # Step 6: Rollback if needed
            print(f"[Cycle {self.cycle_count}] [6/6] Checking for degradation...")
            if result.degraded > 0 and self.config.remediation.rollback_policy == "per_index":
                rolled_back = self._rollback_degraded(safe_recommendations, comparisons)
                result.indexes_rolled_back = rolled_back
            else:
                result.indexes_applied = len(safe_recommendations)
                print(f"  All {len(safe_recommendations)} indexes kept.")

            notify_analysis_complete(result.improved, result.degraded, result.neutral)

        except Exception as e:
            result.errors.append(str(e))
            print(f"  [ERROR] {e}")

        result.duration_seconds = time.time() - start_time
        record_decision(
            "cycle_complete",
            f"Cycle {self.cycle_count}: {result.improved} improved, "
            f"{result.degraded} degraded, {result.neutral} neutral"
        )

        return result

    def _benchmark_and_apply(
        self,
        recommendations: list[IndexRecommendation],
        discovered: list[DiscoveredQuery],
    ) -> tuple[list[BenchmarkResult], list[BenchmarkResult], list[ComparisonResult]]:
        """Benchmark before, apply indexes, benchmark after."""
        runs = self.config.benchmark.runs

        # Build benchmark queries from discovered queries
        bench_queries = []
        for dq in discovered[:10]:  # Top 10 for benchmarking
            bench_queries.append({
                "name": f"query_{dq.queryid}",
                "query": dq.query,
                "params": None,
            })

        # Before benchmarks
        print(f"  Running BEFORE benchmarks ({runs} runs)...")
        before_results = []
        for bq in bench_queries:
            result = run_benchmark(bq["name"], bq["query"], bq.get("params"), runs)
            before_results.append(result)
            record_benchmark(result.name, result.mean_ms, result.median_ms, get_index_snapshot())

        # Apply indexes
        applied = []
        for rec in recommendations:
            idx_name = self._extract_index_name(rec.create_statement)
            print(f"  Applying: {rec.create_statement}")

            start = time.time()
            try:
                execute_query(rec.create_statement, fetch=False)
                duration_ms = (time.time() - start) * 1000

                record_index_applied(
                    idx_name, rec.table, rec.columns,
                    rec.create_statement, rec.reason
                )
                notify_index_applied(idx_name, rec.table, duration_ms)
                applied.append(rec)
                print(f"    [OK] Applied in {duration_ms:.0f}ms")
            except Exception as e:
                print(f"    [FAIL] {e}")

        # After benchmarks
        print(f"  Running AFTER benchmarks ({runs} runs)...")
        after_results = []
        for bq in bench_queries:
            result = run_benchmark(bq["name"], bq["query"], bq.get("params"), runs)
            after_results.append(result)
            record_benchmark(result.name, result.mean_ms, result.median_ms, get_index_snapshot())

        # Compare
        comparisons = compare_results(
            before_results, after_results,
            threshold_pct=self.config.benchmark.degradation_threshold_pct,
        )

        return before_results, after_results, comparisons

    def _rollback_degraded(
        self,
        recommendations: list[IndexRecommendation],
        comparisons: list[ComparisonResult],
    ) -> int:
        """Rollback indexes that caused degradation."""
        degraded_queries = [c for c in comparisons if c.verdict == "degraded"]
        if not degraded_queries:
            return 0

        print(f"  Degradation detected in {len(degraded_queries)} queries:")
        for dq in degraded_queries:
            print(f"    - {dq.name}: {dq.improvement_pct:.2f}% slower")

        # Rollback all applied indexes (conservative approach)
        rolled_back = 0
        for rec in recommendations:
            idx_name = rec.create_statement.split()[2].split("(")[0]
            print(f"  Rolling back: {idx_name}")

            try:
                execute_query(f"DROP INDEX IF EXISTS {idx_name}", fetch=False)
                record_index_rolled_back(idx_name)
                notify_index_rolled_back(idx_name, "Performance degradation detected")
                rolled_back += 1
                print(f"    [OK] Dropped")
            except Exception as e:
                print(f"    [FAIL] {e}")

        return rolled_back

    def run_daemon(self) -> None:
        """Run the agent in continuous daemon mode."""
        interval = self.config.scheduler.analysis_interval_minutes * 60

        print("=" * 60)
        print("VortexDBA Self-Healing Agent - Daemon Mode")
        print("=" * 60)
        print(f"Analysis interval: {self.config.scheduler.analysis_interval_minutes} minutes")
        print(f"Dry run: {self.dry_run}")
        print(f"Press Ctrl+C to stop")
        print("=" * 60)

        notify_agent_started()

        while self.running and not _shutdown_requested:
            try:
                result = self.run_once()
                self._print_cycle_summary(result)

                if not _shutdown_requested:
                    print(f"\nNext cycle in {interval} seconds...")
                    # Sleep in small increments to allow graceful shutdown
                    for _ in range(int(interval)):
                        if _shutdown_requested:
                            break
                        time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[ERROR] Cycle failed: {e}")
                time.sleep(60)  # Wait a minute before retrying

        notify_agent_stopped()
        print("\nAgent stopped.")

    def _print_cycle_summary(self, result: AgentCycleResult) -> None:
        """Print a summary of the cycle result."""
        print("\n" + "=" * 60)
        print(f"CYCLE {result.cycle_number} SUMMARY")
        print("=" * 60)
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"Queries discovered: {result.queries_discovered}")
        print(f"Issues found: {result.issues_found}")
        print(f"Recommendations: {result.recommendations_made}")
        print(f"Indexes applied: {result.indexes_applied}")
        print(f"Indexes rolled back: {result.indexes_rolled_back}")
        print(f"Improved: {result.improved} | Degraded: {result.degraded} | Neutral: {result.neutral}")
        if result.errors:
            print(f"Errors: {len(result.errors)}")
            for err in result.errors:
                print(f"  - {err}")
        print("=" * 60)


def main():
    """CLI entry point for the self-healing agent."""
    import argparse

    parser = argparse.ArgumentParser(description="VortexDBA Self-Healing Agent")
    parser.add_argument("--once", action="store_true",
                        help="Run a single analysis cycle")
    parser.add_argument("--daemon", action="store_true",
                        help="Run in continuous daemon mode")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only analyze, do not apply changes")
    parser.add_argument("--safety-report", action="store_true",
                        help="Print safety status report")

    args = parser.parse_args()

    # Setup
    setup_logging()
    init_db()

    # Register signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    agent = SelfHealingAgent(dry_run=args.dry_run)

    if args.safety_report:
        print(get_safety_report())
    elif args.daemon:
        agent.run_daemon()
    else:
        # Default: run once
        result = agent.run_once()
        agent._print_cycle_summary(result)


if __name__ == "__main__":
    main()
