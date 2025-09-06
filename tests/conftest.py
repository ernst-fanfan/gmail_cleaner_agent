import datetime as dt
from typing import Callable

import pytest

from src.cleanmail.config import load_config
from src.cleanmail.models import MessageSummary


@pytest.fixture
def config_tmp(tmp_path) -> dict:
    cfg_text = (
        "schedule:\n"
        "  time: '22:00'\n"
        "  timezone: 'America/New_York'\n"
        "mode:\n"
        "  dry_run: true\n"
        "  action: 'trash'\n"
        "report:\n"
        "  save_dir: 'reports'\n"
        "secrets:\n"
        "  sqlite_path: 'data/cleanmail.db'\n"
    )
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(cfg_text, encoding="utf-8")
    return load_config(str(cfg_file))


@pytest.fixture
def factory_message() -> Callable[..., MessageSummary]:
    def _make(**overrides) -> MessageSummary:
        base = dict(
            id="m1",
            thread_id="t1",
            from_addr="sender@example.com",
            to_addrs=["you@example.com"],
            cc_addrs=[],
            subject="Test Subject",
            snippet="This is a snippet",
            labels=["INBOX"],
            date=dt.datetime(2025, 1, 1, 12, 0, 0),
            body_preview="Hello world",
        )
        base.update(overrides)
        return MessageSummary(**base)

    return _make

