"""Tests for state_store module."""

import sqlite3
import pytest
from unittest.mock import patch

import state_store


@pytest.fixture
def temp_state_db(tmp_path):
    """Fixture providing a temporary SQLite database for state_store."""
    test_db = tmp_path / "test_vortex_state.db"
    with patch.object(state_store, "DB_PATH", test_db):
        state_store.init_db()
        yield test_db


def test_init_db(temp_state_db):
    """Test that init_db creates all expected tables."""
    conn = sqlite3.connect(str(temp_state_db))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    conn.close()

    assert "applied_indexes" in tables
    assert "benchmark_history" in tables
    assert "agent_decisions" in tables


def test_record_and_get_applied_index(temp_state_db):
    """Test recording an applied index and fetching active indexes."""
    with patch.object(state_store, "DB_PATH", temp_state_db):
        state_store.record_index_applied(
            index_name="idx_customers_city",
            table_name="customers",
            columns=["city"],
            create_sql="CREATE INDEX idx_customers_city ON customers(city);",
            reason="Seq scan elimination",
        )

        assert state_store.was_index_applied("idx_customers_city") is True
        assert state_store.was_index_applied("idx_non_existent") is False
        assert state_store.get_index_count_for_table("customers") == 1
        assert state_store.get_total_active_index_count() == 1

        active = state_store.get_active_indexes()
        assert len(active) == 1
        assert active[0].index_name == "idx_customers_city"
        assert active[0].table_name == "customers"
        assert active[0].columns == ["city"]
        assert active[0].rolled_back_at is None


def test_record_index_rollback(temp_state_db):
    """Test rolling back an applied index."""
    with patch.object(state_store, "DB_PATH", temp_state_db):
        state_store.record_index_applied(
            index_name="idx_orders_status",
            table_name="orders",
            columns=["status"],
            create_sql="CREATE INDEX idx_orders_status ON orders(status);",
            reason="Filter improvement",
        )

        assert state_store.get_index_count_for_table("orders") == 1

        state_store.record_index_rolled_back("idx_orders_status")

        assert state_store.was_index_applied("idx_orders_status") is False
        assert state_store.get_index_count_for_table("orders") == 0
        assert state_store.get_total_active_index_count() == 0
        assert len(state_store.get_active_indexes()) == 0


def test_record_benchmark_and_decisions(temp_state_db):
    """Test benchmark history and agent decisions logging."""
    with patch.object(state_store, "DB_PATH", temp_state_db):
        state_store.record_benchmark("query_1", 12.5, 11.8, "idx_customers_city")
        state_store.record_decision("cycle_complete", "Improved 2 queries")

        history = state_store.get_benchmark_history("query_1")
        assert len(history) == 1
        assert history[0].query_name == "query_1"
        assert history[0].mean_ms == 12.5
        assert history[0].median_ms == 11.8

        decisions = state_store.get_recent_decisions()
        assert len(decisions) == 1
        assert decisions[0].decision_type == "cycle_complete"
        assert "Improved" in decisions[0].details
