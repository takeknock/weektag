"""Deterministic wall-clock tests via freezegun (ADR 0010)."""

import datetime as dt

from freezegun import freeze_time

from weektag import timeutil
from weektag.ulid import mini_ulid


@freeze_time("2026-07-06 03:00:00")
def test_now_local_is_aware():
    now = timeutil.now_local()
    assert now.tzinfo is not None
    assert now.utcoffset() is not None


@freeze_time("2027-01-01 12:00:00")
def test_w53_week_key_from_frozen_now():
    # ADR 0003: 2027-01-01 records land in 2026-W53
    assert timeutil.week_key(dt.date(2027, 1, 1)) == "2026-W53"


def test_mini_ulid_orders_with_frozen_clock():
    with freeze_time("2026-07-06 09:00:00"):
        a = mini_ulid()
    with freeze_time("2026-07-06 09:00:05"):
        b = mini_ulid()
    assert a < b
