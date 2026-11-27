"""Interview set-up: settings, types, interviewers, locations and availability."""

import datetime as dt
from typing import Any, Dict, List, Optional, Union

from ..pagination import PaginatedIterator
from .base import BaseResource, deep_merge
from .events import TimeLike, json_time


class InterviewsResource(BaseResource):
    """Interview set-up (the *Interviews* menu in the dashboard).

    Everything about interviews, from the school's settings to booking one
    student's interview:

    * **Settings** (``interview/settings/``): the default interview length,
      whether and when parents can book or cancel, how many slots they are
      shown, the reminder hours and the school's ``interview_types``.
    * **Interviewers** (``interview/interviewers/``): the staff who interview.
    * **Locations** (``school-locations/``): the rooms an interview is in.
    * **Availability** (``interview/availabilities/``): a block of time on one
      date when one interviewer can interview. EnrolHQ cuts the block into
      slots of ``interview_duration_minutes``, and parents (or staff) book a
      slot.
    * **Questions** (``interview/questions/sections/``): the sections and
      questions printed on the interview review sheet.
    * **PDF settings** (``interview/pdf-settings/``): the title of that sheet
      and which parts of the student's record it shows.
    * **A student's interviews**: :meth:`assign` gives a student an interview
      of one type, :meth:`open_times` lists the slots it can be booked into,
      and :meth:`book` and :meth:`cancel_booking` book and cancel as staff.

    Most of these endpoints need the matching interview permission even to
    read (Registrar role, school Admin or superuser); a staff user without it
    gets 403. Only :meth:`types`, :meth:`interviewers` and
    :meth:`get_pdf_settings` are open to any staff user.
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
        """Make sure interview types with these names exist.

        Returns the type for each name, in the order of *names*. Existing
        types are matched by name (case-insensitive) and kept. Nothing is
        written when every name already exists.
        """
        if isinstance(names, str):
            raise TypeError("names must be a list of names, not one string")
        settings = self.get_settings()
        current = settings.get("interview_types") or []
        wanted = [name.strip() for name in names]
        have = {_key(row.get("name")) for row in current}
        missing: List[Dict[str, Any]] = []
        for name in wanted:
            if _key(name) not in have:
                have.add(_key(name))
                missing.append({"name": name})
        if missing:
            saved = self.update_settings(
                {**settings, "interview_types": [*current, *missing]}
            )
            current = (saved or {}).get("interview_types") or self.types()
        by_name = {_key(row.get("name")): row for row in current}
        return [by_name[_key(name)] for name in wanted]

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
        ``start_time``, ``-start_time``, ``created_at``, comma-separated).
        An ``ordering`` replaces the server's own, so for more than one page
        pass one that cannot tie, such as ``"date,start_time,created_at"``,
        or blocks can repeat or go missing. Each row has ``interviewer`` (an
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
        date: Union[str, dt.date],
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
        ``YYYY-MM-DD`` or a :class:`datetime.date`, and the times take
        anything :func:`~enrolhq.json_time` accepts, such as ``"09:00"``. The block must be at least one
        interview long, and at least one type is required. The server does
        not stop two blocks for the same interviewer overlapping. The
        response leaves out ``has_bookings``.
        """
        return self._post(
            "interview/availabilities/",
            json={
                "interviewer": interviewer,
                "location": {"id": location},
                "date": date.isoformat() if isinstance(date, dt.date) else date,
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

    def time_slots(self, availability_id: str) -> List[Dict[str, Any]]:
        """List the slots of one availability block, earliest first.

        Each is ``{id, interviewer, availability, booking, date, start_time,
        end_time}`` with times as ``"09:00:00"``. ``booking`` is ``None``
        while the slot is free.
        """
        return self._get(f"interview/availabilities/{availability_id}/time-slots/")

    def delete_availability(self, availability_id: str) -> None:
        """Delete an availability block. 400 if a slot in it is booked."""
        self._delete(f"interview/availabilities/{availability_id}/")

    def question_sections(self) -> List[Dict[str, Any]]:
        """List the question sections of the interview review sheet, in order.

        Each is ``{id, position, label, questions, allowed_entry_grades,
        allowed_campuses, allowed_attendance_types,
        allowed_custom_categories_options}``. A question is ``{id, position,
        label, lines_for_answer, is_underline_shown}``. The ``allowed_*``
        lists narrow which students a section is printed for; empty means
        every student.
        """
        return list(self._list("interview/questions/sections/", page_size=1000))

    def get_question_section(self, section_id: str) -> Dict[str, Any]:
        """Get one question section."""
        return self._get(f"interview/questions/sections/{section_id}/")

    def create_question_section(
        self,
        label: str,
        questions: List[Dict[str, Any]],
        *,
        allowed_entry_grades: Optional[List[int]] = None,
        allowed_campuses: Optional[List[str]] = None,
        allowed_attendance_types: Optional[List[str]] = None,
        allowed_custom_categories_options: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Add a question section after the existing ones.

        Each question needs a ``label``; ``lines_for_answer`` (0 to 10,
        default 4) and ``is_underline_shown`` (default true) are filled in.
        Questions are printed in the order given.
        """
        return self._post(
            "interview/questions/sections/",
            json={
                "label": label,
                "position": None,
                "questions": _questions(questions),
                "allowed_entry_grades": list(allowed_entry_grades or []),
                "allowed_campuses": list(allowed_campuses or []),
                "allowed_attendance_types": list(allowed_attendance_types or []),
                "allowed_custom_categories_options": list(
                    allowed_custom_categories_options or []
                ),
            },
        )

    def update_question_section(
        self, section_id: str, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Change a question section: GET, merge *changes*, PUT.

        ``questions`` in *changes* replaces the section's questions, in the
        order given. The server recreates them on every save, so question
        ids do not last. ``position`` (from 1) moves the section among the
        others.
        """
        current = self.get_question_section(section_id)
        merged = deep_merge(current, changes)
        merged["questions"] = _questions(merged.get("questions") or [])
        return self._put(f"interview/questions/sections/{section_id}/", json=merged)

    def delete_question_section(self, section_id: str) -> None:
        """Delete a question section and its questions."""
        self._delete(f"interview/questions/sections/{section_id}/")

    def get_pdf_settings(self) -> Dict[str, Any]:
        """Get the interview review sheet settings.

        ``pdf_settings`` holds ``title`` and one ``is_..._visible`` flag per
        part of the sheet; ``default_pdf_settings`` holds EnrolHQ's defaults
        for the same keys.
        """
        return self._get("interview/pdf-settings/")

    def update_pdf_settings(self, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Change some review sheet settings, keeping the rest.

        For example ``{"title": "Enrolment Interview",
        "is_medical_data_visible": False}``.
        """
        current = self.get_pdf_settings().get("pdf_settings") or {}
        return self._put(
            "interview/pdf-settings/",
            json={"pdf_settings": deep_merge(current, changes)},
        )

    def student_interviews(self, application_id: str) -> List[Dict[str, Any]]:
        """List one student's interviews, oldest first.

        Each is ``{id, interview_type, interviewer, booking, is_booked,
        completed_at, notes, ...}``. ``booking`` is ``None`` or ``{id, date,
        start_time, end_time, location, interviewer, can_be_cancelled, ...}``
        and ``is_booked`` is true while that booking is still ahead. A
        student who was never given an interview has an empty list, and so
        does one in the trash, whose interviews the server does not list.
        """
        if not application_id:
            raise ValueError("application_id is required")
        rows = self._list(
            "interview/assigned-profiles/", params={"id": application_id}, page_size=10
        )
        for row in rows:
            if str(row.get("id")) == str(application_id):
                return row.get("interviews") or []
        return []

    def assign(
        self,
        application_id: str,
        interview_type: str,
        *,
        interviewer: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Give a student an interview of this type, to be booked later.

        A new interview fires the *Interview Assigned* event, so an active
        automation on that event emails the family. A student who already has
        an unfinished interview of the type gets no second one.

        ``interviewer`` (an id) limits the booking to that interviewer's
        availability. It is also set on an existing unfinished interview of
        the type that has no current booking, so repeating the call with
        another interviewer moves the interview to them.

        The response only repeats the request, even when the id matched no
        student, so check with :meth:`student_interviews`.
        """
        return self._post(
            "applications-list/bulk_add_interview/",
            json={"interview_type": interview_type, "interviewer": interviewer},
            params={"id": application_id},
        )

    def unassign(
        self,
        application_id: str,
        interview_type: str,
        *,
        including_with_interviewer: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Remove a student's unfinished interview of this type.

        An interview that has ever been booked, even if the booking was
        cancelled, is kept: use :meth:`unassign_interviewer` and then
        :meth:`delete_interview` for that. With ``including_with_interviewer``
        false an interview that already has an interviewer is kept too.
        """
        return self._post(
            "applications-list/bulk_remove_interview/",
            json={
                "interview_type": interview_type,
                "including_with_interviewer": including_with_interviewer,
            },
            params={"id": application_id},
        )

    def assign_interviewer(
        self, interview_id: str, interviewer: str
    ) -> Optional[Dict[str, Any]]:
        """Set the interviewer of one interview.

        Booking is then limited to that interviewer's availability.
        """
        return self._post(
            f"interview/interviews/{interview_id}/assign_interviewer/",
            json={"interviewer": interviewer},
        )

    def unassign_interviewer(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """Clear the interviewer of one interview."""
        return self._post(f"interview/interviews/{interview_id}/unassign_interviewer/")

    def delete_interview(self, interview_id: str) -> None:
        """Delete one interview and its cancelled bookings.

        400 if the interview has an interviewer or a booking that is not
        cancelled: call :meth:`unassign_interviewer` and
        :meth:`cancel_booking` first.
        """
        self._delete(f"interview/interviews/{interview_id}/")

    def open_times(self, interview_id: str) -> List[Dict[str, Any]]:
        """List the slots an interview can be booked into, as staff see them.

        Each slot is ``{date, start_time, end_time, interviewer, location,
        interviewer_availability, is_booked, token}``. Pass the ``token`` of
        a slot that is not booked to :meth:`book`. Staff are offered every
        matching slot from now on, whatever the parent booking limits are.

        While the interview has a booking, only other interviewers' slots on
        the booked date are listed: booking one adds that interviewer to the
        same interview. To see every slot again, cancel the booking first.
        """
        days = self._get(f"interview/interviews/{interview_id}/interview_intervals/")
        return [slot for day in days or [] for slot in day]

    def book(
        self,
        application_id: str,
        token: str,
        *,
        email_templates_to_send: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Book an interview slot for a student, as staff.

        *token* comes from :meth:`open_times`. A staff booking does not fire
        the *Interview Booked* event, so the family is only told if
        ``email_templates_to_send`` (template ids) is given. Reminder
        automations still run for the booking.
        """
        body: Dict[str, Any] = {"token": token}
        if email_templates_to_send:
            body["email_templates_to_send"] = list(email_templates_to_send)
        return self._post(f"applications/{application_id}/book_interview/", json=body)

    def cancel_booking(
        self, application_id: str, booking_id: str
    ) -> Optional[Dict[str, Any]]:
        """Cancel a student's interview booking and reopen its slot.

        Fires the *Interview Cancelled by Staff* event, so an active
        automation on that event emails the family. There is no call that
        moves a booking: cancel it, then :meth:`book` another slot.
        """
        return self._post(
            f"applications/{application_id}/cancel_interview_booking/",
            json={"booking": booking_id},
        )


def _key(name: Any) -> str:
    return str(name or "").strip().lower()


def _questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "lines_for_answer": 4,
            "is_underline_shown": True,
            **question,
            "position": position,
        }
        for position, question in enumerate(questions, 1)
    ]


def _location(location_id: Optional[str]) -> Optional[Dict[str, str]]:
    return None if location_id is None else {"id": location_id}
