from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .models import RunReport


def build_markdown_report(report: RunReport, config: dict) -> str:
    """Render a human-friendly Markdown report from a `RunReport`."""
    lines: List[str] = []
    lines.append(f"# Gmail Smart Cleaner Report – {report.finished_at:%Y-%m-%d}")
    duration = (report.finished_at - report.started_at).total_seconds()
    lines.append("")
    lines.append(f"Duration: {duration:.1f}s")
    lines.append("")
    lines.append("## Summary")
    total = sum(report.counts.values())
    for action, count in report.counts.items():
        lines.append(f"- {action}: {count}")
    lines.append(f"- total: {total}")
    lines.append("")
    for section in ("keep", "archive", "trash"):
        key = section
        samples = report.examples.get(key, [])
        if not samples:
            continue
        title = {
            "keep": "Kept",
            "archive": "Archived",
            "trash": "Trashed (quarantine)",
        }[section]
        lines.append(f"## {title}")
        for subj in samples[:10]:
            lines.append(f"- {subj}")
        lines.append("")
    if report.errors:
        lines.append("## Errors")
        for e in report.errors:
            lines.append(f"- {e}")
        lines.append("")
    lines.append("---")
    lines.append("Configuration snapshot:")
    mode = config.get("mode", {})
    lines.append(f"- dry_run: {mode.get('dry_run', True)}")
    lines.append(f"- action: {mode.get('action', 'trash')}")
    return "\n".join(lines)


def save_report(markdown: str, path: str) -> str:
    """Save the Markdown report to disk and return the final path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(markdown, encoding="utf-8")
    return str(p)


def email_report(markdown: str, recipient: str, gmail_sender_config: dict) -> None:
    """Send the Markdown report via Gmail to the recipient.

    Scaffold: call gmail_client.send_email later; no-op for now.
    """
    # Deferred to gmail_client implementation
    return None

