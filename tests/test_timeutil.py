"""Tests for ISO-week and time parsing logic (ADR 0003, 0004)."""

import datetime as dt

import pytest

from weektag import timeutil


class TestWeekKey:
    def test_basic(self):
        assert timeutil.week_key(dt.date(2026, 7, 6)) == "2026-W28"

    def test_monday_starts_new_week(self):
        # 2026-07-05 is a Sunday, 2026-07-06 is a Monday
        assert timeutil.week_key(dt.date(2026, 7, 5)) == "2026-W27"
        assert timeutil.week_key(dt.date(2026, 7, 6)) == "2026-W28"

    def test_w53_iso_year_mismatch(self):
        # ADR 0003: a record on 2027-01-01 belongs to 2026-W53
        assert timeutil.week_key(dt.date(2027, 1, 1)) == "2026-W53"

    def test_accepts_datetime(self):
        d = dt.datetime(2026, 7, 6, 9, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        assert timeutil.week_key(d) == "2026-W28"


class TestParseWeek:
    def test_valid(self):
        assert timeutil.parse_week("2026-W27") == "2026-W27"

    def test_normalizes_lowercase_and_padding(self):
        assert timeutil.parse_week("2026-w7") == "2026-W07"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            timeutil.parse_week("July")
        with pytest.raises(ValueError):
            timeutil.parse_week("2026-W60")


class TestWeekNavigation:
    def test_last_week_key(self):
        assert timeutil.last_week_key(dt.date(2026, 7, 6)) == "2026-W27"

    def test_last_week_key_across_year(self):
        assert timeutil.last_week_key(dt.date(2027, 1, 8)) == "2026-W53"

    def test_recent_week_keys(self):
        keys = timeutil.recent_week_keys(dt.date(2026, 7, 6), 3)
        assert keys == ["2026-W28", "2026-W27", "2026-W26"]


class TestParseTime:
    def test_hmm(self):
        assert timeutil.parse_time("9:00") == dt.time(9, 0)

    def test_hhmm(self):
        assert timeutil.parse_time("22:45") == dt.time(22, 45)

    def test_invalid(self):
        with pytest.raises(ValueError):
            timeutil.parse_time("25:00")
        with pytest.raises(ValueError):
            timeutil.parse_time("abc")


class TestAtTime:
    def test_builds_aware_local_datetime(self):
        result = timeutil.at_time(dt.date(2026, 7, 6), "9:30")
        assert result.tzinfo is not None
        assert (result.year, result.month, result.day) == (2026, 7, 6)
        assert (result.hour, result.minute) == (9, 30)


class TestParseRange:
    def test_same_day(self):
        start, stop = timeutil.parse_range("9:00-10:30", dt.date(2026, 7, 6))
        assert start.hour == 9 and stop.hour == 10 and stop.minute == 30
        assert start.date() == stop.date() == dt.date(2026, 7, 6)

    def test_overnight_rolls_to_next_day(self):
        start, stop = timeutil.parse_range("23:00-1:00", dt.date(2026, 7, 6))
        assert start.date() == dt.date(2026, 7, 6)
        assert stop.date() == dt.date(2026, 7, 7)

    def test_invalid(self):
        with pytest.raises(ValueError):
            timeutil.parse_range("9:00", dt.date(2026, 7, 6))


class TestParseDate:
    def test_month_slash_day(self):
        today = dt.date(2026, 7, 6)
        assert timeutil.parse_date("7/6", today) == dt.date(2026, 7, 6)
        assert timeutil.parse_date("12/31", today) == dt.date(2026, 12, 31)

    def test_iso(self):
        assert timeutil.parse_date("2025-01-15", dt.date(2026, 7, 6)) == dt.date(2025, 1, 15)

    def test_invalid(self):
        with pytest.raises(ValueError):
            timeutil.parse_date("someday", dt.date(2026, 7, 6))


class TestParseDatetimeArg:
    def test_time_only_uses_fallback_date(self):
        result = timeutil.parse_datetime_arg("14:00", dt.date(2026, 7, 6))
        assert result.date() == dt.date(2026, 7, 6)
        assert result.hour == 14

    def test_full_iso(self):
        result = timeutil.parse_datetime_arg("2026-07-01T09:00", dt.date(2026, 7, 6))
        assert result.date() == dt.date(2026, 7, 1)
        assert result.tzinfo is not None
