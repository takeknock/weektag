"""Tests for tt export — row-level output (ADR 0006)."""

from weektag import export, ops

HEADER = ["date", "start", "stop", "hours", "tags", "note"]


class TestRows:
    def test_columns(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing", "client-a"], note="draft")
        rows = export.week_rows("2026-W28")
        assert rows == [["2026-07-06", "09:00", "10:30", "1.50", "writing client-a", "draft"]]

    def test_running_record_excluded(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        ops.start(["writing"])
        assert export.week_rows("2026-W28") == []

    def test_round_increment(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:10", ["writing"])  # 1.1666h -> 1.25 at 0.25 steps
        rows = export.week_rows("2026-W28", round_increment=0.25)
        assert rows[0][3] == "1.25"


class TestRender:
    def test_tsv_with_header_by_default(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing"], note="draft")
        out = export.render(export.week_rows("2026-W28"), header=HEADER)
        lines = out.strip().split("\n")
        assert lines[0] == "date\tstart\tstop\thours\ttags\tnote"
        assert lines[1] == "2026-07-06\t09:00\t10:30\t1.50\twriting\tdraft"

    def test_no_header(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing"])
        out = export.render(export.week_rows("2026-W28"), header=None)
        assert not out.startswith("date")

    def test_csv_quotes_commas(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing"], note="a, b")
        out = export.render(export.week_rows("2026-W28"), header=HEADER, fmt="csv")
        lines = out.strip().split("\n")
        assert lines[0] == "date,start,stop,hours,tags,note"
        assert '"a, b"' in lines[1]


class TestDaily:
    def test_three_columns_summary_am_pm(self, data_dir, freeze_now):
        # ADR 0007: exactly summary / AM / PM — no plan column
        import datetime as dt

        freeze_now(2026, 7, 6, 18, 0)
        ops.add("9:00-10:30", ["writing"], note="draft")
        rows = export.daily_rows(dt.date(2026, 7, 6))
        assert rows == [["draft", "1.50", ""]]

    def test_summary_falls_back_to_tags(self, data_dir, freeze_now):
        import datetime as dt

        freeze_now(2026, 7, 6, 18, 0)
        ops.add("9:00-10:00", ["writing", "client-a"])
        rows = export.daily_rows(dt.date(2026, 7, 6))
        assert rows[0][0] == "writing client-a"

    def test_noon_split_prorates(self, data_dir, freeze_now):
        import datetime as dt

        freeze_now(2026, 7, 6, 18, 0)
        ops.add("11:00-13:00", ["work"])
        rows = export.daily_rows(dt.date(2026, 7, 6))
        assert rows == [["work", "1.00", "1.00"]]

    def test_noon_override(self, data_dir, freeze_now):
        import datetime as dt

        freeze_now(2026, 7, 6, 18, 0)
        ops.add("11:00-14:00", ["work"])
        rows = export.daily_rows(dt.date(2026, 7, 6), noon=dt.time(13, 0))
        assert rows == [["work", "2.00", "1.00"]]

    def test_same_taskset_aggregates_across_the_day(self, data_dir, freeze_now):
        # ADR 0007: unit is (tag set + note) per day — morning+evening merge
        import datetime as dt

        freeze_now(2026, 7, 6, 20, 0)
        ops.add("9:00-10:00", ["writing"], note="draft")
        ops.add("15:00-16:30", ["writing"], note="draft")
        rows = export.daily_rows(dt.date(2026, 7, 6))
        assert rows == [["draft", "1.00", "1.50"]]

    def test_different_note_separate_rows(self, data_dir, freeze_now):
        import datetime as dt

        freeze_now(2026, 7, 6, 20, 0)
        ops.add("9:00-10:00", ["writing"], note="a")
        ops.add("10:00-11:00", ["writing"], note="b")
        rows = export.daily_rows(dt.date(2026, 7, 6))
        assert [r[0] for r in rows] == ["a", "b"]

    def test_day_spanning_event_counts_only_target_day(self, data_dir, freeze_now):
        # Sunday 23:00 -> Monday 01:00 lives in the PREVIOUS week's file;
        # only the Monday hour counts for Monday (ADR 0007)
        import datetime as dt

        freeze_now(2026, 7, 5, 23, 30)
        ops.add("23:00-1:00", ["ops"])
        freeze_now(2026, 7, 6, 9, 0)
        rows = export.daily_rows(dt.date(2026, 7, 6))
        assert rows == [["ops", "1.00", ""]]
        # and on Sunday only the Sunday hour
        rows_sun = export.daily_rows(dt.date(2026, 7, 5))
        assert rows_sun == [["ops", "", "1.00"]]

    def test_rounding(self, data_dir, freeze_now):
        import datetime as dt

        freeze_now(2026, 7, 6, 18, 0)
        ops.add("9:00-10:10", ["work"])  # 1.1666 -> 1.25
        rows = export.daily_rows(dt.date(2026, 7, 6), round_increment=0.25)
        assert rows == [["work", "1.25", ""]]

    def test_ordered_by_first_start(self, data_dir, freeze_now):
        import datetime as dt

        freeze_now(2026, 7, 6, 20, 0)
        ops.add("13:00-14:00", ["later"])
        ops.add("9:00-10:00", ["earlier"])
        rows = export.daily_rows(dt.date(2026, 7, 6))
        assert [r[0] for r in rows] == ["earlier", "later"]
