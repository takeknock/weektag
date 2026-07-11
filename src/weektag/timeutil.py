"""ISO-week and local-time helpers (ADR 0003, 0004).

All times are local + UTC offset; week membership is judged on the local
date. Weeks are ISO 8601, Monday-start (fixed, see ADR 0003).
"""

from __future__ import annotations

import datetime as dt
import re

_WEEK_RE = re.compile(r"^(\d{4})-[Ww](\d{1,2})$")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_MD_RE = re.compile(r"^(\d{1,2})/(\d{1,2})$")


def now_local() -> dt.datetime:
    """Current local time with UTC offset, no tzdata needed (ADR 0009)."""
    return dt.datetime.now().astimezone()


def week_key(d: dt.date | dt.datetime) -> str:
    if isinstance(d, dt.datetime):
        d = d.date()
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def parse_week(s: str) -> str:
    m = _WEEK_RE.match(s.strip())
    if not m:
        raise ValueError(f"invalid week (expected like 2026-W27): {s!r}")
    year, week = int(m.group(1)), int(m.group(2))
    if not 1 <= week <= 53:
        raise ValueError(f"invalid week number: {s!r}")
    return f"{year}-W{week:02d}"


def week_monday(key: str) -> dt.date:
    year, week = parse_week(key).split("-W")
    return dt.date.fromisocalendar(int(year), int(week), 1)


def last_week_key(today: dt.date) -> str:
    return week_key(today - dt.timedelta(days=7))


def recent_week_keys(today: dt.date, n: int) -> list[str]:
    return [week_key(today - dt.timedelta(weeks=i)) for i in range(n)]


def parse_time(s: str) -> dt.time:
    m = _TIME_RE.match(s.strip())
    if not m:
        raise ValueError(f"invalid time (expected like 9:00): {s!r}")
    hour, minute = int(m.group(1)), int(m.group(2))
    if hour > 23 or minute > 59:
        raise ValueError(f"invalid time: {s!r}")
    return dt.time(hour, minute)


def local_dt(date: dt.date, time: dt.time) -> dt.datetime:
    """Combine into an aware datetime carrying the local offset for that date."""
    return dt.datetime.combine(date, time).astimezone()


def at_time(date: dt.date, s: str) -> dt.datetime:
    return local_dt(date, parse_time(s))


def parse_range(s: str, date: dt.date) -> tuple[dt.datetime, dt.datetime]:
    parts = s.split("-")
    if len(parts) != 2:
        raise ValueError(f"invalid range (expected like 9:00-10:30): {s!r}")
    start = at_time(date, parts[0])
    stop = at_time(date, parts[1])
    if stop <= start:  # overnight range rolls the stop to the next day
        stop = local_dt(date + dt.timedelta(days=1), parse_time(parts[1]))
    return start, stop


def parse_date(s: str, today: dt.date) -> dt.date:
    s = s.strip()
    m = _MD_RE.match(s)
    if m:
        return dt.date(today.year, int(m.group(1)), int(m.group(2)))
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        raise ValueError(f"invalid date (expected like 7/6 or 2026-07-06): {s!r}") from None


def parse_datetime_arg(s: str, fallback_date: dt.date) -> dt.datetime:
    """For edit: accept a bare time (uses the record's date) or a full ISO datetime."""
    s = s.strip()
    if _TIME_RE.match(s):
        return at_time(fallback_date, s)
    try:
        parsed = dt.datetime.fromisoformat(s)
    except ValueError:
        raise ValueError(
            f"invalid datetime (expected like 14:00 or 2026-07-06T14:00): {s!r}"
        ) from None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def fmt_hours(hours: float) -> str:
    """Decimal hours, two places, no other rounding (ADR 0006)."""
    return f"{hours:.2f}"


def round_to(hours: float, increment: float | None) -> float:
    if not increment:
        return hours
    return round(hours / increment) * increment
