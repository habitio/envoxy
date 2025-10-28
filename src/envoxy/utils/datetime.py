"""Date/time helpers.

This module exposes a small set of helpers used by the project for producing
API-friendly timestamp strings as well as a few convenience formatters.

New helpers added here are:
- ``coerce_datetime``: accept ``datetime`` or ISO-like strings and return a
    timezone-aware ``datetime`` (or ``None``).
- ``format_iso``: RFC3339-style formatting with configurable fractional
    seconds.
- ``format_rfc1123``: HTTP-date / RFC1123 formatting (always in GMT).
- ``format_unix``: return epoch seconds (or milliseconds) as int/float.
- ``format_strftime``: timezone-aware wrapper around ``strftime``.
- ``api_format``: thin wrapper selecting one of the above styles.

The existing ``Now`` class is left unchanged for backward compatibility.
"""

from datetime import datetime, timezone, date
import time
from typing import Optional, Union

try:
        # Python 3.9+ standard timezone database
        from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - very old Python
        ZoneInfo = None  # type: ignore

# ruff: noqa: E722


class Now:
    @staticmethod
    def log_format():
        """
        Return a timestamp string suitable for log entries.

        Returns:
            str: Current UTC date and time formatted as "YYYY-MM-DDTHH:MM:SS".
                 Example: "2025-10-28T14:45:30"

        Notes:
            - The implementation calls datetime.now().utcnow(), which yields the current
              UTC time; the returned string does not include a timezone designator or
              fractional seconds.
            - The format follows a common ISO 8601 layout without an explicit timezone
              suffix (i.e., no "Z" or offset). If a timezone-aware or differently
              formatted timestamp is required, adjust the implementation accordingly.
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def api_format():
        """Return the current UTC timestamp formatted for the API.

        The returned string uses an ISO-like layout with millisecond precision
        and an explicit UTC offset. Example: "2025-10-28T12:34:56.123+0000".

        Returns:
            str: Current UTC timestamp in the format "%Y-%m-%dT%H:%M:%S.%f"
                 truncated to milliseconds and suffixed with "+0000".
        """
        return "+".join(
            [datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3], "0000"]
        )

    @staticmethod
    def timestamp():
        """
        Return the current Unix timestamp as an integer number of seconds.

        This function returns the current time since the Unix epoch (1970-01-01T00:00:00 UTC)
        truncated to whole seconds (i.e., int(time.time())). The value is taken from the
        system clock and may change if the system time is adjusted.

        Returns:
            int: Seconds since the Unix epoch (UTC).

        Example:
            >>> timestamp()
            1610000000
        """
        return int(time.time())

    @staticmethod
    def to_datetime(date_str, format_str="%Y-%m-%dT%H:%M:%S.%f+0000"):
        """
        Parse a date/time string into a datetime object.

        Parameters
        ----------
        date_str : str
            The date/time string to parse.
        format_str : str, optional
            A format string compatible with datetime.strptime. Defaults to
            "%Y-%m-%dT%H:%M:%S.%f+0000".

        Returns
        -------
        datetime.datetime or None
            A datetime object representing the parsed date/time if parsing succeeds;
            otherwise None is returned (parsing errors are caught and suppressed).

        Notes
        -----
        - This function uses datetime.strptime internally. If the provided format_str
          includes a timezone directive (%z), the resulting datetime may be
          timezone-aware; otherwise it will be naive.
        - The default format contains a literal "+0000" rather than a %z directive,
          so the default result is a naive datetime corresponding to the same wall
          time.
        """
        try:
            return datetime.strptime(date_str, format_str)
        except Exception:
            return None


def _get_zone(tz: Optional[Union[str, ZoneInfo]]) -> Optional[ZoneInfo]:
    """Return a ZoneInfo instance for ``tz`` or None.

    Accepts a ZoneInfo or a string like 'UTC' or 'Europe/London'. If the
    stdlib ``zoneinfo`` is not available this will raise a helpful error when
    used for timezone conversions.
    """
    if tz is None:
        return None
    if isinstance(tz, ZoneInfo):
        return tz
    if isinstance(tz, str):
        if ZoneInfo is None:
            raise RuntimeError("zoneinfo not available in this Python")
        return ZoneInfo(tz)
    return None


def coerce_datetime(value: Optional[Union[str, datetime, date]], assume_tz: str = "UTC") -> Optional[datetime]:
    """Coerce a string, date, or datetime to a timezone-aware ``datetime``.

    - If ``value`` is ``None`` return ``None``.
    - If ``value`` is a ``date`` (but not datetime): convert to datetime at midnight
      in ``assume_tz``.
    - If ``value`` is a ``datetime``: if naive, assign ``assume_tz``;
      otherwise return an aware datetime unchanged.
    - If ``value`` is a ``str`` attempt to parse with ``fromisoformat``; if
      the string ends with ``Z`` we convert it to ``+00:00`` first. Naive
      parsed results are given ``assume_tz``.
    """
    if value is None:
        return None
    
    # Handle date objects (but not datetime, since datetime is a subclass of date)
    if isinstance(value, date) and not isinstance(value, datetime):
        # Convert date to datetime at midnight in the assumed timezone
        dt_naive = datetime.combine(value, datetime.min.time())
        if ZoneInfo is None:
            return dt_naive.replace(tzinfo=timezone.utc)
        return dt_naive.replace(tzinfo=ZoneInfo(assume_tz))
    
    if isinstance(value, datetime):
        if value.tzinfo is None:
            if ZoneInfo is None:
                # fall back to UTC tzinfo from stdlib
                return value.replace(tzinfo=timezone.utc)
            return value.replace(tzinfo=ZoneInfo(assume_tz))
        return value

    if isinstance(value, str):
        s = value
        # Handle trailing Z (common in RFC3339)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            # as a last resort try the older to_datetime helper's default
            dt = Now.to_datetime(s)
            if dt is None:
                raise

        if dt.tzinfo is None:
            if ZoneInfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.replace(tzinfo=ZoneInfo(assume_tz))
        return dt

    raise TypeError("value must be None, date, datetime or ISO-like string")


def _format_fractional(us: int, fractional: Optional[int]) -> str:
    """Return fractional seconds string for ``us`` microseconds.

    fractional is number of digits (0..6). ``None`` means keep all 6 digits.
    """
    if fractional is None:
        return f".{us:06d}" if us else ""
    if fractional <= 0:
        return ""
    if fractional > 6:
        fractional = 6
    # round microseconds to requested digits
    factor = 10 ** (6 - fractional)
    rounded = int(round(us / factor))
    # handle carry that would roll over to the seconds (rare)
    if rounded >= 10 ** fractional:
        rounded = 0
    return f".{rounded:0{fractional}d}"


def format_iso(dt: Union[str, datetime, date, None] = None, fractional: Optional[int] = 3, tz: Optional[Union[str, ZoneInfo]] = None, assume_tz: str = "UTC") -> Optional[str]:
    """Return an RFC3339-like ISO string for ``dt``.

    - ``fractional`` controls digits after the decimal point (0..6). ``None``
      keeps full microsecond precision.
    - ``tz`` (string or ZoneInfo) if provided will be the output timezone;
      if ``tz`` is omitted the datetime's own timezone is used. For UTC the
      output will use a trailing ``Z``.
    - ``assume_tz`` is used when parsing/receiving naive datetimes or strings
      without tz info.
    """
    if dt is None:
        dt_obj = datetime.now(timezone.utc)
    else:
        dt_obj = coerce_datetime(dt, assume_tz=assume_tz)
    if dt_obj is None:
        return None

    out_zone = _get_zone(tz)
    if out_zone is not None:
        dt_obj = dt_obj.astimezone(out_zone)

    # build base time
    base = dt_obj.strftime("%Y-%m-%dT%H:%M:%S")
    frac = _format_fractional(dt_obj.microsecond, fractional)

    # tz offset
    if dt_obj.utcoffset() is None:
        offset = ""
    else:
        # If UTC, use Z
        if dt_obj.utcoffset() == timezone.utc.utcoffset(dt_obj):
            offset = "Z"
            # prefer Z instead of +00:00
            return f"{base}{frac}{offset}"
        off = dt_obj.strftime("%z")  # like +0100
        # convert +0100 -> +01:00
        offset = off[:3] + ":" + off[3:]

    return f"{base}{frac}{offset}"


def format_rfc1123(dt: Union[str, datetime, date, None] = None, assume_tz: str = "UTC") -> Optional[str]:
    """Return an RFC1123 / HTTP-date string for ``dt`` in GMT.

    Example: 'Tue, 28 Oct 2025 12:34:56 GMT'
    """
    from wsgiref.handlers import format_date_time

    if dt is None:
        dt_obj = datetime.now(timezone.utc)
    else:
        dt_obj = coerce_datetime(dt, assume_tz=assume_tz)
    if dt_obj is None:
        return None

    # convert to UTC and format as HTTP-date
    ts = dt_obj.astimezone(timezone.utc).timestamp()
    return format_date_time(ts)


def format_unix(dt: Union[str, datetime, date, None] = None, ms: bool = False, as_int: bool = True, assume_tz: str = "UTC") -> Optional[Union[int, float]]:
    """Return epoch seconds for ``dt``. If ``ms`` is True return
    milliseconds.
    """
    if dt is None:
        dt_obj = datetime.now(timezone.utc)
    else:
        dt_obj = coerce_datetime(dt, assume_tz=assume_tz)
    if dt_obj is None:
        return None
    ts = dt_obj.astimezone(timezone.utc).timestamp()
    if ms:
        val = int(round(ts * 1000.0)) if as_int else ts * 1000.0
        return val
    return int(ts) if as_int else ts


def format_strftime(dt: Union[str, datetime, date, None], fmt: str, tz: Optional[Union[str, ZoneInfo]] = None, assume_tz: str = "UTC") -> Optional[str]:
    """Format datetime with a custom strftime pattern, applying ``tz`` first.
    """
    dt_obj = coerce_datetime(dt, assume_tz=assume_tz) if dt is not None else datetime.now(timezone.utc)
    if dt_obj is None:
        return None
    out_zone = _get_zone(tz)
    if out_zone is not None:
        dt_obj = dt_obj.astimezone(out_zone)
    return dt_obj.strftime(fmt)


def api_format(value: Optional[Union[str, datetime, date]] = None, *, style: str = "iso", fmt: Optional[str] = None, tz: Optional[Union[str, ZoneInfo]] = None, fractional: Optional[int] = 3, unix_ms: bool = False, assume_tz: str = "UTC", as_object: bool = False) -> Optional[Union[str, int, float, datetime]]:
    """High-level API formatter.

    Parameters
    - value: datetime or ISO-like string. If omitted current time is used.
    - style: one of "iso" (default), "rfc1123", "unix", "strftime".
    - fmt: required when style == "strftime".
    - tz: output timezone for textual formats.
    - fractional: digits for ISO fractional seconds.
    - unix_ms: when style == "unix" return milliseconds.
    - assume_tz: timezone to assume for naive inputs.
    - as_object: if True return a datetime object (only meaningful for
      style == "iso"/"strftime" when fmt is None).
    """
    if style not in ("iso", "rfc1123", "unix", "strftime"):
        raise ValueError("unsupported style")

    if style == "strftime":
        if fmt is None:
            raise ValueError("fmt is required when style='strftime'")
        if as_object:
            return coerce_datetime(value, assume_tz=assume_tz)
        return format_strftime(value, fmt, tz=tz, assume_tz=assume_tz)

    if style == "iso":
        if as_object:
            return coerce_datetime(value, assume_tz=assume_tz)
        return format_iso(value, fractional=fractional, tz=tz, assume_tz=assume_tz)

    if style == "rfc1123":
        return format_rfc1123(value, assume_tz=assume_tz)

    # unix
    return format_unix(value, ms=unix_ms, as_int=True, assume_tz=assume_tz)


__all__ = [
    "Now",
    "Format",
    "coerce_datetime",
    "format_iso",
    "format_rfc1123",
    "format_unix",
    "format_strftime",
    "api_format",
]


class Format:
    """Datetime formatting utilities following the ``Now`` class pattern.

    This class provides static methods for formatting datetime values into
    various standard formats (ISO8601/RFC3339, RFC1123, Unix epoch, custom
    strftime). Each method works like ``Now.api_format()``:
    
    - Called with no arguments, returns the current UTC time in the specified format
    - Called with a ``dt`` argument, formats that specific datetime
    
    Methods accept datetime objects or ISO-like strings and handle timezone
    conversions consistently.
    
    Examples:
        >>> Format.iso()  # current time as ISO8601
        '2025-10-28T12:34:56.123Z'
        
        >>> Format.iso(my_datetime, fractional=6)
        '2025-10-28T12:34:56.123456Z'
        
        >>> Format.rfc1123()  # current time as HTTP date
        'Tue, 28 Oct 2025 12:34:56 GMT'
        
        >>> Format.unix(ms=True)  # current time as milliseconds
        1730123696123
    """

    @staticmethod
    def iso(dt: Union[str, datetime, date, None] = None, fractional: Optional[int] = 3, tz: Optional[Union[str, ZoneInfo]] = None, assume_tz: str = "UTC") -> str:
        """Return ISO8601/RFC3339 formatted timestamp.
        
        Args:
            dt: Datetime, date, or ISO string to format. If None, uses current UTC time.
            fractional: Number of fractional second digits (0-6). None preserves all microseconds.
            tz: Output timezone (string like 'UTC' or ZoneInfo). UTC outputs 'Z' suffix.
            assume_tz: Timezone to assume for naive datetime inputs.
            
        Returns:
            ISO8601 formatted string, e.g. '2025-10-28T12:34:56.123Z'
            
        Examples:
            >>> Format.iso()  # current time
            '2025-10-28T12:34:56.123Z'
            >>> Format.iso(my_dt, fractional=0)  # no fractional seconds
            '2025-10-28T12:34:56Z'
            >>> Format.iso(my_dt, tz='Europe/London')
            '2025-10-28T13:34:56.123+01:00'
        """
        return format_iso(dt, fractional=fractional, tz=tz, assume_tz=assume_tz)

    @staticmethod
    def rfc1123(dt: Union[str, datetime, date, None] = None, assume_tz: str = "UTC") -> str:
        """Return RFC1123/HTTP-date formatted timestamp (always GMT).
        
        Args:
            dt: Datetime, date, or ISO string to format. If None, uses current UTC time.
            assume_tz: Timezone to assume for naive datetime inputs.
            
        Returns:
            RFC1123 formatted string, e.g. 'Tue, 28 Oct 2025 12:34:56 GMT'
            
        Examples:
            >>> Format.rfc1123()  # current time
            'Tue, 28 Oct 2025 12:34:56 GMT'
            >>> Format.rfc1123(my_datetime)
            'Wed, 29 Oct 2025 08:15:30 GMT'
        """
        return format_rfc1123(dt, assume_tz=assume_tz)

    @staticmethod
    def unix(dt: Union[str, datetime, date, None] = None, ms: bool = False, as_int: bool = True, assume_tz: str = "UTC") -> Union[int, float]:
        """Return Unix epoch timestamp (seconds or milliseconds).
        
        Args:
            dt: Datetime, date, or ISO string to format. If None, uses current UTC time.
            ms: If True, return milliseconds instead of seconds.
            as_int: If True, return integer (rounded). If False, return float.
            assume_tz: Timezone to assume for naive datetime inputs.
            
        Returns:
            Epoch seconds (or milliseconds if ms=True) as int or float.
            
        Examples:
            >>> Format.unix()  # current time in seconds
            1730123696
            >>> Format.unix(ms=True)  # current time in milliseconds
            1730123696123
            >>> Format.unix(my_dt, ms=True, as_int=False)
            1730123696123.456
        """
        return format_unix(dt, ms=ms, as_int=as_int, assume_tz=assume_tz)

    @staticmethod
    def custom(dt: Union[str, datetime, date, None] = None, fmt: str = "%Y-%m-%d %H:%M:%S", tz: Optional[Union[str, ZoneInfo]] = None, assume_tz: str = "UTC") -> str:
        """Return custom strftime-formatted timestamp.
        
        Args:
            dt: Datetime, date, or ISO string to format. If None, uses current UTC time.
            fmt: strftime format string.
            tz: Output timezone to convert to before formatting.
            assume_tz: Timezone to assume for naive datetime inputs.
            
        Returns:
            Custom formatted string according to fmt.
            
        Examples:
            >>> Format.custom(fmt="%Y-%m-%d")  # current date
            '2025-10-28'
            >>> Format.custom(my_dt, fmt="%A, %B %d, %Y at %I:%M %p")
            'Tuesday, October 28, 2025 at 12:34 PM'
            >>> Format.custom(my_dt, fmt="%Y-%m-%d %H:%M:%S %Z", tz="America/New_York")
            '2025-10-28 08:34:56 EDT'
        """
        return format_strftime(dt, fmt, tz=tz, assume_tz=assume_tz)

    @staticmethod
    def api_format(dt: Union[str, datetime, date, None] = None, assume_tz: str = "UTC") -> str:
        """Return API-formatted timestamp matching Now.api_format() pattern.
        
        Returns a timestamp in the format "YYYY-MM-DDTHH:MM:SS.fff+0000" with
        millisecond precision and UTC offset, matching the format produced by
        Now.api_format() but accepting an optional datetime parameter.
        
        Args:
            dt: Datetime, date, or ISO string to format. If None, uses current UTC time.
            assume_tz: Timezone to assume for naive datetime inputs.
            
        Returns:
            API formatted string, e.g. '2025-10-28T12:34:56.123+0000'
            
        Examples:
            >>> Format.api_format()  # current time
            '2025-10-28T12:34:56.123+0000'
            >>> Format.api_format(my_datetime)
            '2025-10-28T12:34:56.789+0000'
            >>> Format.api_format(date(2025, 10, 28))  # date at midnight UTC
            '2025-10-28T00:00:00.000+0000'
        """
        if dt is None:
            dt_obj = datetime.now(timezone.utc)
        else:
            dt_obj = coerce_datetime(dt, assume_tz=assume_tz)
            if dt_obj is None:
                raise ValueError(f"Could not coerce datetime from: {dt}")
        
        # Convert to UTC for consistent output
        dt_utc = dt_obj.astimezone(timezone.utc)
        
        # Format as YYYY-MM-DDTHH:MM:SS.fff+0000 (milliseconds, UTC offset)
        base = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]  # truncate microseconds to milliseconds
        return f"{base}+0000"

    @staticmethod
    def parse(value: Union[str, datetime, date], assume_tz: str = "UTC") -> datetime:
        """Parse a string or coerce date/datetime to timezone-aware datetime object.
        
        Args:
            value: ISO-like string, date, or datetime object to parse/coerce.
            assume_tz: Timezone to assume for naive datetime inputs.
            
        Returns:
            Timezone-aware datetime object.
            
        Raises:
            ValueError: If string cannot be parsed.
            TypeError: If value is not a string, date, or datetime.
            
        Examples:
            >>> Format.parse("2025-10-28T12:34:56Z")
            datetime.datetime(2025, 10, 28, 12, 34, 56, tzinfo=...)
            >>> Format.parse("2025-10-28T12:34:56")  # naive, assumes UTC
            datetime.datetime(2025, 10, 28, 12, 34, 56, tzinfo=...)
            >>> Format.parse(date(2025, 10, 28))  # date at midnight UTC
            datetime.datetime(2025, 10, 28, 0, 0, 0, tzinfo=...)
        """
        result = coerce_datetime(value, assume_tz=assume_tz)
        if result is None:
            raise ValueError(f"Could not parse datetime from: {value}")
        return result
