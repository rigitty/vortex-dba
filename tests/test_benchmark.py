"""Tests for benchmark module."""

import pytest
from benchmark import (
    compare_results,
    format_benchmark_results,
    format_comparison,
    BenchmarkResult,
    ComparisonResult,
)


def test_compare_results_improved():
    before = [
        BenchmarkResult(
            name="query_1",
            query="SELECT 1",
            runs=3,
            durations_ms=[100.0, 100.0, 100.0],
            mean_ms=100.0,
            median_ms=100.0,
            min_ms=100.0,
            max_ms=100.0,
            stddev_ms=0.0,
            rows_returned=10,
        )
    ]
    after = [
        BenchmarkResult(
            name="query_1",
            query="SELECT 1",
            runs=3,
            durations_ms=[20.0, 20.0, 20.0],
            mean_ms=20.0,
            median_ms=20.0,
            min_ms=20.0,
            max_ms=20.0,
            stddev_ms=0.0,
            rows_returned=10,
        )
    ]

    comparisons = compare_results(before, after, threshold_pct=10.0)
    assert len(comparisons) == 1
    assert comparisons[0].name == "query_1"
    assert comparisons[0].verdict == "improved"
    assert comparisons[0].improvement_pct == 80.0


def test_compare_results_degraded():
    before = [
        BenchmarkResult(
            name="query_2",
            query="SELECT 1",
            runs=3,
            durations_ms=[50.0, 50.0, 50.0],
            mean_ms=50.0,
            median_ms=50.0,
            min_ms=50.0,
            max_ms=50.0,
            stddev_ms=0.0,
            rows_returned=5,
        )
    ]
    after = [
        BenchmarkResult(
            name="query_2",
            query="SELECT 1",
            runs=3,
            durations_ms=[80.0, 80.0, 80.0],
            mean_ms=80.0,
            median_ms=80.0,
            min_ms=80.0,
            max_ms=80.0,
            stddev_ms=0.0,
            rows_returned=5,
        )
    ]

    comparisons = compare_results(before, after, threshold_pct=10.0)
    assert len(comparisons) == 1
    assert comparisons[0].name == "query_2"
    assert comparisons[0].verdict == "degraded"
    assert comparisons[0].improvement_pct == -60.0


def test_compare_results_neutral():
    before = [
        BenchmarkResult(
            name="query_3",
            query="SELECT 1",
            runs=3,
            durations_ms=[50.0, 50.0, 50.0],
            mean_ms=50.0,
            median_ms=50.0,
            min_ms=50.0,
            max_ms=50.0,
            stddev_ms=0.0,
            rows_returned=5,
        )
    ]
    after = [
        BenchmarkResult(
            name="query_3",
            query="SELECT 1",
            runs=3,
            durations_ms=[49.0, 49.0, 49.0],
            mean_ms=49.0,
            median_ms=49.0,
            min_ms=49.0,
            max_ms=49.0,
            stddev_ms=0.0,
            rows_returned=5,
        )
    ]

    comparisons = compare_results(before, after, threshold_pct=10.0)
    assert len(comparisons) == 1
    assert comparisons[0].verdict == "neutral"


def test_format_comparison():
    comparisons = [
        ComparisonResult(
            name="query_1",
            before_mean_ms=100.0,
            after_mean_ms=20.0,
            improvement_pct=80.0,
            verdict="improved",
        )
    ]
    formatted = format_comparison(comparisons)
    assert "query_1" in formatted
    assert "improved" in formatted
    assert "+80.00%" in formatted
