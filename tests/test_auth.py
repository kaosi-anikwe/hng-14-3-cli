"""Tests for auth helpers."""

from datetime import datetime, timedelta, timezone

from insighta.auth import _format_last_login


def _ts(delta: timedelta) -> str:
    """Return an ISO timestamp offset from now by `delta`."""
    return (datetime.now(timezone.utc) + delta).isoformat()


def test_just_now():
    assert _format_last_login(_ts(timedelta(seconds=-30))) == "just now"


def test_minutes_ago():
    result = _format_last_login(_ts(timedelta(minutes=-5)))
    assert result == "5 minutes ago"


def test_one_minute_ago():
    result = _format_last_login(_ts(timedelta(minutes=-1)))
    assert result == "1 minute ago"


def test_hours_ago():
    result = _format_last_login(_ts(timedelta(hours=-3)))
    assert result == "3 hours ago"


def test_one_hour_ago():
    result = _format_last_login(_ts(timedelta(hours=-1)))
    assert result == "1 hour ago"


def test_days_ago():
    result = _format_last_login(_ts(timedelta(days=-2)))
    assert result == "2 days ago"


def test_one_day_ago():
    result = _format_last_login(_ts(timedelta(days=-1)))
    assert result == "1 day ago"


def test_over_one_week_returns_formatted_date():
    ts = _ts(timedelta(days=-8))
    result = _format_last_login(ts)
    # Should be a formatted date string, not a relative one
    assert "ago" not in result
    assert "just now" not in result


def test_none_returns_placeholder():
    assert _format_last_login(None) == "[dim]—[/dim]"


def test_invalid_string_returns_raw():
    assert _format_last_login("not-a-date") == "not-a-date"


def test_z_suffix_parsed():
    ts = _ts(timedelta(seconds=-10)).replace("+00:00", "Z")
    assert _format_last_login(ts) == "just now"
