from __future__ import annotations

from typing import List, Tuple, Optional

from .models import MessageSummary, Decision, Action


def is_whitelisted(
    msg: MessageSummary, whitelist_senders: List[str], whitelist_domains: List[str]
) -> bool:
    """Return True if the message sender/domain is explicitly whitelisted."""
    sender = (msg.from_addr or "").lower()
    if sender in {s.lower() for s in whitelist_senders}:
        return True
    for dom in whitelist_domains:
        if sender.endswith("@" + dom.lower()) or sender.endswith("." + dom.lower()):
            return True
    return False


def is_protected(msg: MessageSummary, never_touch_labels: List[str]) -> bool:
    """Return True if the message is starred/important or has protected labels."""
    protected = {l.upper() for l in never_touch_labels}
    labels_upper = {l.upper() for l in msg.labels}
    return bool(protected & labels_upper)


def fast_heuristics(msg: MessageSummary) -> tuple[Action | None, str | None]:
    """Apply quick non-LLM rules.

    Detect newsletters via List-Unsubscribe and common patterns.
    Detect obvious spam by naive subject keywords.
    """
    subj = (msg.subject or "").lower()
    if "list-unsubscribe" in msg.snippet.lower():
        return Action.ARCHIVE, "newsletter header"
    spammy = ["win money", "free!!!", "urgent action required", "loan approved"]
    if any(k in subj for k in spammy):
        return Action.TRASH, "spammy subject"
    return None, None


def policy_decide(msg: MessageSummary, config: dict) -> Decision | None:
    """Return a `Decision` if a policy can confidently decide; otherwise None.

    Enforces safety: whitelists, protected labels.
    Prefers ARCHIVE or LABEL over TRASH when uncertain.
    """
    saf = config.get("safety", {})
    wl = saf.get("whitelist_senders", [])
    wld = saf.get("whitelist_domains", [])
    ntl = saf.get("never_touch_labels", [])

    if is_whitelisted(msg, wl, wld):
        return Decision(msg, Action.KEEP, [], "whitelisted", by="policy")
    if is_protected(msg, ntl):
        return Decision(msg, Action.KEEP, [], "protected label", by="policy")

    action, reason = fast_heuristics(msg)
    if action:
        if action == Action.TRASH:
            # downgrade to ARCHIVE for safety at policy level
            return Decision(msg, Action.ARCHIVE, [], f"{reason} (conservative)", by="policy")
        return Decision(msg, action, [], reason or "heuristic", by="policy")
    return None

