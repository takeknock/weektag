"""Tests for the mini-ULID (ADR 0004): time-sortable, timestamp + randomness."""

import datetime as dt

from weektag.ulid import CROCKFORD, mini_ulid


def aware(y, mo, d, h=0, mi=0, s=0):
    return dt.datetime(y, mo, d, h, mi, s, tzinfo=dt.timezone(dt.timedelta(hours=9)))


def test_length_and_charset():
    uid = mini_ulid(aware(2026, 7, 6, 9, 0, 0))
    assert len(uid) == 8
    assert all(c in CROCKFORD for c in uid)


def test_sortable_across_seconds():
    earlier = mini_ulid(aware(2026, 7, 6, 9, 0, 0))
    later = mini_ulid(aware(2026, 7, 6, 9, 0, 1))
    assert earlier < later


def test_sortable_across_years():
    a = mini_ulid(aware(2026, 1, 1))
    b = mini_ulid(aware(2030, 1, 1))
    assert a < b


def test_randomness_suffix_differs():
    now = aware(2026, 7, 6, 9, 0, 0)
    ids = {mini_ulid(now) for _ in range(50)}
    # same second -> same 6-char prefix, random 2-char suffix varies
    assert len({i[:6] for i in ids}) == 1
    assert len(ids) > 1


def test_default_uses_current_time():
    uid = mini_ulid()
    assert len(uid) == 8
