"""Applications resource."""

import datetime as dt
import uuid
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Union

from ..exceptions import EnrolHQError
from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource

#: The API version whose student record carries ``applications`` (one entry
#: per admission process). The v1 and v2 records have no such key.
STUDENT_APPLICATIONS_API_VERSION = "v3alpha"

#: ``iter_student_applications()`` reads full student records, 100 a request.
#: Such a request takes 10 seconds or more and now and then far longer, and
#: one failure would otherwise lose a sweep that runs for many minutes. So
#: each request gets at least this read timeout (seconds), and a page that
#: fails for a passing reason is asked for again this many times.
SWEEP_READ_TIMEOUT = 120
SWEEP_RETRIES = 3

#: Student fields copied onto each row of ``iter_student_applications()``.
STUDENT_SUMMARY_FIELDS = (
    "id",
    "sid",
    "external_id",
    "first_name",
    "middle_name",
    "last_name",
    "preferred_name",
)


class ApplicationsResource(BaseResource):
    """Interact with student applications."""

    # ── List / Get ──────────────────────────────────────────────

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through all applications matching *filters*.

        Supported filters: entry_year, entry_grade, application_statuses,
        search, campus, gender, first_name, last_name, dob, is_favorite,
        ordering, has_external_id, external_id,
        exclude_application_statuses, exclude_docs, etc.
        """
        return self._list("applications-list/", params=filters, page_size=page_size)

    def list_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of applications."""
        return self._list_page(
            "applications-list/", params=filters, page=page, page_size=page_size
        )

    def count(self, **filters: Any) -> int:
        """Return the total count of applications matching *filters*."""
        resp = self._http.get(self._url("applications-list/count/"), params=filters)
        return resp.json().get("count", 0)

    def get(self, application_id: str) -> Dict[str, Any]:
        """Get full detail for a single application."""
        return self._get(f"applications/{application_id}/")

    # ── Nested profile data ─────────────────────────────────────
    #
    # These live on the detail serializer only. `list()` returns a summary
    # serializer that omits them, which is why a list-based export appears to
    # be missing emergency contacts and medical data entirely.

    def emergency_contacts(self, application_id: str) -> List[Dict[str, Any]]:
        """Return the application's emergency contacts.

        Each contact has ``id``, ``title``, ``first_name``, ``last_name``,
        ``relationship_to_student``, ``home_phone``, ``mobile_phone``,
        ``business_phone``, ``external_id`` and ``updated_at``.

        Not available from :meth:`list` — this fetches the detail record.
        """
        return self.get(application_id).get("emergency_contacts", [])

    def medical_data(self, application_id: str) -> Dict[str, Any]:
        """Return the application's medical data (doctor, medicare, conditions).

        Not available from :meth:`list` — this fetches the detail record.
        """
        return self.get(application_id).get("medical_data", {})

    def guardians(self, application_id: str) -> List[Dict[str, Any]]:
        """Return the application's guardians.

        Not available from :meth:`list` — this fetches the detail record.
        """
        return self.get(application_id).get("guardians", [])

    # ── Admission processes ─────────────────────────────────────
    #
    # Everywhere else in this SDK an "application" is the student record.
    # Under admission processes a student also holds one application per
    # process, which the server calls a student application. Those are only
    # on the v3alpha student record, so these methods read that version
    # whatever version the client's base URL names.

    def student_applications(self, application_id: str) -> List[Dict[str, Any]]:
        """Return the student's applications, one per admission process.

        A school with several admission processes (see
        ``client.admission_processes``) can hold several applications for one
        student, e.g. a school application and a scholarship application.
        Each has its own status and entry details:

        - ``id``, ``created_at`` and ``admission_process`` (the process UUID).
        - ``is_primary``: the application the student record mirrors.
        - ``entry_grade``, ``entry_term``, ``entry_year``, ``campus``,
          ``attendance_type``, ``commencement_date``, ``application_status``.
        - ``is_new_entry_details_missing``: the process asks for its own
          entry details and none were recorded for this application. The
          entry grade, year and campus on the row are then copies of the
          student record's, which can belong to a different campus, so do
          not read them as this application's. The campus applied for is
          the process's ``campus``. A submitted application can be in this
          state.
        - ``submitted_at`` and ``completed_at``: set by the process's
          submission form; ``completed_at`` can come later, e.g. on payment.
        - ``form_submits``: the form submissions that belong to this
          application, each with ``id``, ``form``, ``created_at``,
          ``submitted_at``, ``completed_at`` and ``form_pdf`` (a document
          id, or ``None``). For a custom form, pass the ``id`` to
          ``client.forms.answers()`` to read what the family answered. The
          built-in EOI and enrolment forms have no readable submission (that
          call returns 404): their answers are the student record itself.

        The entry details and status on the student record (:meth:`get`,
        :meth:`list`) are those of the primary application. The others are
        only visible here. At most one application is primary, and a student
        can have applications with none primary (e.g. after a profile merge).

        This is not the same as ``custom_form_submits`` on :meth:`get`: a
        submission made before its form joined a process belongs to no
        application, even if the form was completed, and is not listed here.

        Returns ``[]`` when the student has no application yet, and at schools
        that do not use admission processes. The data comes from the
        ``v3alpha`` API, which may change without notice.
        """
        url = self._url_for_version(
            STUDENT_APPLICATIONS_API_VERSION, f"applications/{application_id}/"
        )
        return _student_applications_of(self._http.get(url).json(), url)

    def iter_student_applications(
        self,
        *,
        admission_process: Optional[Union[str, uuid.UUID, Iterable[Any]]] = None,
        updated_after: Optional[Union[str, dt.datetime]] = None,
        page_size: int = 100,
    ) -> Iterator[Dict[str, Any]]:
        """Yield every student application at the school, across all students.

        Each row is as described in :meth:`student_applications`, plus
        ``student_profile``: the student's ``id``, ``sid``, ``external_id``
        and names. Students without an application yield nothing::

            for app in client.applications.iter_student_applications(
                admission_process=process["id"]
            ):
                print(app["student_profile"]["sid"], app["application_status"])
                for submit in app["form_submits"]:
                    answers = client.forms.answers(submit["id"])  # custom forms

        These are applications, not form submissions. A submission attached
        to no application (see :meth:`student_applications`) is not here; for
        every submission of a form use ``client.forms.iter_answers(form=...)``.

        This sweeps the full student records, 100 per request at most. Each
        request is large and takes around 10 seconds, so a school with 15,000
        students takes about 25 minutes. That is still far quicker than one
        :meth:`student_applications` call per student. A request that times
        out or meets a server error or rate limit is repeated up to three
        times before the sweep gives up.

        Args:
            admission_process: Only applications in this process (an ``id``
                from ``client.admission_processes``), or in any of several.
                The server has no such filter, so every student is still
                read; this only narrows what is yielded.
            updated_after: Only students changed since this time (an aware
                ``datetime`` or an ISO 8601 string with an offset). This is
                the only filter the endpoint applies; others are ignored. It
                follows the student record and its carers, form submissions,
                payments, bookings and documents, not the applications
                themselves, so do a full sweep from time to time.
            page_size: Students per request (the server caps this at 100).
                Smaller pages are not quicker: each request has a high fixed
                cost, so the whole sweep takes longer.
        """
        if isinstance(updated_after, dt.datetime):
            if updated_after.tzinfo is None:
                raise ValueError("updated_after must be timezone-aware")
            updated_after = updated_after.isoformat()
        url = self._url_for_version(STUDENT_APPLICATIONS_API_VERSION, "applications/")
        params = {} if updated_after is None else {"updated_after": updated_after}
        students = PaginatedIterator(
            self._http,
            url,
            params=params,
            page_size=page_size,
            retries=SWEEP_RETRIES,
            timeout=_sweep_timeout(self._http.timeout),
        )
        if admission_process is None:
            wanted = None
        elif isinstance(admission_process, (str, uuid.UUID)):
            wanted = {str(admission_process)}
        else:
            wanted = {str(process_id) for process_id in admission_process}
        # A separate generator, so bad arguments raise here, not on first use.
        return _flatten_student_applications(students, url, wanted)

    # ── Coded fields ────────────────────────────────────────────

    def field_choices(self) -> Dict[str, Dict[Any, Any]]:
        """Return the label for every coded value, keyed by field path.

        Several fields come back as codes rather than text, e.g. a parent's
        ``relationship_to_student`` is ``0`` for Mother and ``1`` for Father.
        This reads the ``OPTIONS applications/`` metadata and maps each
        choice field's path to ``{value: label}``. Nested fields use dots and
        list items drop their index::

            choices = client.applications.field_choices()
            choices["user_parent.relationship_to_student"][0]   # "Mother"
            choices["emergency_contacts.relationship_to_student"]

        Lists a school configures (emergency contact relationships, ethnic
        origins, document kinds) reflect that school's settings.
        """
        meta = self._options("applications/")
        fields = meta.get("actions", {}).get("POST", {})
        choices: Dict[str, Dict[Any, Any]] = {}
        _collect_choices(fields, "", choices)
        return choices

    # ── Create / Update ─────────────────────────────────────────

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new application (CreateStudentProfile schema)."""
        return self._post("applications/", json=data)

    def update(self, application_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Full-replacement update (PUT) of an application.

        WARNING: This is a PUT, not a PATCH. You must send the complete
        application object. Omitted fields may be reset to defaults.
        Recommended pattern: get() -> modify dict -> update().
        """
        return self._put(f"applications/{application_id}/", json=data)

    def attach(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Attach a student to an existing parent."""
        return self._post("applications/attach/", json=data)

    # ── Actions ─────────────────────────────────────────────────

    def change_status(
        self,
        application_ids: List[str],
        status: Union[int, "ApplicationStatus"],
    ) -> Optional[Dict[str, Any]]:
        """Change the status of one or more applications.

        Args:
            application_ids: List of application UUIDs.
            status: Target ApplicationStatus value.
        """
        ids = [str(i) for i in application_ids]
        # The API expects repeated `id` query params (e.g. ?id=a&id=b), not
        # `id__in=`. Without a recognised filter the endpoint refuses with
        # "Bulk action on all items is not allowed".
        return self._post(
            "applications-list/change_status/",
            json={"application_status": int(status)},
            params={"id": ids[0] if len(ids) == 1 else ids},
        )

    def send_mail(
        self, application_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Send an email to the application's parent."""
        return self._post(f"applications/{application_id}/send_mail/", json=data)

    def email_preview(
        self, application_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Preview an email before sending."""
        return self._post(f"applications/{application_id}/email_preview/", json=data)

    def toggle_favorite(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Toggle the favourite flag on an application."""
        return self._post(f"applications/{application_id}/toggle_favorite/")

    def regenerate_sid(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Regenerate the student ID."""
        return self._post(f"applications/{application_id}/regenerate_sid/")

    def book_interview(
        self, application_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Book an interview for the application."""
        return self._post(
            f"applications/{application_id}/book_interview/", json=data
        )

    def cancel_interview(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Cancel an interview booking."""
        return self._post(
            f"applications/{application_id}/cancel_interview_booking/"
        )

    def send_enrolment_invite(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Send an enrolment invite."""
        return self._post(
            f"applications/{application_id}/send_enrolment_invite/"
        )

    def decline_by_parent(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Decline an application (parent-initiated)."""
        return self._post(
            f"applications/{application_id}/decline_student_by_parent/"
        )

    def decline_by_staff(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Decline an application (staff-initiated)."""
        return self._post(
            f"applications/{application_id}/decline_student_by_staff/"
        )

    def cancel_decline_by_parent(
        self, application_id: str
    ) -> Optional[Dict[str, Any]]:
        """Cancel a parent-initiated decline."""
        return self._post(
            f"applications/{application_id}/cancel_decline_student_by_parent/"
        )

    def cancel_decline_by_staff(
        self, application_id: str
    ) -> Optional[Dict[str, Any]]:
        """Cancel a staff-initiated decline."""
        return self._post(
            f"applications/{application_id}/cancel_decline_student_by_staff/"
        )

    # ── Offer Management ────────────────────────────────────────

    def cancel_offer(
        self, application_id: str, offer_kind: str
    ) -> Optional[Dict[str, Any]]:
        """Cancel an offer."""
        return self._post(
            f"applications/{application_id}/cancel_offer/{offer_kind}/"
        )

    def delay_offer(
        self, application_id: str, offer_kind: str
    ) -> Optional[Dict[str, Any]]:
        """Delay an offer."""
        return self._post(
            f"applications/{application_id}/delay_offer/{offer_kind}/"
        )

    # ── Parent Management ───────────────────────────────────────

    def create_non_user_parent(
        self, application_id: str, data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a non-user parent for the application."""
        return self._post(
            f"applications/{application_id}/create_non_user_parent/", json=data
        )

    def delete_non_user_parent(
        self, application_id: str
    ) -> Optional[Dict[str, Any]]:
        """Delete the non-user parent from the application."""
        return self._post(
            f"applications/{application_id}/delete_non_user_parent/"
        )

    def switch_parents(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Swap the primary and secondary parents."""
        return self._post(f"applications/{application_id}/switch_parents/")

    # ── Bulk Operations ─────────────────────────────────────────

    def bulk_send_email(
        self, data: Dict[str, Any], **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Send bulk email to applications matching filters."""
        return self._post(
            "applications-list/bulk_send_email/", json=data, params=filters
        )

    def bulk_send_sms(
        self, data: Dict[str, Any], **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Send bulk SMS to applications matching filters."""
        return self._post(
            "applications-list/bulk_send_sms/", json=data, params=filters
        )

    def bulk_note(self, text: str, **filters: Any) -> Optional[Dict[str, Any]]:
        """Add a note to all applications matching filters."""
        return self._post(
            "applications-list/bulk_note/", json={"text": text}, params=filters
        )

    def bulk_enrolment_invite(self, **filters: Any) -> Optional[Dict[str, Any]]:
        """Send enrolment invites to applications matching filters."""
        return self._post(
            "applications-list/bulk_enrolment_invite/", params=filters
        )

    def bulk_close(self, **filters: Any) -> Optional[Dict[str, Any]]:
        """Close applications matching filters."""
        return self._post("applications-list/bulk_close/", params=filters)

    def bulk_reopen(self, **filters: Any) -> Optional[Dict[str, Any]]:
        """Reopen applications matching filters."""
        return self._post("applications-list/bulk_reopen/", params=filters)

    def bulk_make_offer(
        self, offer_kind: str, **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Make an offer to applications matching filters."""
        return self._post(
            f"applications-list/bulk_make_offer/{offer_kind}/", params=filters
        )

    def bulk_change_campus(
        self, data: Dict[str, Any], **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Change campus for applications matching filters."""
        return self._post(
            "applications-list/bulk_change_campus/", json=data, params=filters
        )

    def bulk_make_manual_payments(
        self, data: Dict[str, Any], **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Create manual payments for applications matching filters."""
        return self._post(
            "applications-list/bulk_make_manual_payments/",
            json=data,
            params=filters,
        )

    def merge_profiles(
        self,
        profile_to_keep: str,
        profile_not_to_keep: str,
        swap_parents: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Merge two student profiles."""
        return self._post(
            "applications-list/merge_profiles/",
            json={
                "profile_to_keep": str(profile_to_keep),
                "profile_not_to_keep": str(profile_not_to_keep),
                "is_profile_not_to_keep_parents_swapped": swap_parents,
            },
        )

    def delete_profiles(self, **filters: Any) -> Optional[Dict[str, Any]]:
        """Delete applications matching filters."""
        return self._post(
            "applications-list/delete-profiles/", params=filters
        )


def _student_applications_of(student: Dict[str, Any], url: str) -> List[Dict[str, Any]]:
    """Return a v3alpha student record's ``applications``.

    The key is always present on that version, so its absence means the
    request reached a version that never sends it. Raising then avoids
    reporting "no applications" for a student who has some.
    """
    if "applications" not in student:
        raise EnrolHQError(
            f"{url} returned a student record without 'applications'. That "
            f"list is only on the {STUDENT_APPLICATIONS_API_VERSION} API, "
            "which the SDK reaches by swapping the version at the end of "
            "base_url, so base_url must end in /api/<version>/ "
            "(e.g. /api/v2/)."
        )
    return student["applications"]


def _sweep_timeout(timeout: Any) -> Any:
    """Return the client's *timeout* with its read part raised for the sweep.

    *timeout* is as ``requests`` takes it: a number, a ``(connect, read)``
    pair, or ``None`` for no limit. A longer limit set on the client is kept.
    """
    if timeout is None:
        return None
    connect, read = timeout if isinstance(timeout, tuple) else (timeout, timeout)
    if read is not None:
        read = max(read, SWEEP_READ_TIMEOUT)
    return (connect, read)


def _flatten_student_applications(
    students: Iterator[Dict[str, Any]], url: str, wanted: Optional[Set[str]]
) -> Iterator[Dict[str, Any]]:
    """Yield each student's applications, tagged with who they belong to.

    *wanted* is the set of admission process ids to keep, or ``None`` for all.
    """
    for student in students:
        summary = {key: student.get(key) for key in STUDENT_SUMMARY_FIELDS}
        for application in _student_applications_of(student, url):
            if wanted is None or application["admission_process"] in wanted:
                yield {**application, "student_profile": summary}


def _collect_choices(
    fields: Dict[str, Any], prefix: str, out: Dict[str, Dict[Any, Any]]
) -> None:
    """Walk DRF OPTIONS field metadata, recording each field's choices."""
    for name, spec in fields.items():
        path = f"{prefix}{name}"
        # A list field describes its items under "child".
        while isinstance(spec.get("child"), dict):
            spec = spec["child"]
        if "choices" in spec:
            out[path] = {c["value"]: c["display_name"] for c in spec["choices"]}
        if isinstance(spec.get("children"), dict):
            _collect_choices(spec["children"], f"{path}.", out)
