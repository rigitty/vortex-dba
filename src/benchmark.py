"""Benchmark module for VortexDBA.

Runs queries multiple times and collects statistical performance
data (mean, min, max, median) for reliable before/after comparison.
"""

import statistics
import time
from dataclasses import dataclass

from db_connection import get_connection


@dataclass
class BenchmarkResult:
    """Statistical result for a single query benchmark."""
    name: str
    query: str
    runs: int
    durations_ms: list[float]
    mean_ms: float
    median_ms: float
    min_ms: float
    max_ms: float
    stddev_ms: float
    rows_returned: int


@dataclass
class ComparisonResult:
    """Before/after comparison for a single query."""
    name: str
    before_mean_ms: float
    after_mean_ms: float
    improvement_pct: float
    verdict: str  # "improved", "degraded", "neutral"


DEFAULT_RUNS = 3


def run_benchmark(name: str, query: str, params: tuple | None = None,
                  runs: int = DEFAULT_RUNS) -> BenchmarkResult:
    """Run a query multiple times and collect timing statistics."""
    durations = []
    row_count = 0
    bench_sql = f"-- VORTEX_INTERNAL_BENCHMARK\n{query}" if not query.strip().startswith("--") else query

    for _ in range(runs):
        conn = get_connection(autocommit=True)
        try:
            with conn.cursor(as_dict=True) as cur:
                start = time.perf_counter()
                cur.execute(bench_sql, params)
                rows = cur.fetchall()
                elapsed_ms = (time.perf_counter() - start) * 1000

                durations.append(round(elapsed_ms, 3))
                row_count = len(rows)
        finally:
            conn.close()


    return BenchmarkResult(
        name=name,
        query=query.strip(),
        runs=runs,
        durations_ms=durations,
        mean_ms=round(statistics.mean(durations), 3),
        median_ms=round(statistics.median(durations), 3),
        min_ms=round(min(durations), 3),
        max_ms=round(max(durations), 3),
        stddev_ms=round(statistics.stdev(durations), 3) if len(durations) > 1 else 0.0,
        rows_returned=row_count,
    )


def run_benchmark_suite(queries: list[dict], runs: int = DEFAULT_RUNS) -> list[BenchmarkResult]:
    """Run benchmarks for a list of queries."""
    results = []
    for q in queries:
        print(f"  Benchmarking: {q['name']} ({runs} runs)...")
        result = run_benchmark(
            name=q["name"],
            query=q["query"],
            params=q.get("params"),
            runs=runs,
        )
        results.append(result)
        print(f"    Mean: {result.mean_ms:.2f} ms | Median: {result.median_ms:.2f} ms")
    return results


def compare_results(before: list[BenchmarkResult], after: list[BenchmarkResult],
                    threshold_pct: float = 5.0) -> list[ComparisonResult]:
    """Compare before/after benchmark results.

    Args:
        threshold_pct: Minimum % change to consider significant.
    """
    before_map = {r.name: r for r in before}
    after_map = {r.name: r for r in after}

    comparisons = []
    for name in before_map:
        if name not in after_map:
            continue

        b = before_map[name]
        a = after_map[name]

        if b.mean_ms == 0:
            improvement_pct = 0.0
        else:
            improvement_pct = ((b.mean_ms - a.mean_ms) / b.mean_ms) * 100

        diff_ms = a.mean_ms - b.mean_ms
        if improvement_pct > threshold_pct:
            verdict = "improved"
        elif improvement_pct < -threshold_pct and diff_ms > 25.0:
            verdict = "degraded"
        else:
            verdict = "neutral"

        comparisons.append(ComparisonResult(
            name=name,
            before_mean_ms=b.mean_ms,
            after_mean_ms=a.mean_ms,
            improvement_pct=round(improvement_pct, 2),
            verdict=verdict,
        ))

    return comparisons


def format_benchmark_results(results: list[BenchmarkResult]) -> str:
    """Format benchmark results into a readable table."""
    if not results:
        return "No benchmark results."

    lines = []
    lines.append("=" * 90)
    lines.append("BENCHMARK RESULTS")
    lines.append("=" * 90)
    lines.append(f"{'Query':<30} {'Mean(ms)':>10} {'Median(ms)':>12} {'Min(ms)':>10} {'Max(ms)':>10} {'StdDev':>10}")
    lines.append("-" * 90)

    for r in results:
        lines.append(
            f"{r.name:<30} {r.mean_ms:>10.2f} {r.median_ms:>12.2f} "
            f"{r.min_ms:>10.2f} {r.max_ms:>10.2f} {r.stddev_ms:>10.2f}"
        )

    lines.append("=" * 90)
    return "\n".join(lines)


def format_comparison(comparisons: list[ComparisonResult]) -> str:
    """Format comparison results into a readable table."""
    if not comparisons:
        return "No comparisons to display."

    lines = []
    lines.append("=" * 80)
    lines.append("BEFORE / AFTER COMPARISON")
    lines.append("=" * 80)
    lines.append(f"{'Query':<30} {'Before(ms)':>12} {'After(ms)':>12} {'Change':>10} {'Verdict':>12}")
    lines.append("-" * 80)

    improved = 0
    degraded = 0
    neutral = 0

    for c in comparisons:
        symbol = "+" if c.improvement_pct > 0 else ""
        change_str = f"{symbol}{c.improvement_pct:.2f}%"
        lines.append(
            f"{c.name:<30} {c.before_mean_ms:>12.2f} {c.after_mean_ms:>12.2f} "
            f"{change_str:>10} {c.verdict:>12}"
        )

        if c.verdict == "improved":
            improved += 1
        elif c.verdict == "degraded":
            degraded += 1
        else:
            neutral += 1

    lines.append("-" * 80)
    lines.append(f"Summary: {improved} improved, {degraded} degraded, {neutral} neutral")
    lines.append("=" * 80)

    return "\n".join(lines)
