"""Admission processes resource (the kinds of application a school accepts)."""

from typing import Any, Dict

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class AdmissionProcessesResource(BaseResource):
    """Read a school's admission processes (*Settings > Admission Processes*).

    An admission process is one kind of application a school accepts, e.g.
    "Junior School Application" or "Scholarship Application". A student can
    have one application per process, so a school with several processes can
    hold several independent applications for the same student, each with its
    own status and entry details. Read those with
    ``client.applications.student_applications()`` (one student) or
    ``client.applications.iter_student_applications()`` (the whole school).

    Each process has:

    - ``id``, ``title`` and ``is_enabled``.
    - ``is_new_entry_details_required`` and ``campus``: when true, the family
      is asked for entry details (year level, entry year) for this process's
      ``campus`` instead of reusing the ones already on the student. ``campus``
      is ``None`` otherwise.
    - ``forms``: the forms that make up the process, in order. Each row has
      its own ``id``, ``custom_form`` (the form's UUID, as in
      ``client.forms.list()``), ``opening_application_status`` (the status a
      new application starts in), ``is_application_submission_form`` and
      ``has_incomplete_student_applications``.

    A form is either the process's *submission form* or a *supporting form*.
    Only submitting the submission form marks the application as submitted.
    A form belongs to at most one process, and can be a custom form or the
    built-in EOI or enrolment form (``kind`` ``CUSTOM``, ``GPA`` or
    ``ENROLMENT`` in ``client.forms.list()``).

    This resource is read-only: processes are set up in the dashboard.
    Schools without the admission processes feature answer every call here
    with 403 (:class:`~enrolhq.ForbiddenError`).
    """

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through the school's admission processes."""
        return self._list("admission-processes/", params=filters, page_size=page_size)

    def list_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of admission processes."""
        return self._list_page(
            "admission-processes/", params=filters, page=page, page_size=page_size
        )

    def get(self, process_id: str) -> Dict[str, Any]:
        """Get one admission process, including its ``forms``."""
        return self._get(f"admission-processes/{process_id}/")
