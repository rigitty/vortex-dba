"""Notification system for VortexDBA.

Sends alerts via webhook, log file, and console for
critical events like rollbacks, new indexes, and anomalies.
"""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

import requests

from config import get_config

# Setup logger
logger = logging.getLogger("vortexdba")


def setup_logging() -> None:
    """Configure logging based on config."""
    config = get_config()
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "vortexdba.log"

    handler = logging.handlers.RotatingFileHandler(
        str(log_file),
        maxBytes=config.logging.max_size_mb * 1024 * 1024,
        backupCount=5,
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))

    logger.setLevel(getattr(logging, config.logging.level, logging.INFO))
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.addHandler(console_handler)


def notify(event_type: str, message: str, details: dict | None = None) -> None:
    """Send a notification through all configured channels.

    Args:
        event_type: Type of event (critical_issue, rollback, new_index_applied, etc.)
        message: Human-readable message
        details: Optional dict with additional context
    """
    config = get_config()

    # Check if this event type should trigger alerts
    if event_type not in config.notification.alert_on:
        return

    timestamp = datetime.now().isoformat()

    # Console/log notification
    log_message = f"[{event_type.upper()}] {message}"
    if event_type in ("critical_issue", "rollback"):
        logger.warning(log_message)
    else:
        logger.info(log_message)

    # Webhook notification
    if config.notification.enabled and config.notification.webhook_url:
        _send_webhook(config.notification.webhook_url, event_type, message, details, timestamp)


def _send_webhook(url: str, event_type: str, message: str,
                  details: dict | None, timestamp: str) -> None:
    """Send notification via webhook."""
    payload = {
        "event_type": event_type,
        "message": message,
        "timestamp": timestamp,
        "source": "vortexdba",
        "details": details or {},
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Webhook notification failed: {e}")


def notify_index_applied(index_name: str, table: str, duration_ms: float) -> None:
    """Notify that a new index was applied."""
    notify(
        "new_index_applied",
        f"Index {index_name} applied to {table} in {duration_ms:.0f}ms",
        {"index_name": index_name, "table": table, "duration_ms": duration_ms},
    )


def notify_index_rolled_back(index_name: str, reason: str) -> None:
    """Notify that an index was rolled back."""
    notify(
        "rollback",
        f"Index {index_name} rolled back: {reason}",
        {"index_name": index_name, "reason": reason},
    )


def notify_critical_issue(issue_type: str, description: str) -> None:
    """Notify about a critical performance issue."""
    notify(
        "critical_issue",
        f"Critical issue detected: {issue_type} - {description}",
        {"issue_type": issue_type, "description": description},
    )


def notify_analysis_complete(improved: int, degraded: int, neutral: int) -> None:
    """Notify that an analysis cycle completed."""
    notify(
        "analysis_complete",
        f"Analysis complete: {improved} improved, {degraded} degraded, {neutral} neutral",
        {"improved": improved, "degraded": degraded, "neutral": neutral},
    )


def notify_agent_started() -> None:
    """Notify that the self-healing agent started."""
    notify(
        "agent_started",
        "VortexDBA Self-Healing Agent started",
    )


def notify_agent_stopped() -> None:
    """Notify that the self-healing agent stopped."""
    notify(
        "agent_stopped",
        "VortexDBA Self-Healing Agent stopped",
    )
