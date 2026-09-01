"""Tests for safety_guard module."""

import pytest
from safety_guard import validate_index_name


class TestValidateIndexName:
    """Test index name validation."""

    def test_valid_name(self):
        assert validate_index_name("idx_customers_city") is True

    def test_valid_name_with_numbers(self):
        assert validate_index_name("idx_orders_2024") is True

    def test_invalid_no_prefix(self):
        assert validate_index_name("customers_city") is False

    def test_invalid_empty(self):
        assert validate_index_name("") is False

    def test_invalid_too_long(self):
        long_name = "idx_" + "a" * 60
        assert validate_index_name(long_name) is False

    def test_invalid_characters(self):
        assert validate_index_name("idx_customers-city") is False

    def test_valid_underscore(self):
        assert validate_index_name("idx_customers_created_at_status") is True
