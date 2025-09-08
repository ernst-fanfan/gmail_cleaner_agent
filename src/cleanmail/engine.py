from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .models import RunReport, Decision, Action, MessageSummary
from .policies import policy_decide
from .gateway import GmailGateway


def process_inbox(now: datetime, config: Dict[str, Any], gateway: Optional[GmailGateway] = None) -> RunReport:
    """Run the end-to-end cleaning workflow and produce a report.

    Scaffold implementation: returns an empty report. Will be extended to
    authenticate, fetch, classify, decide, act, and record.
    """
    started = now
    decisions: List[Decision] = []
    counts = Counter()
    examples = defaultdict(list)
    errors: List[str] = []

    # If no gateway is provided, short-circuit with an empty report (backward compatible)
    if gateway is None:
        finished = datetime.now(timezone.utc)
        return RunReport(
            started_at=started,
            finished_at=finished,
            counts=dict(counts),
            examples=dict(examples),
            errors=errors,
            decisions=decisions,
        )

    # Fetch message IDs
    lim = config.get("limits", {})
    max_results = int(lim.get("max_messages_per_run", 500))
    q = "-in:chats"
    # Optionally add time window (e.g., 24 hours) as a Gmail search operator
    window_h = int(lim.get("fetch_window_hours", 24))
    if window_h > 0:
        q = f"newer_than:{window_h}h {q}"

    try:
        ids = list(gateway.list_messages(max_results=max_results, query=q))
    except Exception as e:  # pragma: no cover - defensive
        errors.append(f"list_messages failed: {e}")
        ids = []

    # Fetch, decide, and (optionally) act
    dry_run = bool(config.get("mode", {}).get("dry_run", True))
    for mid in ids:
        try:
            msg = gateway.get_message(mid, include_body=True)
        except Exception as e:  # pragma: no cover
            errors.append(f"get_message {mid} failed: {e}")
            continue

        decision = policy_decide(msg, config)
        if decision is None:
            # Default conservative fallback
            decision = Decision(message=msg, action=Action.KEEP, labels_to_add=[], reason="fallback", by="policy")

        # Execute if not dry-run
        try:
            execute_decision(decision, config, gateway=gateway, dry_run=dry_run)
        except Exception as e:  # pragma: no cover
            errors.append(f"action failed for {mid}: {e}")

        # Tally
        decisions.append(decision)
        counts[decision.action.value] += 1
        if len(examples[decision.action.value]) < 5:
            examples[decision.action.value].append(decision.message.subject)

    finished = datetime.now(timezone.utc)
    return RunReport(
        started_at=started,
        finished_at=finished,
        counts=dict(counts),
        examples=dict(examples),
        errors=errors,
        decisions=decisions,
    )


def decide_action(msg: MessageSummary, config: Dict[str, Any]) -> Decision:
    """Combine policy and classifier signals into a final `Decision`.

    Placeholder that keeps everything.
    """
    return Decision(message=msg, action=Action.KEEP, labels_to_add=[], reason="scaffold", by="policy")


def execute_decision(decision: Decision, config: Dict[str, Any], *, gateway: Optional[GmailGateway] = None, dry_run: bool = True) -> None:
    """Perform the chosen action on Gmail (archive/label/trash).

    Scaffold: no-op.
    """
    if dry_run or gateway is None:
        return None
    mid = decision.message.id
    if decision.action == Action.KEEP:
        if decision.labels_to_add:
            gateway.modify_labels(mid, add=decision.labels_to_add)
        return None
    if decision.action == Action.ARCHIVE:
        gateway.archive_message(mid)
        if decision.labels_to_add:
            gateway.modify_labels(mid, add=decision.labels_to_add)
        return None
    if decision.action == Action.TRASH:
        gateway.trash_message(mid)
        return None
    if decision.action == Action.LABEL:
        if decision.labels_to_add:
            gateway.modify_labels(mid, add=decision.labels_to_add)
        return None
    return None
