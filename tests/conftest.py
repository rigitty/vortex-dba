"""Pytest configuration and shared fixtures for VortexDBA tests."""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def sample_plan_seq_scan():
    """Sample EXPLAIN ANALYZE output with a sequential scan."""
    return """
Seq Scan on customers  (cost=0.00..2949.00 rows=100000 width=70) (actual time=0.006..9.699 rows=100000 loops=1)
  Filter: ((city)::text = 'New York'::text)
  Rows Removed by Filter: 99900
  Buffers: shared hit=1699
Planning Time: 0.224 ms
Execution Time: 4.667 ms
"""


@pytest.fixture
def sample_plan_index_scan():
    """Sample EXPLAIN ANALYZE output with an index scan."""
    return """
Index Scan using idx_orders_customer_id on orders  (cost=0.42..7.63 rows=7 width=14) (actual time=0.016..0.016 rows=0 loops=1)
  Index Cond: (customer_id = 12345)
  Buffers: shared hit=4
Planning Time: 0.100 ms
Execution Time: 0.050 ms
"""


@pytest.fixture
def sample_plan_nested_loop():
    """Sample EXPLAIN ANALYZE output with a nested loop join."""
    return """
Nested Loop  (cost=0.42..3704.40 rows=32 width=55) (actual time=0.475..5.629 rows=28 loops=1)
  Buffers: shared hit=2049
  ->  Seq Scan on customers c  (cost=0.00..2949.00 rows=90 width=31) (actual time=0.233..5.082 rows=86 loops=1)
        Filter: ((city)::text = 'Lake Michael'::text)
        Rows Removed by Filter: 99914
        Buffers: shared hit=1699
  ->  Index Scan using idx_orders_customer_id on orders o  (cost=0.42..8.38 rows=1 width=32) (actual time=0.006..0.006 rows=0 loops=86)
        Index Cond: (customer_id = c.id)
        Filter: ((total_amount > '500'::numeric) AND ((status)::text = 'completed'::text) AND ((product_category)::text = 'Electronics'::text))
        Rows Removed by Filter: 5
        Buffers: shared hit=350
Planning Time: 0.564 ms
Execution Time: 5.649 ms
"""


@pytest.fixture
def sample_plan_external_sort():
    """Sample EXPLAIN ANALYZE output with external merge sort."""
    return """
Sort  (cost=74339.78..75479.75 rows=455988 width=38) (actual time=459.295..566.870 rows=457107 loops=1)
  Sort Key: c.city, c.country, c.id
  Sort Method: external merge  Disk: 22960kB
  Buffers: shared hit=9791, temp read=2870 written=2880
  ->  Hash Join  (cost=3986.32..19009.52 rows=455988 width=38) (actual time=19.211..117.278 rows=457107 loops=1)
        Hash Cond: (o.customer_id = c.id)
        Buffers: shared hit=9785
Planning Time: 0.454 ms
Execution Time: 650.302 ms
"""


@pytest.fixture
def sample_plan_correlated_subquery():
    """Sample EXPLAIN ANALYZE output with correlated subquery."""
    return """
Seq Scan on customers c  (cost=0.00..688668.52 rows=79890 width=63) (actual time=0.278..150.869 rows=79909 loops=1)
  Filter: ((status)::text = 'active'::text)
  Rows Removed by Filter: 20091
  Buffers: shared hit=326824
  SubPlan 2
    ->  Aggregate  (cost=8.57..8.58 rows=1 width=32) (actual time=0.002..0.002 rows=1 loops=79909)
          Buffers: shared hit=325125
          ->  Index Scan using idx_orders_customer_id on orders o2  (cost=0.42..8.55 rows=7 width=6) (actual time=0.001..0.001 rows=6 loops=79909)
                Index Cond: (customer_id = c.id)
                Buffers: shared hit=325125
Planning Time: 0.933 ms
Execution Time: 405.394 ms
"""


@pytest.fixture
def sample_issues():
    """Sample list of detected issues."""
    from query_analyzer import Issue, Severity

    return [
        Issue(
            severity=Severity.CRITICAL,
            pattern="seq_scan_large_table",
            description="Sequential scan on customers with 100,000 estimated rows",
            node_type="Seq Scan",
            table="customers",
            rows=100000,
            suggestion="CREATE INDEX idx_customers_city ON customers(city)",
            line_number=0,
        ),
        Issue(
            severity=Severity.WARNING,
            pattern="high_filter_removal",
            description="99,900 rows removed by filter on customers",
            node_type="Seq Scan",
            table="customers",
            rows=99900,
            suggestion="Consider adding index on customers(city) for filter condition",
            line_number=0,
        ),
    ]


@pytest.fixture
def sample_recommendations():
    """Sample list of index recommendations."""
    from index_advisor import IndexRecommendation

    return [
        IndexRecommendation(
            table="customers",
            columns=["city"],
            index_type="btree",
            reason="Sequential scan on customers",
            priority=1,
            estimated_impact="~50-100x faster",
            create_statement="CREATE INDEX CONCURRENTLY idx_customers_city ON customers (city);",
            concurrent=True,
        ),
    ]
