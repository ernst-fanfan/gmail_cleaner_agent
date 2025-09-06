from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import List

from .models import RunReport, Decision, Action, MessageSummary


def process_inbox(now: datetime, config: dict) -> RunReport:
    """Run the end-to-end cleaning workflow and produce a report.

    Scaffold implementation: returns an empty report. Will be extended to
    authenticate, fetch, classify, decide, act, and record.
    """
    started = now
    decisions: List[Decision] = []
    counts = Counter()
    examples = defaultdict(list)
    errors: List[str] = []

    finished = datetime.now(timezone.utc)
    return RunReport(
        started_at=started,
        finished_at=finished,
        counts=dict(counts),
        examples=dict(examples),
        errors=errors,
        decisions=decisions,
    )


def decide_action(msg: MessageSummary, config: dict) -> Decision:
    """Combine policy and classifier signals into a final `Decision`.

    Placeholder that keeps everything.
    """
    return Decision(message=msg, action=Action.KEEP, labels_to_add=[], reason="scaffold", by="policy")


def execute_decision(decision: Decision, config: dict) -> None:
    """Perform the chosen action on Gmail (archive/label/trash).

    Scaffold: no-op.
    """
    return None
