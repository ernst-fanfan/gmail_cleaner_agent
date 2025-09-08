from __future__ import annotations

from typing import Iterable, Optional, Protocol, List

from .models import MessageSummary


class GmailGateway(Protocol):
    def authenticate(self, credentials_dir: str) -> None: ...

    def list_messages(
        self,
        after: Optional[str] = None,
        max_results: int = 500,
        query: Optional[str] = None,
    ) -> Iterable[str]: ...

    def get_message(self, message_id: str, include_body: bool = True) -> MessageSummary: ...

    def modify_labels(
        self, message_id: str, add: Optional[List[str]] = None, remove: Optional[List[str]] = None
    ) -> None: ...

    def archive_message(self, message_id: str) -> None: ...

    def trash_message(self, message_id: str) -> None: ...

    def send_email(self, to: str, subject: str, markdown_body: str) -> None: ...

