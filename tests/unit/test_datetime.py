"""Unit tests for envoxy.utils.datetime module."""

import sys
import os
import pytest
import importlib.util

# Import the datetime module directly without triggering package __init__
datetime_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'envoxy', 'utils', 'datetime.py')
spec = importlib.util.spec_from_file_location("datetime_utils", datetime_path)
datetime_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(datetime_utils)

# Extract the classes and functions
Now = datetime_utils.Now
Format = datetime_utils.Format
coerce_datetime = datetime_utils.coerce_datetime
format_iso = datetime_utils.format_iso
format_rfc1123 = datetime_utils.format_rfc1123
format_unix = datetime_utils.format_unix
format_strftime = datetime_utils.format_strftime
api_format = datetime_utils.api_format

from datetime import datetime, date, timezone

try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False


##### Now class tests #####


def test_now_log_format():
    """Test Now.log_format() returns timestamp in log format."""
    result = Now.log_format()
    assert isinstance(result, str)
    # Format: YYYY-MM-DDTHH:MM:SS
    assert len(result) == 19
    assert result[4] == "-"
    assert result[7] == "-"
    assert result[10] == "T"
    assert result[13] == ":"
    assert result[16] == ":"


def test_now_api_format():
    """Test Now.api_format() returns timestamp in API format."""
    result = Now.api_format()
    assert isinstance(result, str)
    # Format: YYYY-MM-DDTHH:MM:SS.fff+0000
    assert result.endswith("+0000")
    assert "T" in result
    assert "." in result
    # Should have milliseconds (3 digits)
    parts = result.split(".")
    assert len(parts) == 2
    milliseconds = parts[1].replace("+0000", "")
    assert len(milliseconds) == 3


def test_now_timestamp():
    """Test Now.timestamp() returns integer Unix timestamp."""
    result = Now.timestamp()
    assert isinstance(result, int)
    assert result > 0
    # Should be reasonable (after 2020, before 2100)
    assert 1577836800 < result < 4102444800


def test_now_to_datetime_valid():
    """Test Now.to_datetime() parses valid date strings."""
    result = Now.to_datetime("2025-10-28T12:34:56.123000+0000")
    assert isinstance(result, datetime)
    assert result.year == 2025
    assert result.month == 10
    assert result.day == 28
    assert result.hour == 12
    assert result.minute == 34
    assert result.second == 56


def test_now_to_datetime_invalid():
    """Test Now.to_datetime() returns None for invalid strings."""
    result = Now.to_datetime("invalid-date-string")
    assert result is None


##### coerce_datetime tests #####


def test_coerce_datetime_none():
    """Test coerce_datetime with None returns None."""
    assert coerce_datetime(None) is None


def test_coerce_datetime_aware_datetime():
    """Test coerce_datetime preserves timezone-aware datetime."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = coerce_datetime(dt)
    assert result == dt
    assert result.tzinfo is not None


def test_coerce_datetime_naive_datetime():
    """Test coerce_datetime adds timezone to naive datetime."""
    dt = datetime(2025, 10, 28, 12, 34, 56)
    result = coerce_datetime(dt, assume_tz="UTC")
    assert result.tzinfo is not None
    assert result.year == 2025
    assert result.month == 10
    assert result.day == 28


def test_coerce_datetime_date():
    """Test coerce_datetime converts date to datetime at midnight."""
    d = date(2025, 10, 28)
    result = coerce_datetime(d, assume_tz="UTC")
    assert isinstance(result, datetime)
    assert result.year == 2025
    assert result.month == 10
    assert result.day == 28
    assert result.hour == 0
    assert result.minute == 0
    assert result.second == 0
    assert result.tzinfo is not None


def test_coerce_datetime_iso_string_with_z():
    """Test coerce_datetime parses ISO string with trailing Z."""
    result = coerce_datetime("2025-10-28T12:34:56Z")
    assert isinstance(result, datetime)
    assert result.year == 2025
    assert result.month == 10
    assert result.day == 28
    assert result.tzinfo is not None


def test_coerce_datetime_iso_string_with_offset():
    """Test coerce_datetime parses ISO string with timezone offset."""
    result = coerce_datetime("2025-10-28T12:34:56+02:00")
    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_coerce_datetime_invalid_type():
    """Test coerce_datetime raises TypeError for invalid input."""
    with pytest.raises(TypeError, match="must be None, date, datetime or ISO-like string"):
        coerce_datetime(12345)


##### format_iso tests #####


def test_format_iso_none():
    """Test format_iso with None returns current time."""
    result = format_iso(None)
    assert isinstance(result, str)
    assert "T" in result
    # Should end with Z (UTC)
    assert result.endswith("Z") or "+" in result


def test_format_iso_datetime():
    """Test format_iso formats datetime correctly."""
    dt = datetime(2025, 10, 28, 12, 34, 56, 123456, tzinfo=timezone.utc)
    result = format_iso(dt)
    assert result == "2025-10-28T12:34:56.123Z"


def test_format_iso_fractional_seconds():
    """Test format_iso with different fractional second settings."""
    dt = datetime(2025, 10, 28, 12, 34, 56, 123456, tzinfo=timezone.utc)
    
    # No fractional seconds
    assert format_iso(dt, fractional=0) == "2025-10-28T12:34:56Z"
    
    # 3 digits (milliseconds)
    assert format_iso(dt, fractional=3) == "2025-10-28T12:34:56.123Z"
    
    # 6 digits (microseconds)
    assert format_iso(dt, fractional=6) == "2025-10-28T12:34:56.123456Z"


def test_format_iso_date():
    """Test format_iso with date object."""
    d = date(2025, 10, 28)
    result = format_iso(d)
    assert result.startswith("2025-10-28T00:00:00")
    assert "Z" in result


##### format_rfc1123 tests #####


def test_format_rfc1123_none():
    """Test format_rfc1123 with None returns current time."""
    result = format_rfc1123(None)
    assert isinstance(result, str)
    assert result.endswith(" GMT")
    assert "," in result


def test_format_rfc1123_datetime():
    """Test format_rfc1123 formats datetime correctly."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = format_rfc1123(dt)
    assert result == "Tue, 28 Oct 2025 12:34:56 GMT"


def test_format_rfc1123_date():
    """Test format_rfc1123 with date object."""
    d = date(2025, 10, 28)
    result = format_rfc1123(d)
    assert result.endswith(" GMT")
    assert "28 Oct 2025" in result


##### format_unix tests #####


def test_format_unix_none():
    """Test format_unix with None returns current time."""
    result = format_unix(None)
    assert isinstance(result, int)
    assert result > 0


def test_format_unix_datetime_seconds():
    """Test format_unix returns seconds by default."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = format_unix(dt)
    assert isinstance(result, int)
    assert result == 1761654896


def test_format_unix_datetime_milliseconds():
    """Test format_unix returns milliseconds when ms=True."""
    dt = datetime(2025, 10, 28, 12, 34, 56, 123000, tzinfo=timezone.utc)
    result = format_unix(dt, ms=True)
    assert isinstance(result, int)
    assert result == 1761654896123


def test_format_unix_as_float():
    """Test format_unix returns float when as_int=False."""
    dt = datetime(2025, 10, 28, 12, 34, 56, 123456, tzinfo=timezone.utc)
    result = format_unix(dt, as_int=False)
    assert isinstance(result, float)


def test_format_unix_date():
    """Test format_unix with date object."""
    d = date(2025, 10, 28)
    result = format_unix(d)
    assert isinstance(result, int)
    # Midnight UTC for 2025-10-28
    assert result == 1761609600


##### format_strftime tests #####


def test_format_strftime_default():
    """Test format_strftime with default format."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = format_strftime(dt, "%Y-%m-%d")
    assert result == "2025-10-28"


def test_format_strftime_custom():
    """Test format_strftime with custom format."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = format_strftime(dt, "%A, %B %d, %Y")
    assert result == "Tuesday, October 28, 2025"


def test_format_strftime_with_time():
    """Test format_strftime with time components."""
    dt = datetime(2025, 10, 28, 15, 45, 30, tzinfo=timezone.utc)
    result = format_strftime(dt, "%H:%M:%S")
    assert result == "15:45:30"


##### api_format tests #####


def test_api_format_iso_style():
    """Test api_format with ISO style."""
    dt = datetime(2025, 10, 28, 12, 34, 56, 123456, tzinfo=timezone.utc)
    result = api_format(dt, style="iso")
    assert result == "2025-10-28T12:34:56.123Z"


def test_api_format_rfc1123_style():
    """Test api_format with RFC1123 style."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = api_format(dt, style="rfc1123")
    assert result == "Tue, 28 Oct 2025 12:34:56 GMT"


def test_api_format_unix_style():
    """Test api_format with Unix style."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = api_format(dt, style="unix")
    assert result == 1761654896


def test_api_format_strftime_style():
    """Test api_format with strftime style."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = api_format(dt, style="strftime", fmt="%Y-%m-%d")
    assert result == "2025-10-28"


def test_api_format_invalid_style():
    """Test api_format raises error for invalid style."""
    with pytest.raises(ValueError, match="unsupported style"):
        api_format(style="invalid")


def test_api_format_strftime_missing_fmt():
    """Test api_format raises error when fmt missing for strftime."""
    with pytest.raises(ValueError, match="fmt is required"):
        api_format(style="strftime")


##### Format class tests #####


def test_format_iso_current_time():
    """Test Format.iso() returns current time by default."""
    result = Format.iso()
    assert isinstance(result, str)
    assert "T" in result
    assert result.endswith("Z") or "+" in result


def test_format_iso_with_datetime():
    """Test Format.iso() with specific datetime."""
    dt = datetime(2025, 10, 28, 12, 34, 56, 123456, tzinfo=timezone.utc)
    result = Format.iso(dt)
    assert result == "2025-10-28T12:34:56.123Z"


def test_format_iso_with_date():
    """Test Format.iso() with date object."""
    d = date(2025, 10, 28)
    result = Format.iso(d)
    assert result.startswith("2025-10-28T00:00:00")


def test_format_rfc1123_current_time():
    """Test Format.rfc1123() returns current time by default."""
    result = Format.rfc1123()
    assert isinstance(result, str)
    assert result.endswith(" GMT")


def test_format_rfc1123_with_datetime():
    """Test Format.rfc1123() with specific datetime."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = Format.rfc1123(dt)
    assert result == "Tue, 28 Oct 2025 12:34:56 GMT"


def test_format_unix_current_time():
    """Test Format.unix() returns current time by default."""
    result = Format.unix()
    assert isinstance(result, int)
    assert result > 0


def test_format_unix_with_datetime():
    """Test Format.unix() with specific datetime."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = Format.unix(dt)
    assert result == 1761654896


def test_format_unix_milliseconds():
    """Test Format.unix() with milliseconds."""
    dt = datetime(2025, 10, 28, 12, 34, 56, 123000, tzinfo=timezone.utc)
    result = Format.unix(dt, ms=True)
    assert result == 1761654896123


def test_format_custom_current_time():
    """Test Format.custom() returns current time by default."""
    result = Format.custom(fmt="%Y-%m-%d")
    assert isinstance(result, str)
    assert len(result) == 10  # YYYY-MM-DD


def test_format_custom_with_datetime():
    """Test Format.custom() with specific datetime."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = Format.custom(dt, fmt="%Y-%m-%d %H:%M:%S")
    assert result == "2025-10-28 12:34:56"


def test_format_api_format_current_time():
    """Test Format.api_format() returns current time by default."""
    result = Format.api_format()
    assert isinstance(result, str)
    assert result.endswith("+0000")
    assert "T" in result
    assert "." in result


def test_format_api_format_with_datetime():
    """Test Format.api_format() with specific datetime."""
    dt = datetime(2025, 10, 28, 12, 34, 56, 123456, tzinfo=timezone.utc)
    result = Format.api_format(dt)
    assert result == "2025-10-28T12:34:56.123+0000"


def test_format_api_format_with_date():
    """Test Format.api_format() with date object."""
    d = date(2025, 10, 28)
    result = Format.api_format(d)
    assert result == "2025-10-28T00:00:00.000+0000"


def test_format_api_format_with_iso_string():
    """Test Format.api_format() with ISO string."""
    result = Format.api_format("2025-10-28T12:34:56.789Z")
    assert result == "2025-10-28T12:34:56.789+0000"


def test_format_api_format_matches_now():
    """Test Format.api_format() produces same format as Now.api_format()."""
    now_result = Now.api_format()
    format_result = Format.api_format()
    
    # Both should have same structure (may differ by milliseconds due to timing)
    assert len(now_result) == len(format_result)
    assert now_result.endswith("+0000")
    assert format_result.endswith("+0000")
    assert "T" in now_result and "T" in format_result
    assert "." in now_result and "." in format_result


def test_format_parse_iso_string():
    """Test Format.parse() with ISO string."""
    result = Format.parse("2025-10-28T12:34:56Z")
    assert isinstance(result, datetime)
    assert result.year == 2025
    assert result.month == 10
    assert result.day == 28
    assert result.hour == 12
    assert result.minute == 34
    assert result.second == 56
    assert result.tzinfo is not None


def test_format_parse_datetime():
    """Test Format.parse() with datetime object."""
    dt = datetime(2025, 10, 28, 12, 34, 56)
    result = Format.parse(dt)
    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_format_parse_date():
    """Test Format.parse() with date object."""
    d = date(2025, 10, 28)
    result = Format.parse(d)
    assert isinstance(result, datetime)
    assert result.year == 2025
    assert result.month == 10
    assert result.day == 28
    assert result.hour == 0
    assert result.tzinfo is not None


def test_format_parse_invalid():
    """Test Format.parse() raises error for invalid input."""
    with pytest.raises(ValueError, match="Invalid isoformat string"):
        Format.parse("invalid-date")


@pytest.mark.skipif(not HAS_ZONEINFO, reason="zoneinfo not available")
def test_format_iso_with_timezone():
    """Test Format.iso() with timezone conversion."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = Format.iso(dt, tz="America/New_York")
    # UTC 12:34 is EDT 08:34 (UTC-4)
    assert result.startswith("2025-10-28T08:34:56")
    assert "-04:00" in result or "EDT" in result.upper()


@pytest.mark.skipif(not HAS_ZONEINFO, reason="zoneinfo not available")
def test_format_custom_with_timezone():
    """Test Format.custom() with timezone conversion."""
    dt = datetime(2025, 10, 28, 12, 34, 56, tzinfo=timezone.utc)
    result = Format.custom(dt, fmt="%H:%M", tz="America/New_York")
    # UTC 12:34 is EDT 08:34
    assert result == "08:34"
