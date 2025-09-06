import datetime as dt

from src.cleanmail.engine import process_inbox


def test_process_inbox_scaffold_returns_report(config_tmp):
    now = dt.datetime(2025, 1, 1, 22, 0, 0)
    report = process_inbox(now, config_tmp)
    assert hasattr(report, "counts")
    assert isinstance(report.started_at, dt.datetime)

