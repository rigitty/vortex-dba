"""Tests for config module."""

import os
import pytest
from unittest.mock import patch

from config import load_config, AppConfig


def test_load_config_defaults():
    config = load_config()
    assert isinstance(config, AppConfig)
    assert config.database.port == 1433
    assert config.remediation.max_indexes_per_table > 0


def test_env_overrides():
    with patch.dict(os.environ, {"VORTEX_DB_PORT": "1434", "VORTEX_DB_HOST": "mssql.local"}):
        config = load_config()
        assert config.database.port == 1434
        assert config.database.host == "mssql.local"
