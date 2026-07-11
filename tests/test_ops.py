"""Tests for recording operations (ADR 0002, 0005)."""

import pytest

from weektag import ops, storage
from weektag.ops import WeektagError

# 2026-07-06 is a Monday -> 2026-W28


class TestStart:
    def test_creates_running_record_in_current_week(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        rec, stopped = ops.start(["writing", "client-a"], note="draft")
        assert stopped is None
        assert rec["tags"] == ["writing", "client-a"]
        assert rec["note"] == "draft"
        assert "stop" not in rec
        stored = storage.read_week("2026-W28")
        assert len(stored) == 1 and stored[0]["id"] == rec["id"]

    def test_start_at_given_time(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 10, 0)
        rec, _ = ops.start(["writing"], at="9:00")
        assert rec["start"].split("T")[1].startswith("09:00")

    def test_auto_stops_running_task(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        first, _ = ops.start(["writing"])
        freeze_now(2026, 7, 6, 10, 30)
        second, stopped = ops.start(["meeting"])
        assert stopped is not None and stopped["id"] == first["id"]
        assert stopped["stop"] == second["start"]
        records = storage.read_week("2026-W28")
        assert sum(1 for r in records if "stop" not in r) == 1

    def test_requires_at_least_one_tag(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        with pytest.raises(WeektagError):
            ops.start([])


class TestStopStatus:
    def test_stop_completes_running(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        rec, _ = ops.start(["writing"])
        freeze_now(2026, 7, 6, 10, 30)
        stopped = ops.stop()
        assert stopped["id"] == rec["id"]
        assert storage.duration_hours(stopped) == 1.5

    def test_stop_at(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.start(["writing"])
        freeze_now(2026, 7, 6, 11, 0)
        stopped = ops.stop(at="10:30")
        assert stopped["stop"].split("T")[1].startswith("10:30")

    def test_stop_without_running_raises(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        with pytest.raises(WeektagError):
            ops.stop()

    def test_stop_before_start_raises(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.start(["writing"])
        with pytest.raises(WeektagError):
            ops.stop(at="8:00")

    def test_find_running_none(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        assert ops.find_running() is None

    def test_find_running_scans_previous_weeks(self, data_dir, freeze_now):
        # started Friday of the previous week, never stopped
        freeze_now(2026, 7, 3, 9, 0)
        rec, _ = ops.start(["writing"])
        freeze_now(2026, 7, 6, 9, 0)
        found = ops.find_running()
        assert found is not None and found[1]["id"] == rec["id"]
        assert found[0] == "2026-W27"


class TestResume:
    def test_resume_copies_tags_and_note(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.start(["writing", "client-a"], note="draft")
        freeze_now(2026, 7, 6, 12, 0)
        ops.stop()
        freeze_now(2026, 7, 6, 13, 0)
        rec = ops.resume()
        assert rec["tags"] == ["writing", "client-a"]
        assert rec["note"] == "draft"
        assert "stop" not in rec
        assert rec["start"].split("T")[1].startswith("13:00")

    def test_resume_picks_latest_completed(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.add("8:00-8:30", ["standup"])
        ops.add("6:00-7:00", ["exercise"])
        rec = ops.resume()
        assert rec["tags"] == ["standup"]

    def test_resume_while_running_raises(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.start(["writing"])
        with pytest.raises(WeektagError):
            ops.resume()

    def test_resume_with_no_history_raises(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        with pytest.raises(WeektagError):
            ops.resume()


class TestAdd:
    def test_add_completed_interval(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        rec = ops.add("9:00-10:30", ["writing"], note="draft")
        assert storage.duration_hours(rec) == 1.5
        assert storage.read_week("2026-W28")[0]["id"] == rec["id"]

    def test_add_overnight_single_record(self, data_dir, freeze_now):
        # Sunday 23:00 -> Monday 01:00: one record, filed in the start week (W27)
        freeze_now(2026, 7, 5, 23, 30)
        rec = ops.add("23:00-1:00", ["ops"])
        assert storage.duration_hours(rec) == 2.0
        assert [r["id"] for r in storage.read_week("2026-W27")] == [rec["id"]]
        assert storage.read_week("2026-W28") == []


class TestFindByPrefix:
    def test_prefix_match(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        rec = ops.add("9:00-10:00", ["writing"])
        key, found = ops.find_by_prefix(rec["id"][:4])
        assert found["id"] == rec["id"]
        assert key == "2026-W28"

    def test_no_match_raises(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        with pytest.raises(WeektagError):
            ops.find_by_prefix("ZZZZ")

    def test_ambiguous_raises(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        a = ops.add("9:00-10:00", ["a"])
        b = ops.add("10:00-11:00", ["b"])
        common = ""
        for ca, cb in zip(a["id"], b["id"], strict=True):
            if ca != cb:
                break
            common += ca
        if not common:
            pytest.skip("ids share no common prefix")
        with pytest.raises(WeektagError):
            ops.find_by_prefix(common)


class TestEdit:
    def test_edit_tags_and_note(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        rec = ops.add("9:00-10:00", ["writing"], note="old")
        edited = ops.edit(rec["id"], tags=["review"], note="new")
        assert edited["tags"] == ["review"]
        assert edited["note"] == "new"
        assert storage.read_week("2026-W28")[0]["tags"] == ["review"]

    def test_edit_start_time_keeps_date(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        rec = ops.add("9:00-10:00", ["writing"])
        edited = ops.edit(rec["id"], start="8:30")
        assert edited["start"].startswith("2026-07-06T08:30")

    def test_edit_start_across_weeks_moves_record(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        rec = ops.add("9:00-10:00", ["writing"])
        ops.edit(rec["id"], start="2026-07-03T09:00", stop="2026-07-03T10:00")
        assert storage.read_week("2026-W28") == []
        moved = storage.read_week("2026-W27")
        assert len(moved) == 1 and moved[0]["id"] == rec["id"]

    def test_edit_stop_before_start_raises(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        rec = ops.add("9:00-10:00", ["writing"])
        with pytest.raises(WeektagError):
            ops.edit(rec["id"], stop="8:00")


class TestRemoveCancel:
    def test_rm_deletes(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        rec = ops.add("9:00-10:00", ["writing"])
        removed = ops.remove(rec["id"][:4])
        assert removed["id"] == rec["id"]
        assert storage.read_week("2026-W28") == []

    def test_cancel_discards_running(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.start(["writing"])
        cancelled = ops.cancel()
        assert "stop" not in cancelled
        assert storage.read_week("2026-W28") == []

    def test_cancel_without_running_raises(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        with pytest.raises(WeektagError):
            ops.cancel()


class TestLog:
    def test_log_returns_week_records_sorted(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.add("10:00-11:00", ["b"])
        ops.add("9:00-9:30", ["a"])
        records = ops.log_records("2026-W28")
        assert [r["tags"][0] for r in records] == ["a", "b"]


class TestCollectTags:
    def test_collects_recent_tags(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.add("9:00-10:00", ["writing", "client-a"])
        ops.add("10:00-11:00", ["meeting"])
        tags = ops.collect_recent_tags()
        assert {"writing", "client-a", "meeting"} <= set(tags)
