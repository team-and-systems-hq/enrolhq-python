"""Interview set-up: settings, types, interviewers, locations and availability."""

from typing import Any, Dict, List, Optional

from ..pagination import PaginatedIterator
from .base import BaseResource, deep_merge
from .events import TimeLike, json_time


class InterviewsResource(BaseResource):
    """Interview set-up (the *Interviews* menu in the dashboard).

    Booking or cancelling an interview for a student is on
    ``client.applications``. This resource is the school's side:

    * **Settings** (``interview/settings/``): the default interview length,
      whether and when parents can book or cancel, how many slots they are
      shown, the reminder hours and the school's ``interview_types``.
    * **Interviewers** (``interview/interviewers/``): the staff who interview.
    * **Locations** (``school-locations/``): the rooms an interview is in.
    * **Availability** (``interview/availabilities/``): a block of time on one
      date when one interviewer can interview. EnrolHQ cuts the block into
      slots of ``interview_duration_minutes``, and parents (or staff) book a
      slot.

    Reading needs any staff user. Writing needs the matching interview
    permissions (Registrar role, school Admin or superuser).
    """

    def get_settings(self) -> Dict[str, Any]:
        """Get the interview settings, including ``interview_types``."""
        return self._get("interview/settings/")

    def update_settings(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Replace the interview settings (full PUT). Start from :meth:`get_settings`.

        ``interview_types`` is replaced wholesale: a type without an ``id`` is
        created and a type left out is deleted (400 if an availability or an
        interview uses it; those have ``is_removable`` false). At least one
        type is required. ``parents_interview_duration`` may not be longer
        than ``interview_duration_minutes``, and
        ``allow_to_book_starting_from_x_days_before`` (``None`` for no limit)
        must be more than ``allow_to_book_up_to_x_days_before``.
        """
        return self._put("interview/settings/", json=data)

    def update_settings_fields(
        self, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Change some settings: GET, deep-merge *changes*, PUT the result."""
        return self._read_modify_write("interview/settings/", changes)

    def types(self) -> List[Dict[str, Any]]:
        """List interview types (``{id, name, is_removable}``)."""
        return list(self._list("interview/types/", page_size=1000))

    def ensure_types(self, names: List[str]) -> List[Dict[str, Any]]:
        """Make sure interview types with these names exist; return all types.

        Existing types are matched by name (case-insensitive) and kept.
        Nothing is written when every name already exists.
        """
        settings = self.get_settings()
        current = settings.get("interview_types") or []
        have = {(row.get("name") or "").strip().lower() for row in current}
        missing = []
        for name in names:
            wanted = name.strip()
            if wanted.lower() not in have:
                have.add(wanted.lower())
                missing.append({"name": wanted})
        if not missing:
            return current
        saved = self.update_settings({**settings, "interview_types": [*current, *missing]})
        return (saved or {}).get("interview_types") or self.types()

    def interviewers(self) -> List[Dict[str, Any]]:
        """List interviewers.

        Each is ``{id, name, email, default_location, calendar,
        is_hide_interviewer_name, is_interview_booking_enabled}``.
        ``default_location`` is ``{id, name}`` or ``None`` and ``calendar``
        is the interviewer's private calendar feed address.
        """
        return list(self._list("interview/interviewers/", page_size=1000))

    def get_interviewer(self, interviewer_id: str) -> Dict[str, Any]:
        """Get one interviewer."""
        return self._get(f"interview/interviewers/{interviewer_id}/")

    def find_interviewers(self, name: str) -> List[Dict[str, Any]]:
        """Return the interviewers with this name (case-insensitive).

        Names are not unique, so check for exactly one before changing it.
        """
        needle = name.strip().lower()
        return [
            row
            for row in self.interviewers()
            if (row.get("name") or "").strip().lower() == needle
        ]

    def create_interviewer(
        self,
        name: str,
        email: str,
        *,
        default_location: Optional[str] = None,
        is_hide_interviewer_name: bool = False,
        is_interview_booking_enabled: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Create an interviewer.

        ``default_location`` is a location id. ``is_hide_interviewer_name``
        hides the name from parents, and ``is_interview_booking_enabled``
        false stops parents booking this interviewer themselves.
        """
        return self._post(
            "interview/interviewers/",
            json={
                "name": name,
                "email": email,
                "default_location": _location(default_location),
                "is_hide_interviewer_name": is_hide_interviewer_name,
                "is_interview_booking_enabled": is_interview_booking_enabled,
            },
        )

    def update_interviewer(
        self, interviewer_id: str, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Change some interviewer fields: GET, merge *changes*, PUT.

        ``default_location`` in *changes* is a location id or ``None``.
        """
        changes = dict(changes)
        current = self.get_interviewer(interviewer_id)
        if "default_location" in changes:
            current["default_location"] = _location(changes.pop("default_location"))
        return self._put(
            f"interview/interviewers/{interviewer_id}/",
            json=deep_merge(current, changes),
        )

    def delete_interviewer(self, interviewer_id: str, new_interviewer: str) -> None:
        """Delete an interviewer, moving their interviews and availability.

        The server needs another interviewer's id to take over.
        """
        self._http.delete(
            self._url(f"interview/interviewers/{interviewer_id}/"),
            json={"new_interviewer": new_interviewer},
        )

    def locations(self) -> List[Dict[str, Any]]:
        """List school locations (``{id, name, hint_text, hint_image, campus}``)."""
        return list(self._list("school-locations/", page_size=1000))

    def create_location(
        self, name: str, *, campus: Optional[str] = None, hint_text: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Create a location. Names are unique within the school.

        ``campus`` is a campus id and ``hint_text`` tells parents how to find
        the room. The API has no way to delete a location.
        """
        return self._post(
            "school-locations/",
            json={"name": name, "campus": campus, "hint_text": hint_text},
        )

    def update_location(
        self, location_id: str, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Change a location's ``name``, ``campus`` or ``hint_text``.

        The location's image is left as it is.
        """
        current = self._get(f"school-locations/{location_id}/")
        current.pop("hint_image", None)
        return self._put(
            f"school-locations/{location_id}/", json=deep_merge(current, changes)
        )

    def ensure_location(self, name: str) -> Dict[str, Any]:
        """Return the location with this name, creating it if missing."""
        wanted = name.strip()
        for row in self.locations():
            if (row.get("name") or "").strip().lower() == wanted.lower():
                return row
        return self.create_location(wanted) or {}

    def availabilities(
        self, *, page_size: int = 100, **filters: Any
    ) -> PaginatedIterator:
        """Auto-paginate through availability blocks, newest date first.

        Filters: ``interviewer`` (an id), ``date`` (comma-separated dates),
        ``date_gte``, ``date_lt`` and ``ordering`` (``date``, ``-date``,
        ``start_time``, ``-start_time``). Each row has ``interviewer`` (an
        id), ``location`` (``{id, name}``), ``date``, ``start_time`` and
        ``end_time`` (``{"HH", "mm"}`` objects), ``types`` (ids),
        ``interview_duration_minutes``, ``parents_interview_duration``,
        ``online_meeting_link``, ``meeting_instructions`` and
        ``has_bookings``.
        """
        return self._list(
            "interview/availabilities/", params=filters, page_size=page_size
        )

    def get_availability(self, availability_id: str) -> Dict[str, Any]:
        """Get one availability block."""
        return self._get(f"interview/availabilities/{availability_id}/")

    def create_availability(
        self,
        *,
        interviewer: str,
        location: str,
        date: str,
        start_time: TimeLike,
        end_time: TimeLike,
        types: List[str],
        interview_duration_minutes: int,
        parents_interview_duration: int,
        online_meeting_link: str = "",
        meeting_instructions: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Create one availability block and its bookable slots.

        ``interviewer``, ``location`` and ``types`` are ids, ``date`` is
        ``YYYY-MM-DD`` and the times take anything :func:`~enrolhq.json_time`
        accepts, such as ``"09:00"``. The block must be at least one
        interview long, and at least one type is required. The server does
        not stop two blocks for the same interviewer overlapping. The
        response leaves out ``has_bookings``.
        """
        return self._post(
            "interview/availabilities/",
            json={
                "interviewer": interviewer,
                "location": {"id": location},
                "date": date,
                "start_time": json_time(start_time),
                "end_time": json_time(end_time),
                "types": list(types),
                "interview_duration_minutes": interview_duration_minutes,
                "parents_interview_duration": parents_interview_duration,
                "online_meeting_link": online_meeting_link,
                "meeting_instructions": meeting_instructions,
            },
        )

    def update_availability(
        self, availability_id: str, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Change an availability block: GET, merge *changes*, PUT.

        Only ``types``, ``online_meeting_link``, ``meeting_instructions`` and
        ``parents_interview_duration`` can change. The server ignores the
        rest, so to move a block delete it and create another.
        """
        current = self.get_availability(availability_id)
        return self._put(
            f"interview/availabilities/{availability_id}/",
            json=deep_merge(current, changes),
        )

    def delete_availability(self, availability_id: str) -> None:
        """Delete an availability block. 400 if a slot in it is booked."""
        self._delete(f"interview/availabilities/{availability_id}/")


def _location(location_id: Optional[str]) -> Optional[Dict[str, str]]:
    return None if location_id is None else {"id": location_id}
