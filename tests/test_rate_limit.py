import time
from unittest.mock import patch

from app.rate_limit import (
    check_rate_limit,
    rate_limit_message,
    RATE_LIMIT_MAX_MESSAGES,
    RATE_LIMIT_WINDOW_SECONDS,
    _message_log,
)


def setup_function():
    """Clear rate limit state before each test."""
    _message_log.clear()


def test_allows_first_message():
    assert check_rate_limit("hash1") is True


def test_allows_up_to_max_messages():
    for i in range(RATE_LIMIT_MAX_MESSAGES):
        assert check_rate_limit("hash1") is True


def test_blocks_after_max_messages():
    for i in range(RATE_LIMIT_MAX_MESSAGES):
        check_rate_limit("hash1")
    assert check_rate_limit("hash1") is False


def test_different_users_have_separate_limits():
    for i in range(RATE_LIMIT_MAX_MESSAGES):
        check_rate_limit("hash1")
    assert check_rate_limit("hash1") is False
    assert check_rate_limit("hash2") is True


def test_allows_after_window_expires():
    past = time.time() - RATE_LIMIT_WINDOW_SECONDS - 1
    _message_log["hash1"] = [past] * RATE_LIMIT_MAX_MESSAGES
    assert check_rate_limit("hash1") is True


def test_rate_limit_message_french():
    msg = rate_limit_message("fr")
    assert "trop rapidement" in msg


def test_rate_limit_message_english():
    msg = rate_limit_message("en")
    assert "too quickly" in msg


def test_rate_limit_message_unknown_falls_back_to_french():
    msg = rate_limit_message("xx")
    assert "trop rapidement" in msg


def test_constants():
    assert RATE_LIMIT_MAX_MESSAGES == 10
    assert RATE_LIMIT_WINDOW_SECONDS == 60
