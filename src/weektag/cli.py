"""tt — the weektag command line interface (ADR 0005, 0008, 0009).

Output is plain text only: safe for pipes, agents, and Excel paste.
"""

from __future__ import annotations

import datetime as dt
import sys
from typing import Annotated

import typer

from . import export as export_mod
from . import ops, report, storage, timeutil
from .ops import WeektagError

app = typer.Typer(
    name="tt",
    help="Tag-based time tracker with agent-readable weekly JSONL storage.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


def complete_tag(incomplete: str) -> list[str]:
    """Dynamic tag completion from recent week files (ADR 0009)."""
    return [t for t in ops.collect_recent_tags() if t.startswith(incomplete)]


def _fail(message: str) -> None:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(1)


def _hhmm(iso: str) -> str:
    return dt.datetime.fromisoformat(iso).strftime("%H:%M")


def _summary(rec: dict) -> str:
    # ASCII separators only: Windows consoles may use narrow codepages (cp932)
    tags = " ".join(rec.get("tags", []))
    note = rec.get("note", "")
    return f'{tags} "{note}"' if note else tags


def _echo_stopped(rec: dict) -> None:
    hours = timeutil.fmt_hours(storage.duration_hours(rec))
    typer.echo(f"stopped {_summary(rec)} ({hours} h)")


TagsArg = Annotated[
    list[str], typer.Argument(help="tags (no '#' needed)", autocompletion=complete_tag)
]
NoteOpt = Annotated[str, typer.Option("-m", "--note", help="free-form note")]
AtOpt = Annotated[str | None, typer.Option("--at", help="time like 9:00 (today)")]
WeekOpt = Annotated[str | None, typer.Option("--week", help="ISO week like 2026-W27")]
LastOpt = Annotated[bool, typer.Option("--last", help="previous week")]


def _resolve_week(week: str | None, last: bool) -> str:
    today = timeutil.now_local().date()
    if week is not None:
        return timeutil.parse_week(week)
    if last:
        return timeutil.last_week_key(today)
    return timeutil.week_key(today)


@app.command()
def start(tags: TagsArg, note: NoteOpt = "", at: AtOpt = None) -> None:
    """Start a task (auto-stops a running one)."""
    try:
        rec, stopped = ops.start(tags, note=note, at=at)
    except (WeektagError, ValueError) as e:
        _fail(str(e))
    if stopped is not None:
        _echo_stopped(stopped)
    typer.echo(f"started {_summary(rec)} at {_hhmm(rec['start'])} [{rec['id']}]")


@app.command()
def stop(at: AtOpt = None) -> None:
    """Stop the running task."""
    try:
        rec = ops.stop(at=at)
    except (WeektagError, ValueError) as e:
        _fail(str(e))
    _echo_stopped(rec)


@app.command()
def status() -> None:
    """Show the running task and elapsed time."""
    running = ops.find_running()
    if running is None:
        typer.echo("no task is running")
        return
    _, rec = running
    elapsed = (timeutil.now_local() - storage.start_dt(rec)).total_seconds() / 3600
    typer.echo(
        f"running: {_summary(rec)} "
        f"(started {_hhmm(rec['start'])}, {timeutil.fmt_hours(elapsed)} h elapsed) [{rec['id']}]"
    )


@app.command()
def resume() -> None:
    """Restart the previous task with the same tags and note."""
    try:
        rec = ops.resume()
    except WeektagError as e:
        _fail(str(e))
    typer.echo(f"resumed {_summary(rec)} at {_hhmm(rec['start'])} [{rec['id']}]")


@app.command()
def add(
    range_: Annotated[str, typer.Argument(metavar="RANGE", help="interval like 9:00-10:30")],
    tags: TagsArg,
    note: NoteOpt = "",
) -> None:
    """Add a past interval (today)."""
    try:
        rec = ops.add(range_, tags, note=note)
    except (WeektagError, ValueError) as e:
        _fail(str(e))
    hours = timeutil.fmt_hours(storage.duration_hours(rec))
    typer.echo(
        f"added {_summary(rec)} {_hhmm(rec['start'])}-{_hhmm(rec['stop'])} "
        f"({hours} h) [{rec['id']}]"
    )


@app.command()
def edit(
    id_prefix: Annotated[str, typer.Argument(metavar="ID", help="record id (prefix ok)")],
    start_: Annotated[
        str | None, typer.Option("--start", help="new start (14:00 or 2026-07-06T14:00)")
    ] = None,
    stop_: Annotated[
        str | None, typer.Option("--stop", help="new stop (14:00 or 2026-07-06T14:00)")
    ] = None,
    tags: Annotated[
        str | None, typer.Option("--tags", help="replacement tags, space/comma separated")
    ] = None,
    note: Annotated[str | None, typer.Option("-m", "--note", help="replacement note")] = None,
) -> None:
    """Edit a record by id prefix."""
    tag_list = tags.replace(",", " ").split() if tags is not None else None
    try:
        rec = ops.edit(id_prefix, start=start_, stop=stop_, tags=tag_list, note=note)
    except WeektagError as e:
        _fail(str(e))
    typer.echo(f"edited [{rec['id']}] {_summary(rec)}")


@app.command()
def rm(
    id_prefix: Annotated[str, typer.Argument(metavar="ID", help="record id (prefix ok)")],
) -> None:
    """Delete a record by id prefix."""
    try:
        rec = ops.remove(id_prefix)
    except WeektagError as e:
        _fail(str(e))
    typer.echo(f"removed [{rec['id']}] {_summary(rec)}")


@app.command()
def cancel() -> None:
    """Discard the running task without recording it."""
    try:
        rec = ops.cancel()
    except WeektagError as e:
        _fail(str(e))
    typer.echo(f"cancelled {_summary(rec)} (started {_hhmm(rec['start'])})")


@app.command()
def log(week: WeekOpt = None, last: LastOpt = False) -> None:
    """Raw log with ids (the entry point for edit)."""
    try:
        key = _resolve_week(week, last)
    except ValueError as e:
        _fail(str(e))
    for rec in ops.log_records(key):
        start_ = storage.start_dt(rec)
        stop_ = storage.stop_dt(rec)
        if stop_ is None:
            span, hours = f"{start_:%H:%M}-...", ""
        else:
            span = f"{start_:%H:%M}-{stop_:%H:%M}"
            hours = timeutil.fmt_hours(storage.duration_hours(rec))
        typer.echo(
            f"{rec['id']}  {start_.date().isoformat()}  {span:>12}  {hours:>6}  {_summary(rec)}"
        )


@app.command("report")
def report_cmd(week: WeekOpt = None, last: LastOpt = False) -> None:
    """Per-tag summary for a week (default: this week)."""
    try:
        key = _resolve_week(week, last)
    except ValueError as e:
        _fail(str(e))
    typer.echo(report.render(key), nl=False)


@app.command("export")
def export_cmd(
    week: WeekOpt = None,
    last: LastOpt = False,
    fmt: Annotated[str, typer.Option("--format", help="tsv or csv")] = "tsv",
    output: Annotated[str | None, typer.Option("-o", "--output", help="write to file")] = None,
    header: Annotated[
        bool | None,
        typer.Option("--header/--no-header", help="default: on for week export, off for --daily"),
    ] = None,
    daily: Annotated[bool, typer.Option("--daily", help="3-column daily report preset")] = False,
    date: Annotated[str | None, typer.Option("--date", help="daily target like 7/6")] = None,
    noon: Annotated[str, typer.Option("--noon", help="AM/PM boundary")] = "12:00",
    round_: Annotated[
        float | None, typer.Option("--round", help="round hours to this increment, e.g. 0.25")
    ] = None,
) -> None:
    """Row-level TSV/CSV export, or the daily preset with --daily (ADR 0006, 0007)."""
    if fmt not in ("tsv", "csv"):
        _fail(f"unknown format {fmt!r} (expected tsv or csv)")
    today = timeutil.now_local().date()
    try:
        if daily:
            target = timeutil.parse_date(date, today) if date else today
            rows = export_mod.daily_rows(
                target, noon=timeutil.parse_time(noon), round_increment=round_
            )
            header_row = export_mod.DAILY_HEADER if header else None
        else:
            key = _resolve_week(week, last)
            rows = export_mod.week_rows(key, round_increment=round_)
            header_row = export_mod.WEEK_HEADER if header is None or header else None
    except ValueError as e:
        _fail(str(e))
    content = export_mod.render(rows, header=header_row, fmt=fmt)
    if output:
        with open(output, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        typer.echo(f"wrote {len(rows)} rows to {output}")
    else:
        typer.echo(content, nl=False)


def main() -> None:
    # never crash on notes the console codepage can't render
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    app()


if __name__ == "__main__":
    main()
