# weektag

Tag-based CLI time tracker with agent-readable weekly JSONL storage.

[日本語版 README](README.ja.md)

`weektag` records what you work on as start/stop intervals with flat tags, stores them
as plain JSONL files split by ISO week, and turns them into weekly reports or
TSV/CSV you can paste straight into Excel. The files are the whole database:
`cat`, `grep`, `jq`, and coding agents (Claude Code etc.) can read them with no
preprocessing — and hand-editing them is officially supported.

```console
$ tt start writing client-a -m "blog draft"
started writing client-a "blog draft" at 09:00 [KZ3M2A7Q]

$ tt status
running: writing client-a "blog draft" (started 09:00, 1.50 h elapsed) [KZ3M2A7Q]

$ tt stop
stopped writing client-a "blog draft" (1.50 h)
```

## Install

```console
pipx install weektag    # or: uv tool install weektag
```

The installed command is `tt` (the package name `tt` was taken on PyPI).
Requires Python 3.11+.

## Commands

```
tt start <tags...> [-m NOTE] [--at 9:00]   # start (auto-stops a running task)
tt stop [--at 10:30]                       # stop
tt status                                  # running task + elapsed time
tt resume                                  # restart previous task (same tags/note)
tt add 9:00-10:30 <tags...> [-m NOTE]      # add a past interval
tt edit <id-prefix> [--start] [--stop] [--tags] [-m]
tt rm <id-prefix>                          # delete a record
tt cancel                                  # discard the running task
tt log [--week 2026-W27]                   # raw log with ids (entry point for edit)
tt report [--week 2026-W27 | --last]       # per-tag weekly summary
tt export [--format csv] [-o FILE] [--no-header]
tt export --daily [--date 7/6] [--noon 13:00] [--round 0.25] [--header]
```

Only one task runs at a time: `tt start` while another task is running stops it
first. Forgot to start or stop? `add` / `edit` / `rm` fix the record afterwards.

Shell completion (bash / zsh / fish), including dynamic tag completion from your
recent records:

```console
tt --install-completion
```

## Data format

One JSON object per line, one file per ISO week (Monday start), in
`~/.local/share/weektag/events/` (override with `WEEKTAG_DATA_DIR`;
`XDG_DATA_HOME` is honored):

```json
{"id":"KZ3M2A7Q","start":"2026-07-06T09:00:00+09:00","stop":"2026-07-06T10:30:00+09:00","tags":["writing","client-a"],"note":"blog draft"}
```

- A running task is simply a record without a `stop` key.
- Times are local time with UTC offset; week membership follows the local date
  of `start`. Week-spanning records are not split.
- The week files are the only source of truth — no hidden state, no index, no
  database. Edit them by hand or with an agent whenever you like.

### Note on ISO week years

Files use ISO 8601 week numbering, which can differ from the calendar year at
year boundaries: a record on 2027-01-01 lives in `2026-W53.jsonl`. Commands
resolve this correctly; it only matters when you browse the files by hand.

## Excel workflow

`tt export` prints TSV rows (`date start stop hours tags note`) with decimal
hours (`1.50`), so a paste into Excel splits into columns and `SUM` just works.

`tt export --daily` is a preset for daily-report sheets: exactly three columns
(summary / AM hours / PM hours), aggregated per (tag set + note), split at noon
(`--noon` to change), no header by default so you can append to an existing
table day after day. There is no clipboard integration — pipe instead:

```console
tt export --daily | clip        # Windows
tt export --daily | pbcopy      # macOS
tt export --daily | xclip -sel c
```

## Command name collision

The `tt-time-tracker` package also installs a `tt` command. pipx / uv isolate
the environments, so only the PATH entry can collide. If you use both, rename
one with a shell alias, e.g. `alias wt=tt`.

## Development

```console
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

MIT license.
