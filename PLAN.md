# Gmail Smart Cleaner – Project Plan

## Goals
- Reduce inbox noise safely using rules + LLM guidance.
- Run daily at 22:00, inside Docker.
- Produce and email a Markdown report of actions.
- Default to reversible actions (label/trash) with strong safety rails.

## Non‑Goals (initial phase)
- No permanent deletion without a quarantine window.
- No multi‑user SaaS; single Gmail account focus.
- No external DB dependencies beyond a lightweight local store.

## High‑Level Architecture
- Scheduler: Triggers daily run at 22:00 local time.
- Engine: Orchestrates fetching, classifying, deciding, and executing actions.
- Gmail Client: Authenticates and performs Gmail API operations.
- Policies: Safety rules, whitelists/blacklists, and guardrails.
- Classifier: LLM + heuristics to decide archive/trash/keep.
- Storage: Persists last run timestamp and audit log (SQLite or file‑based).
- Reporter: Builds Markdown report and emails it to you; also saves to disk.
- Config: Centralizes settings, thresholds, labels, schedules.

### Data Flow
1. At 22:00, scheduler invokes `engine.process_inbox()`.
2. Gmail client lists candidate messages (e.g., since last run or past N hours) and fetches summaries + limited content.
3. Policies run first for quick, safe decisions (e.g., whitelist keep, mailing list auto‑archive). 
4. For remaining uncertain messages, the classifier calls an LLM with minimal, privacy‑aware context to suggest an action.
5. Engine executes reversible actions (apply labels, mark as read, move to Trash if configured), and logs decisions.
6. Reporter compiles a Markdown report (counts, examples, senders) and emails it; report is also saved under `reports/YYYY‑MM‑DD.md`.

### Safety & Privacy
- Never touch starred, important, or from whitelisted senders/domains.
- Default mode: quarantine by applying `label:ToReview` or moving to Trash (not permanent delete).
- Optional "aging" deletion: only permanently delete items in Trash older than X days.
- Redact or truncate message bodies before sending to the LLM; prefer headers, subject, and snippets.
- Configurable dry‑run mode that only reports proposed actions.

## Tech Choices
- Language: Python 3.13+
- Gmail API: OAuth2 with offline access (`gmail.modify` scope).
- LLM: OpenAI GPT (configurable model, e.g., `gpt-4o-mini`), temperature low.
- Scheduler: APScheduler inside the app, or container `cron`—start with APScheduler for portability.
- Storage: SQLite (via `sqlite3` or `sqlmodel`) for audit + last run; minimal JSON alternative supported.
- Config: `config.yaml` loaded via `pydantic-settings` or plain `yaml`.
- Packaging: `pyproject.toml`; runnable via `python -m cleanmail.main`.
- Docker: Multi‑stage build, non‑root user, timezone support, bind‑mounted volume for tokens/db.

## Repository Structure
```
.
├── PLAN.md
├── README.md                  # short overview + setup later
├── config.example.yaml        # documented example configuration
├── reports/                   # markdown reports (gitignored)
├── data/                      # tokens, sqlite db (gitignored)
├── src/
│   └── cleanmail/
│       ├── __init__.py
│       ├── main.py            # CLI entrypoint
│       ├── scheduler.py
│       ├── engine.py
│       ├── gmail_client.py
│       ├── classifier.py
│       ├── policies.py
│       ├── reporter.py
│       ├── storage.py
│       ├── config.py
│       ├── logging_setup.py
│       └── models.py
├── tests/                     # pytest tests (later)
├── Dockerfile
└── pyproject.toml
```

## Configuration (proposed)
```yaml
# config.yaml
schedule:
  time: "22:00"
  timezone: "America/New_York"  # set your TZ

mode:
  dry_run: true               # start safe; switch to false after validation
  action: "trash"             # one of: label, archive, trash
  quarantine_label: "ToReview"
  preserve_days: 7            # only permanently delete after N days (optional)

limits:
  max_messages_per_run: 500
  fetch_window_hours: 24

llm:
  provider: "openai"
  model: "gpt-4o-mini"
  temperature: 0.0
  max_body_chars: 2000        # limit text sent to LLM
  system_prompt_path: "prompts/classifier_system.md"

safety:
  whitelist_senders: ["boss@company.com", "alerts@bank.com"]
  whitelist_domains: ["company.com"]
  never_touch_labels: ["STARRED", "IMPORTANT"]
  denylist_senders: ["noreply@annoying.com"]

report:
  recipient: "you@example.com"
  save_dir: "reports"

secrets:
  openai_api_key_env: "OPENAI_API_KEY"
  google_credentials_dir: "data/google"  # store token.json/credentials.json here
  sqlite_path: "data/cleanmail.db"
```

## Core Models (Python typing)
```python
# src/cleanmail/models.py
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
    category: str            # e.g., spam, promo, newsletter, personal, receipt
    confidence: float        # 0..1
    suggested_action: Action
    rationale: Optional[str] = None

@dataclass
class Decision:
    message: MessageSummary
    action: Action
    labels_to_add: List[str]
    reason: str
    by: str                  # "policy" or "llm"

@dataclass
class RunReport:
    started_at: datetime
    finished_at: datetime
    counts: Dict[str, int]   # action => count
    examples: Dict[str, List[str]]  # action => list of subjects
    errors: List[str]
    decisions: List[Decision]
```

## Module Design: Functions and Docstrings

### src/cleanmail/config.py
```python
def load_config(path: str | None = None) -> dict:
    """Load and validate application configuration.

    - Reads YAML from `path` or default `config.yaml` if None.
    - Applies defaults and basic validation (e.g., schedule format, enums).
    - Expands relative paths (reports dir, credentials dir, sqlite path).

    Returns a nested dict suitable for injection into components.
    """
```

### src/cleanmail/logging_setup.py
```python
def setup_logging(verbosity: int = 0) -> None:
    """Configure structured logging for the application.

    - Sets log level based on verbosity.
    - Configures console handler and optional file handler.
    - Adds useful context (run id, timestamps) to log records.
    """
```

### src/cleanmail/gmail_client.py
```python
from typing import Iterable
from .models import MessageSummary

def authenticate(credentials_dir: str) -> None:
    """Ensure Gmail OAuth2 tokens are available and valid.

    - Uses `credentials.json` for client secrets and persists `token.json`.
    - Requests `gmail.modify` scope with offline access for unattended runs.
    - Refreshes tokens as needed and caches session on disk.
    """

def list_messages(after: str | None = None,
                  max_results: int = 500,
                  query: str | None = None) -> Iterable[str]:
    """List message IDs matching the search.

    - `after`: RFC3339 or Gmail search operator (e.g., `newer_than:1d`).
    - `query`: additional Gmail search query (e.g., `-in:chats`).
    - Returns an iterable of message IDs.
    """

def get_message(message_id: str, include_body: bool = True) -> MessageSummary:
    """Fetch a single message summary and limited body preview.

    - Extracts headers (From, To, Cc, Subject, Date), labels, snippet.
    - Optionally includes a truncated plain‑text body for classification.
    - Returns a `MessageSummary`.
    """

def modify_labels(message_id: str, add: list[str] | None = None, remove: list[str] | None = None) -> None:
    """Add and/or remove labels for a message.

    - Creates missing labels if necessary (idempotent behavior).
    - Used for quarantine (e.g., `ToReview`) and bookkeeping labels.
    """

def archive_message(message_id: str) -> None:
    """Archive a message by removing `INBOX` label (keeps it searchable)."""

def trash_message(message_id: str) -> None:
    """Move a message to Trash (reversible within Gmail retention window)."""

def send_email(to: str, subject: str, markdown_body: str) -> None:
    """Send an email via Gmail.

    - Accepts Markdown body; renders to plain text and inline HTML as needed.
    - Sends the daily report to the configured recipient.
    """
```

### src/cleanmail/policies.py
```python
from .models import MessageSummary, Decision, Action

def is_whitelisted(msg: MessageSummary, whitelist_senders: list[str], whitelist_domains: list[str]) -> bool:
    """Return True if the message sender/domain is explicitly whitelisted."""

def is_protected(msg: MessageSummary, never_touch_labels: list[str]) -> bool:
    """Return True if the message is starred/important or has protected labels."""

def fast_heuristics(msg: MessageSummary) -> tuple[Action | None, str | None]:
    """Apply quick non‑LLM rules.

    - Detect mailing lists/newsletters via headers (List‑Unsubscribe) and common patterns.
    - Detect obvious spam via sender patterns and bad subjects.
    - Return `(action, reason)` or `(None, None)` if undecided.
    """

def policy_decide(msg: MessageSummary, config: dict) -> Decision | None:
    """Return a `Decision` if a policy can confidently decide; otherwise None.

    - Enforces safety: whitelists, protected labels, age limits, etc.
    - Prefers ARCHIVE or LABEL over TRASH when uncertain.
    """
```

### src/cleanmail/classifier.py
```python
from .models import MessageSummary, Classification, Action

def classify_with_llm(msg: MessageSummary, config: dict) -> Classification:
    """Call the configured LLM to classify the message.

    - Sends minimal context: sender, subject, snippet, and truncated body.
    - System prompt instructs conservative actions and privacy constraints.
    - Returns a `Classification` with category, confidence, and suggested action.
    """

def decide_from_classification(msg: MessageSummary, cls: Classification, config: dict) -> tuple[Action, str]:
    """Convert an LLM classification into a concrete action and reason.

    - Applies confidence thresholds and action caps (e.g., favor ARCHIVE over TRASH).
    - Returns `(action, reason)`.
    """
```

### src/cleanmail/engine.py
```python
from datetime import datetime
from .models import RunReport, Decision

def process_inbox(now: datetime, config: dict) -> RunReport:
    """Run the end‑to‑end cleaning workflow and produce a report.

    Steps:
    1) Authenticate Gmail and load last run timestamp.
    2) List candidate messages (since last run / fetch window).
    3) For each message: apply policies; if undecided, call LLM classifier.
    4) In dry‑run, only record proposed actions; otherwise execute them.
    5) Collect counts, examples, and errors into `RunReport`.
    6) Persist audit records and new last run timestamp.
    """

def decide_action(msg, config: dict) -> Decision:
    """Combine policy and classifier signals into a final `Decision`.

    - Policy decision wins if decisive; otherwise consult LLM.
    - Always enforce safety rails before returning the final action.
    """


def execute_decision(decision: Decision, config: dict) -> None:
    """Perform the chosen action on Gmail (archive/label/trash).

    - Idempotent operations; handles transient API errors with retries.
    - Records results in storage/audit.
    """
```

### src/cleanmail/reporter.py
```python
from .models import RunReport

def build_markdown_report(report: RunReport, config: dict) -> str:
    """Render a human‑friendly Markdown report from a `RunReport`.

    - Includes summary counts, sample subjects, top senders, and errors.
    - Adds footers with configuration snapshot (mode, thresholds, version).
    """

def save_report(markdown: str, path: str) -> str:
    """Save the Markdown report to disk and return the final path."""

def email_report(markdown: str, recipient: str, gmail_sender_config: dict) -> None:
    """Send the Markdown report via Gmail to the recipient."""
```

### src/cleanmail/storage.py
```python
from datetime import datetime
from typing import Iterable
from .models import Decision

def get_last_run(db_path: str) -> datetime | None:
    """Return the timestamp of the last successful run, if available."""

def set_last_run(db_path: str, ts: datetime) -> None:
    """Persist the timestamp of the latest completed run."""

def append_audit_records(db_path: str, decisions: Iterable[Decision]) -> None:
    """Append decisions to an immutable audit log for traceability."""
```

### src/cleanmail/scheduler.py
```python
from datetime import time

def start_scheduler(daily_time: time, timezone: str, runner) -> None:
    """Start the APScheduler that invokes `runner` at the configured time.

    - `runner` is a callable that executes one full inbox processing run.
    - Scheduler runs in the foreground; container handles lifecycle.
    """

def run_once() -> None:
    """Convenience entry for a single immediate processing run (no schedule)."""
```

### src/cleanmail/main.py
```python
def main() -> None:
    """CLI entrypoint.

    - Loads config and initializes logging.
    - Supports `run` (one‑off), and `serve` (start scheduler) subcommands.
    - Exits non‑zero on failures and logs actionable diagnostics.
    """
```

## Docker & Deployment
- Bind‑mount `data/` for tokens and SQLite, and `reports/` for outputs.
- Set timezone via `TZ` env var and install tzdata in the image.
- Provide `OPENAI_API_KEY` via Docker secrets/env; never bake into image.
- Healthcheck: optional simple `python -m cleanmail.main --healthcheck`.

### Dockerfile (outline)
```
FROM python:3.11-slim AS base
# install system deps: libffi, tzdata, etc.
# create non-root user
# copy pyproject + install deps
# copy src/
# set ENV for TZ, PYTHONUNBUFFERED, etc.
# CMD ["python", "-m", "cleanmail.main", "serve"]
```

## Reporting Format (Markdown)
- Header: date/time, duration, counts by action.
- Sections:
  - Kept (policy/whitelist reasons)
  - Archived (top senders + sample subjects)
  - Trashed (quarantine) with reversible note
  - Errors/Skipped (with reasons)
- Footer: configuration snapshot (mode, thresholds), app version.

## Open Questions for You
- Scope of actions: Is “trash (reversible)” acceptable as the default, or should we start with “label only” quarantine for a week?
- Whitelist: Which senders/domains must never be touched? Any mailing lists to always archive?
- Model/cost: OK to use OpenAI API (`gpt-4o-mini`) to keep costs low? Any monthly budget limits?
- Privacy: Are there senders/domains whose content must never be sent to an LLM (policy‑only)?
- Timezone: Confirm the timezone for the 22:00 run.
- Initial mode: Start with `dry_run: true` for 3–7 days to build confidence?
- Report recipient: Which email should receive the nightly report?
- Permanent deletion: Should we ever auto‑purge items after N days in Trash, or leave that manual?

## Next Steps (after confirmation)
1) Scaffold repo (+ `pyproject.toml`, `config.example.yaml`).
2) Implement Gmail OAuth + client operations.
3) Add policies and conservative classifier prompt.
4) Build engine + reporting, then Docker + scheduler.
5) Run in dry‑run for a week, iterate thresholds, then enable trash.

```
This plan is intentionally conservative to protect important emails. We can tune aggressiveness as confidence grows.
```
