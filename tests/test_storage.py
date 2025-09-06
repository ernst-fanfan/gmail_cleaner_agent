import datetime as dt
from pathlib import Path

from src.cleanmail.storage import get_last_run, set_last_run, append_audit_records
from src.cleanmail.models import Decision, Action


def test_last_run_roundtrip(tmp_path):
    db = str(tmp_path / "db.sqlite")
    assert get_last_run(db) is None
    ts = dt.datetime(2025, 1, 1, 12, 0, 0)
    set_last_run(db, ts)
    assert get_last_run(db) == ts


def test_append_audit_records_empty(tmp_path):
    db = str(tmp_path / "db.sqlite")
    # No exception on empty iterable
    append_audit_records(db, [])

