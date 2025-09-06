"""Gmail API wrapper – function stubs to be implemented.

These functions abstract Gmail operations so the rest of the app can be
tested with in-memory stubs without touching the network.
"""
from __future__ import annotations

from typing import Iterable, List, Optional

from .models import MessageSummary


def authenticate(credentials_dir: str) -> None:
    """Ensure Gmail OAuth2 tokens are available and valid.

    - Uses `credentials.json` for client secrets and persists `token.json`.
    - Requests `gmail.modify` scope with offline access for unattended runs.
    - Refreshes tokens as needed and caches session on disk.
    """
    # TODO: Implement using google-auth and google-api-python-client
    return None


def list_messages(
    after: str | None = None,
    max_results: int = 500,
    query: str | None = None,
) -> Iterable[str]:
    """List message IDs matching the search.

    - `after`: RFC3339 or Gmail search operator (e.g., `newer_than:1d`).
    - `query`: additional Gmail search query (e.g., `-in:chats`).
    - Returns an iterable of message IDs.
    """
    # TODO: Implement API call; currently returns empty list for scaffold.
    return []


def get_message(message_id: str, include_body: bool = True) -> MessageSummary:
    """Fetch a single message summary and limited body preview.

    - Extracts headers (From, To, Cc, Subject, Date), labels, snippet.
    - Optionally includes a truncated plain-text body for classification.
    - Returns a `MessageSummary`.
    """
    # TODO: Implement
    raise NotImplementedError


def modify_labels(
    message_id: str,
    add: List[str] | None = None,
    remove: List[str] | None = None,
) -> None:
    """Add and/or remove labels for a message.

    - Creates missing labels if necessary (idempotent behavior).
    - Used for quarantine (e.g., `ToReview`) and bookkeeping labels.
    """
    # TODO: Implement
    return None


def archive_message(message_id: str) -> None:
    """Archive a message by removing `INBOX` label (keeps it searchable)."""
    # TODO: Implement
    return None


def trash_message(message_id: str) -> None:
    """Move a message to Trash (reversible within Gmail retention window)."""
    # TODO: Implement
    return None


def send_email(to: str, subject: str, markdown_body: str) -> None:
    """Send an email via Gmail.

    - Accepts Markdown body; renders to plain text and inline HTML as needed.
    - Sends the daily report to the configured recipient.
    """
    # TODO: Implement
    return None

