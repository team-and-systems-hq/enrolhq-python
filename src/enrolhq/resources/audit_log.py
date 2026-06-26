"""Audit log resource (change history)."""

from typing import Any, Optional

from ..pagination import CursorPaginatedIterator
from .base import BaseResource


class AuditLogResource(BaseResource):
    """Read the audit / change log for a student profile or parent.

    The ``audit/log/`` endpoint is read-only and uses cursor pagination. Each
    entry has the shape::

        {
            "changes": ["... human-readable change description ..."],
            "updated_at": "2026-06-25T18:53:28.494243+10:00",
            "updated_by": "",
        }

    Filter by exactly one subject — ``student_profile_id`` or ``parent_id``.
    """

    def list(
        self,
        *,
        student_profile_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        page_size: int = 25,
        **filters: Any,
    ) -> CursorPaginatedIterator:
        """List audit log entries, auto-following cursor pages.

        Args:
            student_profile_id: Filter to a student profile's audit log.
            parent_id: Filter to a parent's audit log.
            page_size: Records fetched per request.
            **filters: Additional query params (e.g. another subject id).

        Returns:
            A :class:`CursorPaginatedIterator` yielding entries across all pages.
        """
        if student_profile_id:
            filters["student_profile"] = student_profile_id
        if parent_id:
            filters["parent"] = parent_id
        if not filters:
            raise ValueError(
                "Provide student_profile_id, parent_id, or a filter"
            )
        return self._list_cursor("audit/log/", params=filters, page_size=page_size)
