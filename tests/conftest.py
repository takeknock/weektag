import datetime as dt

import pytest

from weektag import timeutil


@pytest.fixture
def data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("WEEKTAG_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def freeze_now(monkeypatch):
    """Pin timeutil.now_local to a fixed local time (machine tz, deterministic)."""

    def _freeze(year, month, day, hour=12, minute=0):
        fixed = dt.datetime(year, month, day, hour, minute).astimezone()
        monkeypatch.setattr(timeutil, "now_local", lambda: fixed)
        return fixed

    return _freeze
