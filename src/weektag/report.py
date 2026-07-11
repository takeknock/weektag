"""tt report — per-tag summary table for the terminal (ADR 0006).

Plain text only. A multi-tag event counts its full duration under each of
its tags, so the tag column may sum to more than the total row, which is
computed from real event time.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from . import storage, timeutil


def _completed(week: str) -> list[dict]:
    return [r for r in storage.read_week(week) if not storage.is_running(r)]


def tag_totals(week: str) -> list[tuple[str, float]]:
    totals: dict[str, float] = defaultdict(float)
    for rec in _completed(week):
        hours = storage.duration_hours(rec)
        for tag in rec.get("tags", []):
            totals[tag] += hours
    return sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))


def total_hours(week: str) -> float:
    return sum(storage.duration_hours(r) for r in _completed(week))


def render(week: str) -> str:
    totals = tag_totals(week)
    monday = timeutil.week_monday(week)
    sunday = monday + dt.timedelta(days=6)
    title = f"{week} ({monday.isoformat()} - {sunday.isoformat()})"
    if not totals:
        return f"{title}\nno records\n"
    width = max(len(tag) for tag, _ in totals + [("total", 0.0)])
    lines = [title]
    for tag, hours in totals:
        lines.append(f"{tag:<{width}}  {timeutil.fmt_hours(hours):>7}")
    lines.append("-" * (width + 9))
    lines.append(f"{'total':<{width}}  {timeutil.fmt_hours(total_hours(week)):>7}")
    return "\n".join(lines) + "\n"
