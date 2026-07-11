"""tt export — row-level TSV/CSV output and the daily preset (ADR 0006, 0007)."""

from __future__ import annotations

import csv
import datetime as dt
import io

from . import storage, timeutil

WEEK_HEADER = ["date", "start", "stop", "hours", "tags", "note"]
DAILY_HEADER = ["summary", "am", "pm"]


def _fmt(hours: float, round_increment: float | None) -> str:
    return timeutil.fmt_hours(timeutil.round_to(hours, round_increment))


def week_rows(week: str, round_increment: float | None = None) -> list[list[str]]:
    rows = []
    records = sorted(storage.read_week(week), key=lambda r: (r["start"], r["id"]))
    for rec in records:
        if storage.is_running(rec):
            continue
        start = storage.start_dt(rec)
        stop = storage.stop_dt(rec)
        rows.append(
            [
                start.date().isoformat(),
                start.strftime("%H:%M"),
                stop.strftime("%H:%M"),
                _fmt(storage.duration_hours(rec), round_increment),
                " ".join(rec.get("tags", [])),
                rec.get("note", ""),
            ]
        )
    return rows


def daily_rows(
    date: dt.date,
    noon: dt.time = dt.time(12, 0),
    round_increment: float | None = None,
) -> list[list[str]]:
    """3-column daily preset: summary / AM / PM (ADR 0007).

    Rows aggregate by (tag set + note); events are clipped to the target
    date and split mechanically at the noon boundary.
    """
    day_start = timeutil.local_dt(date, dt.time(0, 0))
    day_end = timeutil.local_dt(date + dt.timedelta(days=1), dt.time(0, 0))
    noon_dt = timeutil.local_dt(date, noon)

    def overlap(a0: dt.datetime, a1: dt.datetime, b0: dt.datetime, b1: dt.datetime) -> float:
        lo, hi = max(a0, b0), min(a1, b1)
        return max((hi - lo).total_seconds(), 0) / 3600

    # a day-spanning event may live in the previous week's file (ADR 0003)
    weeks = {timeutil.week_key(date), timeutil.week_key(date - dt.timedelta(days=7))}
    groups: dict[tuple, dict] = {}
    for week in sorted(weeks):
        for rec in storage.read_week(week):
            if storage.is_running(rec):
                continue
            start, stop = storage.start_dt(rec), storage.stop_dt(rec)
            if stop <= day_start or start >= day_end:
                continue
            key = (tuple(sorted(rec.get("tags", []))), rec.get("note", ""))
            group = groups.setdefault(
                key, {"am": 0.0, "pm": 0.0, "first": start, "tags": rec.get("tags", [])}
            )
            group["am"] += overlap(start, stop, day_start, noon_dt)
            group["pm"] += overlap(start, stop, noon_dt, day_end)
            if start < group["first"]:
                group["first"] = start
                group["tags"] = rec.get("tags", [])

    rows = []
    for (_, note), group in sorted(groups.items(), key=lambda kv: kv[1]["first"]):
        summary = note or " ".join(group["tags"])
        cells = []
        for hours in (group["am"], group["pm"]):
            rounded = timeutil.round_to(hours, round_increment)
            cells.append(timeutil.fmt_hours(rounded) if rounded > 0 else "")
        rows.append([summary, *cells])
    return rows


def render(rows: list[list[str]], header: list[str] | None = None, fmt: str = "tsv") -> str:
    all_rows = ([header] if header else []) + rows
    if fmt == "csv":
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows(all_rows)
        return buf.getvalue()
    return "".join("\t".join(cell.replace("\t", " ") for cell in row) + "\n" for row in all_rows)
