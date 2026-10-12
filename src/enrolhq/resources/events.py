"""Events resource (staff-side)."""

import datetime as dt
from typing import Any, Dict, List, Optional, Union

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource

TimeLike = Union[str, dt.time, Dict[str, Any]]

#: ``after_submit_settings.action`` values valid for events.
AFTER_SUBMIT_ACTIONS = (
    "SHOW_CONFIRMATION",
    "REDIRECT_TO_PARENT_DASHBOARD",
    "REDIRECT_TO_CUSTOM_FORM",
    "REDIRECT_TO_URL",
)


def json_time(value: Optional[TimeLike]) -> Optional[Dict[str, str]]:
    """Convert a time to EnrolHQ's session time object, ``{"HH": "09", "mm": "30"}``.

    Session ``start_time``/``end_time`` are JSON objects, not strings. The
    server returns zero-padded strings and accepts strings or ints, so this
    emits the same shape it returns — a GET -> PUT round trip compares equal.

    Accepts ``"09:30"``, :class:`datetime.time`, an ``{"HH", "mm"}`` object
    (ints or strings) or ``None``.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        hours, minutes = int(value["HH"]), int(value["mm"])
    elif isinstance(value, dt.time):
        hours, minutes = value.hour, value.minute
    else:
        h, _, m = str(value).strip().partition(":")
        hours, minutes = int(h), int(m or 0)
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError(f"Invalid time: {value!r}")
    return {"HH": f"{hours:02d}", "mm": f"{minutes:02d}"}


def session(
    name: str,
    date: Union[str, dt.date],
    start_time: TimeLike,
    end_time: Optional[TimeLike] = None,
    *,
    capacity: int,
    registrations_limit: Optional[int] = None,
    is_session_enabled: bool = True,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an event session payload.

    Dates and times are wall-clock values in the school's timezone (set it
    with ``client.school.set_region`` before creating events).

    Args:
        name: Session name shown to families, e.g. ``"Tuesday 9am tour"``.
        date: ``"YYYY-MM-DD"`` or a :class:`datetime.date`.
        start_time: ``"HH:MM"``, :class:`datetime.time` or ``{"HH", "mm"}``.
        end_time: Same forms, or ``None`` for no end time.
        capacity: Maximum attendees across all bookings.
        registrations_limit: Maximum number of bookings (families), or
            ``None`` for no limit.
        session_id: The existing session's ``id`` when updating an event —
            sessions sent without an id are created, and existing sessions
            missing from an update are deleted.
    """
    payload: Dict[str, Any] = {
        "name": name,
        "date": date.isoformat() if isinstance(date, dt.date) else date,
        "start_time": json_time(start_time),
        "end_time": json_time(end_time),
        "capacity": capacity,
        "registrations_limit": registrations_limit,
        "is_session_enabled": is_session_enabled,
    }
    if session_id:
        payload["id"] = session_id
    return payload


class EventsResource(BaseResource):
    """CRUD operations on staff events.

    Event payload notes (``staff-events/``):

    - ``kind`` is an event kind id (see ``client.event_settings``), not an
      enum; ``campus`` is a campus id.
    - ``slug`` and ``after_submit_settings`` keys must always be present.
      On create send ``slug=""`` and the server generates one;
      ``after_submit_settings=None`` uses the default confirmation.
      :meth:`create` fills both in when missing.
    - ``sessions`` are nested and replaced wholesale on update — keep
      existing sessions by sending their ``id`` (see :func:`session`).
    - ``image`` is a base64 data URI (:func:`enrolhq.files.image_data_uri`),
      write-only; the GET returns ``image_src``. Omit it to keep the image.
    - There is no published flag: an event is visible when it has an enabled
      session and ``is_unlisted`` is false.

    Requires the ``*_event`` permissions (Registrar role or superuser).
    """

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through all staff events.

        Filters: ``end_datetime_gte``, ``end_datetime_lt``, ``search`` (name
        prefix), ``ordering``.
        """
        return self._list("staff-events/", params=filters, page_size=page_size)

    def list_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of staff events."""
        return self._list_page(
            "staff-events/", params=filters, page=page, page_size=page_size
        )

    def get(self, event_id: str) -> Dict[str, Any]:
        """Get a single event by ID."""
        return self._get(f"staff-events/{event_id}/")

    def find(self, name: str) -> Optional[Dict[str, Any]]:
        """Return the first event whose name matches *name* exactly, or ``None``."""
        for event in self.list(search=name):
            if event.get("name") == name:
                return event
        return None

    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new event.

        ``slug`` defaults to ``""`` (server-generated) and
        ``after_submit_settings`` to ``None`` (default confirmation).
        """
        payload = {"slug": "", "after_submit_settings": None, **data}
        return self._post("staff-events/", json=payload)

    def update(self, event_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an event (full PUT).

        Send the current ``slug``, keep sessions by ``id`` and omit ``image``
        to keep the current one. ``after_submit_settings`` defaults to
        ``None`` when missing.
        """
        payload = {"after_submit_settings": None, **data}
        return self._put(f"staff-events/{event_id}/", json=payload)

    def delete(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Delete an event (400 if it has bookings)."""
        return self._delete(f"staff-events/{event_id}/")

    def preview(self, **params: Any) -> Any:
        """Preview upcoming events (``staff-events-preview/``)."""
        params.setdefault("page_size", 1000)
        resp = self._http.get(self._url("staff-events-preview/"), params=params)
        return resp.json()
