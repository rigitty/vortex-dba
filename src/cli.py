"""Unified CLI entry point for VortexDBA.

Provides a single command-line interface for all VortexDBA operations:
- generate: Generate synthetic test data
- analyze: Run performance analysis
- remediate: Auto-remediation with benchmarks
- agent: Self-healing daemon
- safety-report: Show safety status
- unused-indexes: Detect unused indexes
- stats: Show PostgreSQL statistics
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def cmd_generate(args):
    """Generate synthetic test data."""
    from data_generator import main
    main()


def cmd_analyze(args):
    """Run performance analysis pipeline."""
    from analyzer_pipeline import main
    main()


def cmd_remediate(args):
    """Run auto-remediation."""
    from auto_remediator import run_remediation, format_report

    report = run_remediation(
        dry_run=args.dry_run,
        apply=not args.dry_run,
        compare=not args.no_compare,
        rollback=not args.no_rollback,
        benchmark_runs=args.runs,
        degradation_threshold=args.threshold,
    )
    print(format_report(report))


def cmd_agent(args):
    """Run self-healing agent."""
    from self_healing_agent import SelfHealingAgent, setup_logging, init_db

    setup_logging()
    init_db()

    agent = SelfHealingAgent(dry_run=args.dry_run)

    if args.daemon:
        agent.run_daemon()
    else:
        result = agent.run_once()
        agent._print_cycle_summary(result)


def cmd_safety_report(args):
    """Show safety status report."""
    from safety_guard import get_safety_report
    from state_store import init_db
    init_db()
    print(get_safety_report())


def cmd_unused_indexes(args):
    """Detect and report unused indexes."""
    from unused_index_detector import (
        get_unused_indexes, format_unused_indexes,
        get_index_usage_stats, format_index_usage_stats,
        get_drop_all_sql,
    )

    if args.stats:
        stats = get_index_usage_stats()
        print(format_index_usage_stats(stats))
    else:
        unused = get_unused_indexes()
        print(format_unused_indexes(unused))

        if args.sql:
            print("\n" + get_drop_all_sql(unused))


def cmd_stats(args):
    """Show PostgreSQL statistics."""
    from pg_stats_reader import get_full_report
    print(get_full_report())


def main():
    parser = argparse.ArgumentParser(
        prog="vortexdba",
        description="VortexDBA - Autonomous Database Performance Optimizer",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # generate
    p_generate = subparsers.add_parser("generate", help="Generate synthetic test data")
    p_generate.set_defaults(func=cmd_generate)

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Run performance analysis")
    p_analyze.set_defaults(func=cmd_analyze)

    # remediate
    p_remediate = subparsers.add_parser("remediate", help="Auto-remediation with benchmarks")
    p_remediate.add_argument("--dry-run", action="store_true", help="Only report, do not apply")
    p_remediate.add_argument("--no-compare", action="store_true", help="Skip benchmarks")
    p_remediate.add_argument("--no-rollback", action="store_true", help="Do not rollback degraded")
    p_remediate.add_argument("--runs", type=int, default=3, help="Benchmark runs (default: 3)")
    p_remediate.add_argument("--threshold", type=float, default=10.0, help="Degradation threshold %%")
    p_remediate.set_defaults(func=cmd_remediate)

    # agent
    p_agent = subparsers.add_parser("agent", help="Self-healing agent")
    p_agent.add_argument("--once", action="store_true", help="Run a single analysis cycle (default)")
    p_agent.add_argument("--daemon", action="store_true", help="Run in continuous daemon mode")
    p_agent.add_argument("--dry-run", action="store_true", help="Only analyze, do not apply")
    p_agent.set_defaults(func=cmd_agent)

    # safety-report
    p_safety = subparsers.add_parser("safety-report", help="Show safety status")
    p_safety.set_defaults(func=cmd_safety_report)

    # unused-indexes
    p_unused = subparsers.add_parser("unused-indexes", help="Detect unused indexes")
    p_unused.add_argument("--stats", action="store_true", help="Show all index usage stats")
    p_unused.add_argument("--sql", action="store_true", help="Generate DROP SQL script")
    p_unused.set_defaults(func=cmd_unused_indexes)

    # stats
    p_stats = subparsers.add_parser("stats", help="Show PostgreSQL statistics")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
