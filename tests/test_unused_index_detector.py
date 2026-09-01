"""Tests for unused_index_detector module."""

import pytest
from unused_index_detector import (
    UnusedIndex,
    _format_size,
    format_unused_indexes,
    get_drop_all_sql,
)


def test_format_size():
    assert _format_size(500) == "500.0 B"
    assert _format_size(2048) == "2.0 KB"
    assert _format_size(10 * 1024 * 1024) == "10.0 MB"
    assert _format_size(5 * 1024 * 1024 * 1024) == "5.0 GB"


def test_format_unused_indexes():
    unused = [
        UnusedIndex(
            table_name="customers",
            index_name="idx_customers_status",
            index_size_bytes=1024 * 1024,
            index_size_pretty="1.0 MB",
            is_unique=False,
            is_primary=False,
            columns=["status"],
            drop_statement="DROP INDEX IF EXISTS idx_customers_status ON customers;",
        )
    ]
    report = format_unused_indexes(unused)
    assert "idx_customers_status" in report
    assert "customers" in report
    assert "1.0 MB" in report
    assert "Total reclaimable space: 1.0 MB" in report


def test_get_drop_all_sql():
    unused = [
        UnusedIndex(
            table_name="orders",
            index_name="idx_orders_status",
            index_size_bytes=2048,
            index_size_pretty="2.0 KB",
            is_unique=False,
            is_primary=False,
            columns=["status"],
            drop_statement="DROP INDEX IF EXISTS idx_orders_status ON orders;",
        )
    ]
    sql = get_drop_all_sql(unused)
    assert "DROP INDEX IF EXISTS idx_orders_status ON orders;" in sql
