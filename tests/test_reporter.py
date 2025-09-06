import datetime as dt

from src.cleanmail.models import RunReport
from src.cleanmail.reporter import build_markdown_report


def test_build_markdown_report_empty(config_tmp):
    now = dt.datetime(2025, 1, 1, 22, 0, 0)
    report = RunReport(
        started_at=now,
        finished_at=now,
        counts={},
        examples={},
        errors=[],
        decisions=[],
    )
    md = build_markdown_report(report, config_tmp)
    assert "Gmail Smart Cleaner Report" in md
    assert "Summary" in md

