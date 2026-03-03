"""Tests for bot countdown timer helpers."""

from datetime import datetime, timedelta, timezone

from src.bot.utils.timers import get_remaining_seconds


def test_get_remaining_seconds_none():
    """None expiration should produce zero remaining time."""
    assert get_remaining_seconds(None) == 0


def test_get_remaining_seconds_past_time():
    """Past expiration should not return negative values."""
    expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)  # noqa: UP017
    assert get_remaining_seconds(expires_at) == 0


def test_get_remaining_seconds_future_time():
    """Future expiration should return a positive number."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=8)  # noqa: UP017
    remaining = get_remaining_seconds(expires_at)
    assert 7 <= remaining <= 8
