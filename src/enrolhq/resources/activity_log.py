"""Activity log resource."""

from typing import Any, Dict, Optional

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class ActivityLogResource(BaseResource):
    """List and create activity log entries."""

    def list(
        self, student_profile_id: str, *, page_size: int = 1000, **filters: Any
    ) -> PaginatedIterator:
        """List activity log entries for a student profile."""
        filters["student_profile"] = student_profile_id
        return self._list("activity-log/", params=filters, page_size=page_size)

    def list_page(
        self,
        student_profile_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        **filters: Any,
    ) -> PaginatedResponse:
        """Fetch a single page of activity log entries."""
        filters["student_profile"] = student_profile_id
        return self._list_page(
            "activity-log/", params=filters, page=page, page_size=page_size
        )

    def create(
        self,
        student_profile_id: str,
        text: str,
        **extra: Any,
    ) -> Optional[Dict[str, Any]]:
        """Create an activity log entry.

        Args:
            student_profile_id: The student profile UUID.
            text: Activity log text content.
            **extra: Additional fields to include in the payload.
        """
        data = {"student_profile": student_profile_id, "text": text, **extra}
        return self._post("activity-log/", json=data)
