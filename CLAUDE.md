# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**weektag** — a CLI-first, tag-based time tracker (command name: `tt`) distributed on PyPI as `weektag`. Its differentiator is agent-readability: the data files must be directly readable by humans, `jq`, and coding agents with no preprocessing.

Implementation lives in `src/weektag/` (`cli.py` typer commands → `ops.py` operations → `storage.py` JSONL I/O, plus `timeutil.py`, `ulid.py`, `report.py`, `export.py`). Tests in `tests/` pin the current time by monkeypatching `timeutil.now_local` (see `conftest.py` fixtures `data_dir` / `freeze_now`) so results don't depend on the machine timezone.

## Design source of truth: docs/adr/

`docs/adr/latest/` (Japanese) is the **single canonical source** for all design decisions. Read the relevant ADRs before implementing or reviewing anything, and resolve design questions against them.

ADR rules: new decisions get a new sequential number in `latest/`; numbers are never reused or renumbered. To change a decision, move the old ADR to `archive/{NNNN}/` and write a new one under a new number. Each ADR has four sections: ステータス / コンテキスト / 決定 / 結果.

## Architecture (decided in ADRs 0001–0010)

**Recording model (0002):** start/stop interval records only. At most **one running task** — `start` while another runs auto-stops it. A running task is simply a record with no `stop` key; there is no separate state file. `add`/`edit`/`rm`/`cancel` provide after-the-fact correction.

**Storage (0003):** weekly JSONL files are the **only source of truth** — no index, no DB, no hidden state. Location: `~/.local/share/weektag/events/` (XDG), overridable via `WEEKTAG_DATA_DIR`. Files are named by ISO 8601 week (`2026-W27.jsonl`), weeks start **Monday (unchangeable)**. A record belongs to the week of its **start time**; week-spanning records are not split. Writes go through temp file + atomic `os.replace`. Hand-editing by users/agents is officially supported. The running task is found by scanning recent week files for a record lacking `stop`.

**Record schema (0004):** one JSON object per line:
```json
{"id":"01JZK3AB","start":"2026-07-06T09:00:00+09:00","stop":"2026-07-06T10:30:00+09:00","tags":["writing","client-a"],"note":"ブログ下書き"}
```
- Times are **local time + UTC offset** (ISO 8601) — never normalize to UTC. Week membership is judged by local date.
- `id` is a self-implemented sortable **mini-ULID** (timestamp + randomness); commands accept prefix matches.
- Tags are positional args (`tt start writing client-a`); a quoted `'#tag'` is accepted with `#` stripped. Note goes via `-m`.

**v1 command set (0005):** `start`, `stop`, `status`, `resume`, `add`, `edit`, `rm`, `cancel`, `log`, `report`, `export`. Explicitly **out of scope for v1**: goals/targets, focus timer, timeline UI, plan.

**report vs export (0006):** `report` is a per-tag summary table for the terminal (multi-tag events count their full duration under *each* tag, so the tag column can exceed the total row, which is computed from real event time). `export` emits row-level data, default **TSV**, columns `date/start/stop/hours/tags/note`. Hours are **decimal** (1.50), unrounded unless `--round`. All output is **plain text — no rich formatting anywhere**. No clipboard integration (pipe to clip.exe/pbcopy instead).

**Daily preset (0007):** `tt export --daily [--date 7/6]` emits exactly 3 TSV columns (summary / AM hours / PM hours), **no header by default**, aggregated per (tag-set + note) per day, split mechanically at noon (`--noon` to change), pro-rated across the boundary. Summary = note if present, else space-joined tags.

**Naming (0008):** PyPI/import/repo name `weektag`, console command `tt` via `[project.scripts] tt = "weektag.cli:main"`.

## Stack & constraints (0009)

- **typer** is the only runtime dependency (bundled rich/shellingham included, but rich decoration is unused).
- Python **3.11+**.
- Shell completion is a v1 requirement, including **dynamic tag completion** (candidates gathered from recent week files via typer autocompletion callbacks).
- Current time: `datetime.now().astimezone()` (works on Windows without tzdata).
- No config file in v1 — env var + flags only.

## Development (0010)

- **src layout** (`src/weektag/`), **hatchling** backend, everything in `pyproject.toml`.
- Tooling: **uv** (env/lock), **ruff** (lint + format), **pytest + freezegun** (deterministic time-based tests). Dev deps separated from runtime deps.
- This checkout lives under OneDrive, which breaks uv's default hardlinking — run uv with `UV_LINK_MODE=copy` (e.g. `UV_LINK_MODE=copy uv sync`).
- Commands:
  - `uv sync` — set up environment
  - `uv run pytest` — run tests; single test: `uv run pytest tests/test_x.py::test_name`
  - `uv run ruff check .` / `uv run ruff format .`
  - `uv run tt ...` — run the CLI locally
- CI: GitHub Actions matrix ubuntu/macos/windows × Python 3.11–3.13 on every push/PR.
- Publishing: PyPI **Trusted Publishing** (OIDC) triggered by pushing a git tag. No API tokens.
- License MIT. README in English with a `README.ja.md` alongside.

## Testing focus

Bugs are expected to concentrate in time handling — write freezegun-pinned tests for: ISO week boundaries, the W53 ISO-week-year mismatch (e.g. 2027-01-01 belongs to `2026-W53.jsonl`), noon splitting/pro-rating, timezone offsets, and midnight-spanning events. Windows behavior (paths, `os.replace` atomicity, console output) is verified in CI, not locally.
