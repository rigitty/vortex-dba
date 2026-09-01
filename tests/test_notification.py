"""Tests for notification module."""

import logging
import pytest
from unittest.mock import patch

from notification import setup_logging, notify, logger


def test_setup_logging_no_duplicate_handlers():
    setup_logging()
    initial_count = len(logger.handlers)
    setup_logging()
    assert len(logger.handlers) == initial_count


def test_notify_filtering():
    with patch("notification.logger") as mock_logger:
        # Event type not in alert_on should not log or send webhook
        notify("untracked_event", "Some message")
        mock_logger.info.assert_not_called()
        mock_logger.warning.assert_not_called()
