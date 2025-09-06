from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime


class Action(str, Enum):
    KEEP = "keep"
    ARCHIVE = "archive"
    TRASH = "trash"
    LABEL = "label"


@dataclass
class MessageSummary:
    id: str
    thread_id: str
    from_addr: str
    to_addrs: List[str]
    cc_addrs: List[str]
    subject: str
    snippet: str
    labels: List[str]
    date: datetime
    body_preview: Optional[str] = None


@dataclass
class Classification:
    category: str  # e.g., spam, promo, newsletter, personal, receipt
    confidence: float  # 0..1
    suggested_action: Action
    rationale: Optional[str] = None


@dataclass
class Decision:
    message: MessageSummary
    action: Action
    labels_to_add: List[str]
    reason: str
    by: str  # "policy" or "llm"


@dataclass
class RunReport:
    started_at: datetime
    finished_at: datetime
    counts: Dict[str, int]  # action => count
    examples: Dict[str, List[str]]  # action => list of subjects
    errors: List[str]
    decisions: List[Decision]

