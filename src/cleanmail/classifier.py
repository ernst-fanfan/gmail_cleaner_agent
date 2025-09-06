from __future__ import annotations

from typing import Tuple

from .models import MessageSummary, Classification, Action


def classify_with_llm(msg: MessageSummary, config: dict) -> Classification:
    """Call the configured LLM to classify the message.

    Scaffold: returns a conservative default classification until implemented.
    """
    # Placeholder: default to ARCHIVE with low confidence
    return Classification(
        category="unknown",
        confidence=0.4,
        suggested_action=Action.ARCHIVE,
        rationale="scaffold default",
    )


def decide_from_classification(
    msg: MessageSummary, cls: Classification, config: dict
) -> tuple[Action, str]:
    """Convert an LLM classification into a concrete action and reason.

    Applies confidence thresholds and caps TRASH unless highly confident.
    """
    min_trash = float(config.get("llm", {}).get("min_trash_confidence", 0.85))
    action = cls.suggested_action
    if action == Action.TRASH and cls.confidence < min_trash:
        return Action.ARCHIVE, "low confidence; archived instead"
    return action, cls.rationale or cls.category

