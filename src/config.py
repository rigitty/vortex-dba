"""Centralized configuration management for VortexDBA.

Loads configuration from config.yaml with environment variable
overrides and provides typed access to all settings.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 1433
    dbname: str = "vortex_db"
    user: str = "sa"
    password: str = "VortexPassword123!"
    pool_min: int = 2
    pool_max: int = 10


@dataclass
class DetectionConfig:
    min_mean_exec_time_ms: float = 100
    min_total_exec_time_ms: float = 10000
    min_calls: int = 10
    seq_scan_row_threshold: int = 10000
    filter_removal_threshold: int = 10000
    buffer_hit_threshold: int = 100000
    top_queries_limit: int = 20


@dataclass
class RemediationConfig:
    enabled: bool = True
    dry_run_default: bool = True
    max_indexes_per_table: int = 5
    max_indexes_total: int = 20
    cooldown_minutes: int = 60
    rollback_policy: str = "per_index"


@dataclass
class BenchmarkConfig:
    runs: int = 3
    degradation_threshold_pct: float = 10.0
    improvement_threshold_pct: float = 5.0


@dataclass
class SchedulerConfig:
    analysis_interval_minutes: int = 30
    unused_index_check_hours: int = 24


@dataclass
class NotificationConfig:
    enabled: bool = False
    webhook_url: str = ""
    alert_on: list[str] = field(default_factory=lambda: ["critical_issue", "rollback", "new_index_applied"])


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/vortexdba.log"
    max_size_mb: int = 50


@dataclass
class AppConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    remediation: RemediationConfig = field(default_factory=RemediationConfig)
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _apply_env_overrides(config: dict) -> dict:
    """Apply environment variable overrides to config dict."""
    env_mapping = {
        "VORTEX_DB_HOST": ("database", "host"),
        "VORTEX_DB_PORT": ("database", "port"),
        "VORTEX_DB_NAME": ("database", "dbname"),
        "VORTEX_DB_USER": ("database", "user"),
        "VORTEX_DB_PASSWORD": ("database", "password"),
    }

    for env_var, (section, key) in env_mapping.items():
        value = os.environ.get(env_var)
        if value is not None:
            if section not in config:
                config[section] = {}
            # Type conversion for port
            if key == "port":
                value = int(value)
            config[section][key] = value

    return config


def _dict_to_dataclass(data: dict, cls):
    """Convert a dict to a dataclass instance."""
    field_names = {f.name for f in cls.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in field_names}
    return cls(**filtered)


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load configuration from YAML file with env var overrides."""
    path = Path(config_path) if config_path else CONFIG_PATH

    config_dict = {}
    if path.exists():
        with open(path, "r") as f:
            config_dict = yaml.safe_load(f) or {}

    # Apply environment variable overrides
    config_dict = _apply_env_overrides(config_dict)

    # Build config object
    return AppConfig(
        database=_dict_to_dataclass(config_dict.get("database", {}), DatabaseConfig),
        detection=_dict_to_dataclass(config_dict.get("detection", {}), DetectionConfig),
        remediation=_dict_to_dataclass(config_dict.get("remediation", {}), RemediationConfig),
        benchmark=_dict_to_dataclass(config_dict.get("benchmark", {}), BenchmarkConfig),
        scheduler=_dict_to_dataclass(config_dict.get("scheduler", {}), SchedulerConfig),
        notification=_dict_to_dataclass(config_dict.get("notification", {}), NotificationConfig),
        logging=_dict_to_dataclass(config_dict.get("logging", {}), LoggingConfig),
    )


# Global config singleton
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> AppConfig:
    """Reload configuration from file."""
    global _config
    _config = load_config()
    return _config
