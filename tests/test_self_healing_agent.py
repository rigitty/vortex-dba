"""Tests for self_healing_agent module."""

import pytest
from self_healing_agent import SelfHealingAgent


def test_extract_index_name_standard():
    agent = SelfHealingAgent(dry_run=True)
    sql = "CREATE INDEX idx_customers_city ON customers(city);"
    assert agent._extract_index_name(sql) == "idx_customers_city"


def test_extract_index_name_nonclustered():
    agent = SelfHealingAgent(dry_run=True)
    sql = "CREATE NONCLUSTERED INDEX idx_customers_city ON customers (city);"
    assert agent._extract_index_name(sql) == "idx_customers_city"


def test_extract_index_name_concurrently():
    agent = SelfHealingAgent(dry_run=True)
    sql = "CREATE INDEX CONCURRENTLY idx_customers_city ON customers (city);"
    assert agent._extract_index_name(sql) == "idx_customers_city"


def test_extract_index_name_composite():
    agent = SelfHealingAgent(dry_run=True)
    sql = "CREATE NONCLUSTERED INDEX idx_orders_status_total ON orders (status, total_amount);"
    assert agent._extract_index_name(sql) == "idx_orders_status_total"


def test_agent_dry_run_cycle_summary():
    agent = SelfHealingAgent(dry_run=True)
    assert agent.dry_run is True
