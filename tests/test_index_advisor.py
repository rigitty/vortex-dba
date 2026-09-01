"""Tests for index_advisor module."""

import pytest
from index_advisor import (
    generate_recommendations, extract_columns_from_filter,
    extract_columns_from_condition, is_index_redundant,
    generate_index_name, estimate_impact, estimate_impact_from_rows,
    IndexRecommendation,
)
from query_analyzer import Issue, Severity


class TestExtractColumns:
    """Test column extraction functions."""

    def test_extract_from_filter_simple(self):
        cols = extract_columns_from_filter("((city)::text = 'New York'::text)")
        assert "city" in cols

    def test_extract_from_filter_multiple(self):
        cols = extract_columns_from_filter("((status)::text = 'active'::text) AND ((city)::text = 'NY'::text)")
        assert "status" in cols
        assert "city" in cols

    def test_extract_from_condition(self):
        cols = extract_columns_from_condition("customer_id = c.id")
        assert "customer_id" in cols

    def test_extract_from_condition_with_prefix(self):
        cols = extract_columns_from_condition("o.customer_id = c.id")
        assert "customer_id" in cols


class TestIndexRedundancy:
    """Test index redundancy detection."""

    def test_not_redundant_new_index(self):
        assert not is_index_redundant("customers", ["city"])

    def test_redundant_existing_index(self):
        # idx_orders_customer_id exists
        assert is_index_redundant("orders", ["customer_id"])


class TestGenerateIndexName:
    """Test index name generation."""

    def test_single_column(self):
        assert generate_index_name("customers", ["city"]) == "idx_customers_city"

    def test_multiple_columns(self):
        name = generate_index_name("orders", ["status", "total_amount"])
        assert name == "idx_orders_status_total_amount"

    def test_max_three_columns(self):
        name = generate_index_name("orders", ["a", "b", "c", "d"])
        assert name == "idx_orders_a_b_c"


class TestEstimateImpact:
    """Test impact estimation."""

    def test_high_impact(self):
        assert "50-100x" in estimate_impact_from_rows(600000)

    def test_medium_impact(self):
        assert "10-50x" in estimate_impact_from_rows(200000)

    def test_low_impact(self):
        assert "5-10x" in estimate_impact_from_rows(50000)

    def test_minimal_impact(self):
        assert "2-5x" in estimate_impact_from_rows(5000)


class TestGenerateRecommendations:
    """Test recommendation generation."""

    def test_generates_recommendations(self, sample_issues):
        recs = generate_recommendations(sample_issues)
        assert len(recs) > 0
        assert all(isinstance(r, IndexRecommendation) for r in recs)
        for rec in recs:
            assert "CREATE NONCLUSTERED INDEX" in rec.create_statement or "INDEX" in rec.create_statement

    def test_skips_info_severity(self):
        issues = [
            Issue(
                severity=Severity.INFO,
                pattern="test",
                description="test",
                node_type="test",
                table="test",
                rows=100,
                suggestion="test",
            )
        ]
        recs = generate_recommendations(issues)
        assert len(recs) == 0

    def test_deduplicates(self):
        issues = [
            Issue(
                severity=Severity.CRITICAL,
                pattern="seq_scan_large_table",
                description="test",
                node_type="Seq Scan",
                table="customers",
                rows=100000,
                suggestion="CREATE INDEX idx_customers_city ON customers(city)",
            ),
            Issue(
                severity=Severity.WARNING,
                pattern="high_filter_removal",
                description="test",
                node_type="Seq Scan",
                table="customers",
                rows=50000,
                suggestion="Consider adding index on customers(city)",
            ),
        ]
        recs = generate_recommendations(issues)
        # Should deduplicate same table+column
        city_recs = [r for r in recs if "city" in r.columns]
        assert len(city_recs) == 1
