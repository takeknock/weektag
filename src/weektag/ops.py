"""Recording operations (ADR 0002, 0005).

At most one running task at a time; a running task is a record without a
`stop` key. Everything is read-modify-write against the weekly JSONL files.
"""

from __future__ import annotations

import datetime as dt

from . import storage, timeutil
from .ulid import mini_ulid

# ADR 0003: the running task is found by scanning recent week files.
RECENT_SCAN_WEEKS = 4


class WeektagError(Exception):
    """User-facing error; the CLI prints the message and exits non-zero."""


def _iso(d: dt.datetime) -> str:
    return d.isoformat(timespec="seconds")


def clean_tags(tags: list[str]) -> list[str]:
    """Strip a quoted leading '#' (ADR 0004) and drop empties."""
    cleaned = [t.lstrip("#").strip() for t in tags]
    return [t for t in cleaned if t]


def find_running() -> tuple[str, dict] | None:
    today = timeutil.now_local().date()
    candidates = []
    for key in timeutil.recent_week_keys(today, RECENT_SCAN_WEEKS):
        for rec in storage.read_week(key):
            if storage.is_running(rec):
                candidates.append((key, rec))
    if not candidates:
        return None
    return max(candidates, key=lambda kr: kr[1]["start"])


def _resolve_at(at: str | None) -> dt.datetime:
    now = timeutil.now_local()
    if at is None:
        return now
    return timeutil.at_time(now.date(), at)


def _complete(key: str, rec: dict, stop: dt.datetime) -> dict:
    start = storage.start_dt(rec)
    if stop <= start:
        raise WeektagError(
            f"stop time {_iso(stop)} is not after start {_iso(start)} (record {rec['id']})"
        )
    records = storage.read_week(key)
    for r in records:
        if r["id"] == rec["id"]:
            r["stop"] = _iso(stop)
            rec = r
            break
    storage.write_week(key, records)
    return rec


def start(tags: list[str], note: str = "", at: str | None = None) -> tuple[dict, dict | None]:
    tags = clean_tags(tags)
    if not tags:
        raise WeektagError("at least one tag is required")
    start_time = _resolve_at(at)
    stopped = None
    running = find_running()
    if running is not None:
        stopped = _complete(running[0], running[1], start_time)
    rec = {"id": mini_ulid(start_time), "start": _iso(start_time), "tags": tags, "note": note}
    storage.append_record(rec)
    return rec, stopped


def stop(at: str | None = None) -> dict:
    running = find_running()
    if running is None:
        raise WeektagError("no task is running")
    return _complete(running[0], running[1], _resolve_at(at))


def cancel() -> dict:
    running = find_running()
    if running is None:
        raise WeektagError("no task is running")
    key, rec = running
    storage.write_week(key, [r for r in storage.read_week(key) if r["id"] != rec["id"]])
    return rec


def resume() -> dict:
    if find_running() is not None:
        raise WeektagError("a task is already running (stop it first)")
    today = timeutil.now_local().date()
    completed = []
    for key in timeutil.recent_week_keys(today, RECENT_SCAN_WEEKS):
        completed.extend(r for r in storage.read_week(key) if not storage.is_running(r))
    if not completed:
        raise WeektagError("no previous task to resume")
    last = max(completed, key=lambda r: r["stop"])
    rec, _ = start(list(last["tags"]), note=last.get("note", ""))
    return rec


def add(range_str: str, tags: list[str], note: str = "") -> dict:
    tags = clean_tags(tags)
    if not tags:
        raise WeektagError("at least one tag is required")
    today = timeutil.now_local().date()
    try:
        start_time, stop_time = timeutil.parse_range(range_str, today)
    except ValueError as e:
        raise WeektagError(str(e)) from None
    rec = {
        "id": mini_ulid(start_time),
        "start": _iso(start_time),
        "stop": _iso(stop_time),
        "tags": tags,
        "note": note,
    }
    storage.append_record(rec)
    return rec


def find_by_prefix(prefix: str) -> tuple[str, dict]:
    prefix = prefix.strip().upper()
    if not prefix:
        raise WeektagError("empty id")
    matches = [
        (key, rec)
        for key in storage.all_week_keys()
        for rec in storage.read_week(key)
        if rec["id"].upper().startswith(prefix)
    ]
    if not matches:
        raise WeektagError(f"no record matching id {prefix!r}")
    if len(matches) > 1:
        ids = ", ".join(rec["id"] for _, rec in matches)
        raise WeektagError(f"id {prefix!r} is ambiguous: {ids}")
    return matches[0]


def edit(
    prefix: str,
    start: str | None = None,
    stop: str | None = None,
    tags: list[str] | None = None,
    note: str | None = None,
) -> dict:
    key, rec = find_by_prefix(prefix)
    old_start = storage.start_dt(rec)
    try:
        if start is not None:
            rec["start"] = _iso(timeutil.parse_datetime_arg(start, old_start.date()))
        if stop is not None:
            fallback = storage.stop_dt(rec) or storage.start_dt(rec)
            rec["stop"] = _iso(timeutil.parse_datetime_arg(stop, fallback.date()))
    except ValueError as e:
        raise WeektagError(str(e)) from None
    if tags is not None:
        cleaned = clean_tags(tags)
        if not cleaned:
            raise WeektagError("at least one tag is required")
        rec["tags"] = cleaned
    if note is not None:
        rec["note"] = note
    new_stop = storage.stop_dt(rec)
    if new_stop is not None and new_stop <= storage.start_dt(rec):
        raise WeektagError("stop time must be after start time")
    new_key = storage.record_week_key(rec)
    remaining = [r for r in storage.read_week(key) if r["id"] != rec["id"]]
    if new_key == key:
        storage.write_week(key, remaining + [rec])
    else:
        storage.write_week(key, remaining)
        storage.append_record(rec)
    return rec


def remove(prefix: str) -> dict:
    key, rec = find_by_prefix(prefix)
    storage.write_week(key, [r for r in storage.read_week(key) if r["id"] != rec["id"]])
    return rec


def log_records(week: str) -> list[dict]:
    return sorted(storage.read_week(week), key=lambda r: (r["start"], r["id"]))


def collect_recent_tags() -> list[str]:
    """Tag candidates for shell completion (ADR 0009)."""
    today = timeutil.now_local().date()
    tags: set[str] = set()
    for key in timeutil.recent_week_keys(today, RECENT_SCAN_WEEKS):
        for rec in storage.read_week(key):
            tags.update(rec.get("tags", []))
    return sorted(tags)
