"""Email log resource."""

from typing import Any

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class EmailLogResource(BaseResource):
    """Read-only access to email history."""

    def list(
        self, student_profile_id: str, *, page_size: int = 1000, **filters: Any
    ) -> PaginatedIterator:
        """List email log entries for a student profile."""
        filters["student_profile"] = student_profile_id
        return self._list("email-log/", params=filters, page_size=page_size)

    def list_page(
        self,
        student_profile_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        **filters: Any,
    ) -> PaginatedResponse:
        """Fetch a single page of email log entries."""
        filters["student_profile"] = student_profile_id
        return self._list_page(
            "email-log/", params=filters, page=page, page_size=page_size
        )
