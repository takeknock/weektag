"""Tests for weekly JSONL storage (ADR 0003, 0004)."""

import datetime as dt
import json

from weektag import storage


def rec(id_, start, stop=None, tags=None, note=""):
    r = {"id": id_, "start": start, "tags": tags or ["work"], "note": note}
    if stop is not None:
        r["stop"] = stop
    return r


class TestDataDir:
    def test_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path / "custom"))
        assert storage.data_dir() == tmp_path / "custom"

    def test_default_is_xdg_weektag_events(self, monkeypatch, tmp_path):
        monkeypatch.delenv("WEEKTAG_DATA_DIR", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        assert storage.data_dir() == tmp_path / "xdg" / "weektag" / "events"

    def test_fallback_home(self, monkeypatch):
        monkeypatch.delenv("WEEKTAG_DATA_DIR", raising=False)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        d = storage.data_dir()
        assert d.parts[-3:] == (".local", "share", "weektag") or d.parts[-4:-1] == (
            ".local",
            "share",
            "weektag",
        )
        assert d.name == "events"


class TestReadWrite:
    def test_read_missing_week_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
        assert storage.read_week("2026-W28") == []

    def test_roundtrip(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
        records = [rec("AAAAAAAA", "2026-07-06T09:00:00+09:00", "2026-07-06T10:30:00+09:00")]
        storage.write_week("2026-W28", records)
        assert storage.read_week("2026-W28") == records

    def test_one_json_object_per_line(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
        records = [
            rec("AAAAAAAA", "2026-07-06T09:00:00+09:00", "2026-07-06T10:30:00+09:00"),
            rec("BBBBBBBB", "2026-07-06T11:00:00+09:00"),
        ]
        storage.write_week("2026-W28", records)
        lines = (tmp_path / "2026-W28.jsonl").read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            json.loads(line)

    def test_running_record_has_no_stop_key(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
        storage.write_week("2026-W28", [rec("AAAAAAAA", "2026-07-06T09:00:00+09:00")])
        line = (tmp_path / "2026-W28.jsonl").read_text(encoding="utf-8").strip()
        assert "stop" not in json.loads(line)

    def test_japanese_note_stored_readable(self, monkeypatch, tmp_path):
        # ADR 0001: agent-readable — no \uXXXX escaping
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
        storage.write_week(
            "2026-W28",
            [rec("AAAAAAAA", "2026-07-06T09:00:00+09:00", note="ブログ下書き")],
        )
        raw = (tmp_path / "2026-W28.jsonl").read_text(encoding="utf-8")
        assert "ブログ下書き" in raw

    def test_write_sorts_by_start(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
        storage.write_week(
            "2026-W28",
            [
                rec("BBBBBBBB", "2026-07-06T11:00:00+09:00", "2026-07-06T12:00:00+09:00"),
                rec("AAAAAAAA", "2026-07-06T09:00:00+09:00", "2026-07-06T10:00:00+09:00"),
            ],
        )
        ids = [r["id"] for r in storage.read_week("2026-W28")]
        assert ids == ["AAAAAAAA", "BBBBBBBB"]


class TestAppend:
    def test_append_goes_to_week_of_start(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
        # Sunday 2026-07-05 -> W27; spans into Monday but is NOT split (ADR 0003)
        storage.append_record(
            rec("AAAAAAAA", "2026-07-05T23:00:00+09:00", "2026-07-06T01:00:00+09:00")
        )
        assert (tmp_path / "2026-W27.jsonl").exists()
        assert not (tmp_path / "2026-W28.jsonl").exists()

    def test_week_membership_uses_local_date(self, monkeypatch, tmp_path):
        # 2026-07-06T00:30+09:00 is 2026-07-05T15:30Z; local date (Monday) decides -> W28
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
        storage.append_record(rec("AAAAAAAA", "2026-07-06T00:30:00+09:00"))
        assert (tmp_path / "2026-W28.jsonl").exists()


class TestHelpers:
    def test_all_week_keys_sorted(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
        storage.write_week("2026-W28", [rec("AAAAAAAA", "2026-07-06T09:00:00+09:00")])
        storage.write_week("2026-W02", [rec("BBBBBBBB", "2026-01-05T09:00:00+09:00")])
        assert storage.all_week_keys() == ["2026-W02", "2026-W28"]

    def test_duration_hours(self):
        r = rec("AAAAAAAA", "2026-07-06T09:00:00+09:00", "2026-07-06T10:30:00+09:00")
        assert storage.duration_hours(r) == 1.5

    def test_start_dt_parses_offset(self):
        r = rec("AAAAAAAA", "2026-07-06T09:00:00+09:00")
        d = storage.start_dt(r)
        assert d.utcoffset() == dt.timedelta(hours=9)
