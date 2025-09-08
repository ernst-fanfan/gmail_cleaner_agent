import datetime as dt
from unittest.mock import create_autospec

from src.cleanmail.models import MessageSummary, Action
from src.cleanmail.engine import process_inbox
from src.cleanmail.gateway import GmailGateway


def _msg(mid: str, subj: str, from_addr: str = "sender@example.com") -> MessageSummary:
    return MessageSummary(
        id=mid,
        thread_id=f"t-{mid}",
        from_addr=from_addr,
        to_addrs=["you@example.com"],
        cc_addrs=[],
        subject=subj,
        snippet="...",
        labels=["INBOX"],
        date=dt.datetime(2025, 1, 1, 12, 0, 0),
        body_preview="unsubscribe here",
    )


def test_process_inbox_with_mock_gateway():
    now = dt.datetime(2025, 1, 1, 22, 0, 0)
    msgs = {
        "m1": _msg("m1", "Weekly digest", from_addr="news@letters.com"),
        "m2": _msg("m2", "WIN MONEY now!!!", from_addr="spam@bad.com"),
        "m3": _msg("m3", "Hi", from_addr="boss@company.com"),
    }
    gw = create_autospec(GmailGateway, instance=True)
    gw.list_messages.return_value = list(msgs.keys())
    gw.get_message.side_effect = lambda mid, include_body=True: msgs[mid]

    cfg = {
        "mode": {"dry_run": True},
        "limits": {"max_messages_per_run": 10, "fetch_window_hours": 24},
        "safety": {
            "whitelist_senders": ["boss@company.com"],
            "whitelist_domains": [],
            "never_touch_labels": ["STARRED"],
        },
    }

    report = process_inbox(now, cfg, gateway=gw)

    assert sum(report.counts.values()) == 3
    # At least one message should be kept due to whitelist
    keep_count = report.counts.get(Action.KEEP.value, 0)
    assert keep_count >= 1
    # Spammy subject downgraded by policy to ARCHIVE conservatively
    assert report.counts.get(Action.ARCHIVE.value, 0) >= 1

    # In dry_run, gateway side effects should not be invoked
    gw.archive_message.assert_not_called()
    gw.trash_message.assert_not_called()
