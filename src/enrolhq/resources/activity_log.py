"""Activity log resource (the Comms Log on a student profile)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Union

from ..constants import ActivityKind
from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource

_KINDS = {k.value for k in ActivityKind}


class ActivityLogResource(BaseResource):
    """List, create and delete activity log entries."""

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
        activity_kind: Union[ActivityKind, str],
        description: str = "",
        *,
        occurred_at: Union[datetime, str, None] = None,
        attachment: Optional[str] = None,
        **extra: Any,
    ) -> Optional[Dict[str, Any]]:
        """Add an entry to a student profile's Comms Log.

        The entry's ``created_by`` is the staff user the API token belongs
        to. Creating an entry sends nothing to families.

        Args:
            student_profile_id: The student profile UUID.
            activity_kind: An :class:`~enrolhq.ActivityKind` (e.g.
                ``ActivityKind.PHONE_CALL``) or its string value.
            description: The entry's text.
            occurred_at: When the activity happened, as a timezone-aware
                datetime or an ISO 8601 string. Defaults to now. A naive
                datetime is rejected: the server would read it in the
                school's timezone, which is easy to get wrong in imports.
            attachment: Optional file as a data URI, e.g.
                ``file_data_uri("call-notes.pdf")``. Document types and
                ``.msg`` / ``.eml`` emails are accepted.
            **extra: Additional fields to include in the payload.

        Returns:
            The created entry, including its ``id``.

        Raises:
            ValueError: If *activity_kind* is not an ActivityKind value or
                *occurred_at* is a naive datetime.
        """
        kind = (
            activity_kind.value
            if isinstance(activity_kind, Enum)
            else str(activity_kind)
        )
        if kind not in _KINDS:
            raise ValueError(
                f"activity_kind {kind!r} is not one of: {', '.join(sorted(_KINDS))}"
            )
        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)
        if isinstance(occurred_at, datetime):
            if occurred_at.utcoffset() is None:
                raise ValueError(
                    "occurred_at must be timezone-aware, e.g. "
                    "datetime(..., tzinfo=ZoneInfo('Australia/Sydney'))"
                )
            occurred_at = occurred_at.isoformat()
        data: Dict[str, Any] = {
            "student_profile": student_profile_id,
            "activity_kind": kind,
            "description": description,
            "occurred_at": occurred_at,
            **extra,
        }
        if attachment is not None:
            data["attachment"] = attachment
        return self._post("activity-log/", json=data)

    def delete(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Delete an activity log entry by ID."""
        return self._delete(f"activity-log/{entry_id}/")
