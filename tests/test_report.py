"""Tests for tt report — per-tag summary (ADR 0006)."""

from weektag import ops, report


class TestTagTotals:
    def test_full_duration_counted_under_each_tag(self, data_dir, freeze_now):
        # ADR 0006: a multi-tag event counts its FULL time under each tag
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing", "client-a"])
        totals = dict(report.tag_totals("2026-W28"))
        assert totals["writing"] == 1.5
        assert totals["client-a"] == 1.5

    def test_sorted_by_hours_desc(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:00", ["short"])
        ops.add("10:00-13:00", ["long"])
        assert [t for t, _ in report.tag_totals("2026-W28")] == ["long", "short"]

    def test_running_record_excluded(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.start(["writing"])
        assert report.tag_totals("2026-W28") == []


class TestTotalHours:
    def test_total_is_real_event_time_not_tag_sum(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing", "client-a"])  # 1.5h once, not 3h
        ops.add("10:30-11:00", ["meeting"])
        assert report.total_hours("2026-W28") == 2.0


class TestRender:
    def test_plain_text_with_total_row(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing", "client-a"])
        out = report.render("2026-W28")
        assert "\x1b" not in out  # plain text, no ANSI decoration (ADR 0006/0009)
        assert "2026-W28" in out
        assert "writing" in out and "1.50" in out
        lines = out.strip().splitlines()
        assert "total" in lines[-1] and "1.50" in lines[-1]

    def test_empty_week(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        out = report.render("2026-W28")
        assert "no records" in out
