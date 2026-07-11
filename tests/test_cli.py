"""End-to-end CLI tests through typer's CliRunner (ADR 0005)."""

import contextlib
import json

from typer.testing import CliRunner

from weektag import ops, storage
from weektag.cli import app, complete_tag

runner = CliRunner()


def all_output(result):
    out = result.output
    with contextlib.suppress(ValueError, AttributeError):
        out += result.stderr
    return out


class TestStartStopStatus:
    def test_start_creates_record(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        result = runner.invoke(app, ["start", "writing", "client-a", "-m", "draft"])
        assert result.exit_code == 0
        assert "writing" in result.output
        records = storage.read_week("2026-W28")
        assert len(records) == 1
        assert records[0]["tags"] == ["writing", "client-a"]
        assert records[0]["note"] == "draft"

    def test_quoted_hash_tag_is_stripped(self, data_dir, freeze_now):
        # ADR 0004: '#writing' arrives quoted -> accept with '#' stripped
        freeze_now(2026, 7, 6, 9, 0)
        result = runner.invoke(app, ["start", "#writing"])
        assert result.exit_code == 0
        assert storage.read_week("2026-W28")[0]["tags"] == ["writing"]

    def test_start_at(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 10, 0)
        runner.invoke(app, ["start", "writing", "--at", "9:00"])
        assert "T09:00" in storage.read_week("2026-W28")[0]["start"]

    def test_start_auto_stops_previous(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        runner.invoke(app, ["start", "writing"])
        freeze_now(2026, 7, 6, 10, 0)
        result = runner.invoke(app, ["start", "meeting"])
        assert result.exit_code == 0
        assert "stopped" in result.output
        assert sum(1 for r in storage.read_week("2026-W28") if "stop" not in r) == 1

    def test_stop(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        runner.invoke(app, ["start", "writing"])
        freeze_now(2026, 7, 6, 10, 30)
        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0
        assert "1.50" in result.output

    def test_stop_nothing_running_fails(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        result = runner.invoke(app, ["stop"])
        assert result.exit_code == 1
        assert "no task is running" in all_output(result)

    def test_status_running(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        runner.invoke(app, ["start", "writing"])
        freeze_now(2026, 7, 6, 10, 30)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "writing" in result.output
        assert "1.50" in result.output

    def test_status_idle(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "no task is running" in result.output


class TestResumeAddEditRmCancel:
    def test_resume(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        runner.invoke(app, ["start", "writing", "-m", "draft"])
        freeze_now(2026, 7, 6, 12, 0)
        runner.invoke(app, ["stop"])
        freeze_now(2026, 7, 6, 13, 0)
        result = runner.invoke(app, ["resume"])
        assert result.exit_code == 0
        running = [r for r in storage.read_week("2026-W28") if "stop" not in r]
        assert len(running) == 1 and running[0]["tags"] == ["writing"]

    def test_add(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        result = runner.invoke(app, ["add", "9:00-10:30", "writing", "-m", "draft"])
        assert result.exit_code == 0
        rec = storage.read_week("2026-W28")[0]
        assert storage.duration_hours(rec) == 1.5

    def test_edit(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        rec = ops.add("9:00-10:00", ["writing"])
        result = runner.invoke(app, ["edit", rec["id"][:4], "--tags", "review", "-m", "new"])
        assert result.exit_code == 0
        stored = storage.read_week("2026-W28")[0]
        assert stored["tags"] == ["review"] and stored["note"] == "new"

    def test_edit_start_stop(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        rec = ops.add("9:00-10:00", ["writing"])
        result = runner.invoke(app, ["edit", rec["id"], "--start", "8:00", "--stop", "9:30"])
        assert result.exit_code == 0
        stored = storage.read_week("2026-W28")[0]
        assert "T08:00" in stored["start"] and "T09:30" in stored["stop"]

    def test_rm(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        rec = ops.add("9:00-10:00", ["writing"])
        result = runner.invoke(app, ["rm", rec["id"][:4]])
        assert result.exit_code == 0
        assert storage.read_week("2026-W28") == []

    def test_rm_unknown_id_fails(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        result = runner.invoke(app, ["rm", "ZZZZ"])
        assert result.exit_code == 1

    def test_cancel(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        runner.invoke(app, ["start", "writing"])
        result = runner.invoke(app, ["cancel"])
        assert result.exit_code == 0
        assert storage.read_week("2026-W28") == []


class TestLogReport:
    def test_log_shows_ids(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        rec = ops.add("9:00-10:30", ["writing"], note="draft")
        result = runner.invoke(app, ["log"])
        assert result.exit_code == 0
        assert rec["id"] in result.output
        assert "writing" in result.output

    def test_log_specific_week(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:00", ["writing"])
        result = runner.invoke(app, ["log", "--week", "2026-W27"])
        assert result.exit_code == 0
        assert "writing" not in result.output

    def test_log_marks_running(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        runner.invoke(app, ["start", "writing"])
        result = runner.invoke(app, ["log"])
        assert "..." in result.output

    def test_report_default_current_week(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing"])
        result = runner.invoke(app, ["report"])
        assert result.exit_code == 0
        assert "writing" in result.output and "1.50" in result.output

    def test_report_last_week(self, data_dir, freeze_now):
        freeze_now(2026, 7, 3, 14, 0)  # Friday of W27
        ops.add("9:00-10:00", ["oldwork"])
        freeze_now(2026, 7, 6, 14, 0)  # Monday of W28
        result = runner.invoke(app, ["report", "--last"])
        assert "oldwork" in result.output

    def test_report_bad_week_fails(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        result = runner.invoke(app, ["report", "--week", "July"])
        assert result.exit_code == 1


class TestExport:
    def test_default_tsv_with_header(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing"], note="draft")
        result = runner.invoke(app, ["export"])
        lines = result.output.strip().split("\n")
        assert lines[0] == "date\tstart\tstop\thours\ttags\tnote"
        assert lines[1] == "2026-07-06\t09:00\t10:30\t1.50\twriting\tdraft"

    def test_no_header(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing"])
        result = runner.invoke(app, ["export", "--no-header"])
        assert not result.output.startswith("date")

    def test_csv_format(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing"])
        result = runner.invoke(app, ["export", "--format", "csv"])
        assert "date,start,stop,hours,tags,note" in result.output

    def test_output_file(self, data_dir, freeze_now, tmp_path):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:30", ["writing"])
        out_file = tmp_path / "out.tsv"
        result = runner.invoke(app, ["export", "-o", str(out_file)])
        assert result.exit_code == 0
        assert "writing" in out_file.read_text(encoding="utf-8")

    def test_daily_three_columns_no_header(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 18, 0)
        ops.add("9:00-10:30", ["writing"], note="draft")
        result = runner.invoke(app, ["export", "--daily"])
        lines = result.output.strip("\n").split("\n")
        assert lines == ["draft\t1.50\t"]

    def test_daily_header_opt_in(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 18, 0)
        ops.add("9:00-10:30", ["writing"])
        result = runner.invoke(app, ["export", "--daily", "--header"])
        assert result.output.startswith("summary\tam\tpm")

    def test_daily_date_noon_round(self, data_dir, freeze_now):
        freeze_now(2026, 7, 7, 18, 0)  # export yesterday from Tuesday
        ops.add("9:00-10:10", ["work"])  # runs on the frozen "today"... use --date
        result = runner.invoke(
            app, ["export", "--daily", "--date", "7/7", "--noon", "13:00", "--round", "0.25"]
        )
        assert result.output.strip("\n") == "work\t1.25\t"


class TestCompletion:
    def test_complete_tag_prefix(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 14, 0)
        ops.add("9:00-10:00", ["writing", "wiki"])
        ops.add("10:00-11:00", ["meeting"])
        assert complete_tag("w") == ["wiki", "writing"]
        assert complete_tag("") == ["meeting", "wiki", "writing"]


class TestDataIsAgentReadable:
    def test_week_file_is_plain_jsonl(self, data_dir, freeze_now):
        freeze_now(2026, 7, 6, 9, 0)
        runner.invoke(app, ["start", "writing", "-m", "ブログ下書き"])
        raw = (data_dir / "2026-W28.jsonl").read_text(encoding="utf-8")
        rec = json.loads(raw.strip())
        assert set(rec) == {"id", "start", "tags", "note"}
        assert "ブログ下書き" in raw
