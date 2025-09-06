from __future__ import annotations

from typing import List, Tuple, Optional, Dict, Any

from .models import MessageSummary, Decision, Action


def is_whitelisted(
    msg: MessageSummary, whitelist_senders: List[str], whitelist_domains: List[str]
) -> bool:
    """Return True if the message sender/domain is explicitly whitelisted."""
    sender = (msg.from_addr or "").strip().lower()
    if sender in {s.strip().lower() for s in whitelist_senders}:
        return True
    # Extract domain from email address and compare allowing subdomains.
    if "@" in sender:
        domain = sender.split("@", 1)[1]
        for dom in whitelist_domains:
            d = (dom or "").strip().lower()
            if not d:
                continue
            if domain == d or domain.endswith("." + d):
                return True
    return False


def is_protected(msg: MessageSummary, never_touch_labels: List[str]) -> bool:
    """Return True if the message is starred/important or has protected labels."""
    protected = {l.upper() for l in never_touch_labels}
    labels_upper = {l.upper() for l in msg.labels}
    return bool(protected & labels_upper)


def fast_heuristics(msg: MessageSummary) -> Tuple[Optional[Action], Optional[str]]:
    """Apply quick non-LLM rules.

    Detect newsletters via unsubscribe hints and common patterns.
    Detect obvious spam by naive subject keywords.
    """
    subj = (msg.subject or "").lower()
    # Heuristic: look for unsubscribe tokens in body preview/snippet.
    body_hint_source = (msg.body_preview or msg.snippet or "").lower()
    if ("list-unsubscribe" in body_hint_source) or ("unsubscribe" in body_hint_source):
        return Action.ARCHIVE, "unsubscribe hint"
    spammy = ["win money", "free!!!", "urgent action required", "loan approved"]
    if any(k in subj for k in spammy):
        return Action.TRASH, "spammy subject"
    return None, None


def policy_decide(msg: MessageSummary, config: Dict[str, Any]) -> Optional[Decision]:
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
