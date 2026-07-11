"""Weekly JSONL storage — the only source of truth (ADR 0003).

No index, no DB, no hidden state. Writes are temp-file + atomic os.replace.
Files are hand-editable by users and agents.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import re
import tempfile
from pathlib import Path

from . import timeutil

_WEEK_FILE_RE = re.compile(r"^(\d{4}-W\d{2})\.jsonl$")

# JSON keys in canonical order (ADR 0004 schema)
_KEY_ORDER = ["id", "start", "stop", "tags", "note"]


def data_dir() -> Path:
    env = os.environ.get("WEEKTAG_DATA_DIR")
    if env:
        return Path(env)
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "weektag" / "events"


def week_path(key: str) -> Path:
    return data_dir() / f"{key}.jsonl"


def read_week(key: str) -> list[dict]:
    path = week_path(key)
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _dump(record: dict) -> str:
    ordered = {k: record[k] for k in _KEY_ORDER if k in record}
    ordered.update({k: v for k, v in record.items() if k not in _KEY_ORDER})
    return json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))


def write_week(key: str, records: list[dict]) -> None:
    path = week_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = sorted(records, key=lambda r: (r["start"], r["id"]))
    content = "".join(_dump(r) + "\n" for r in records)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def record_week_key(record: dict) -> str:
    """A record belongs to the week of its start's local date (ADR 0003)."""
    return timeutil.week_key(start_dt(record))


def append_record(record: dict) -> str:
    key = record_week_key(record)
    records = read_week(key)
    records.append(record)
    write_week(key, records)
    return key


def all_week_keys() -> list[str]:
    d = data_dir()
    if not d.exists():
        return []
    keys = []
    for entry in d.iterdir():
        m = _WEEK_FILE_RE.match(entry.name)
        if m:
            keys.append(m.group(1))
    return sorted(keys)


def start_dt(record: dict) -> dt.datetime:
    return dt.datetime.fromisoformat(record["start"])


def stop_dt(record: dict) -> dt.datetime | None:
    if "stop" not in record:
        return None
    return dt.datetime.fromisoformat(record["stop"])


def is_running(record: dict) -> bool:
    return "stop" not in record


def duration_hours(record: dict) -> float:
    stop = stop_dt(record)
    if stop is None:
        raise ValueError(f"record {record['id']} is still running")
    return (stop - start_dt(record)).total_seconds() / 3600
