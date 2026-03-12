"""Notes resource."""

from typing import Any, Dict, Optional

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class NotesResource(BaseResource):
    """List and add notes on student profiles."""

    def list(
        self, student_profile_id: str, *, page_size: int = 1000, **filters: Any
    ) -> PaginatedIterator:
        """List all notes for a student profile."""
        filters["student_profile"] = student_profile_id
        return self._list("notes/", params=filters, page_size=page_size)

    def list_page(
        self,
        student_profile_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        **filters: Any,
    ) -> PaginatedResponse:
        """Fetch a single page of notes."""
        filters["student_profile"] = student_profile_id
        return self._list_page(
            "notes/", params=filters, page=page, page_size=page_size
        )

    def create(
        self,
        student_profile_id: str,
        text: str,
        **extra: Any,
    ) -> Optional[Dict[str, Any]]:
        """Create a note on a student profile.

        Args:
            student_profile_id: The student profile UUID.
            text: Note text content.
            **extra: Additional fields to include in the payload.
        """
        data = {"student_profile": student_profile_id, "text": text, **extra}
        return self._post("notes/", json=data)
