"""Custom forms resource (form definitions and parent submissions)."""

import os
from typing import Any, Dict, Iterator, List, Optional

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource

#: Element types whose answers are written back onto the student profile
#: rather than being stored in the submit's ``payload``.
PROFILE_BACKED_ELEMENTS = frozenset(
    {
        "EMERGENCY_CONTACTS",
        "MEDICAL_DATA",
        "PARENT_1_CONTACTS",
        "PARENT_2_CONTACTS",
        "GUARDIAN_CONTACTS",
        "DOCUMENTS",
    }
)

#: Element types that carry no answer (layout/content only).
_CONTENT_ELEMENTS = frozenset({"HTML", "HEADER", "DIVIDER", "IMAGE"})


class FormsResource(BaseResource):
    """Custom forms and the submissions parents make against them.

    Custom forms (medical updates, permission/consent forms, transition
    surveys, scholarship registrations) are the mechanism schools use to
    collect data that has no dedicated field on the application. Their answers
    are **not** returned by ``applications.list()`` — see :meth:`answers`.

    A submit stores answers in two places:

    - ``payload`` — answers to the form's own questions (radio, checkbox,
      text, signature, ...). This is where consent/permission answers live.
    - ``initial_payload`` — the profile data pre-filled into the form when it
      was opened, plus blank slots for the form's own questions.

    Elements listed in :data:`PROFILE_BACKED_ELEMENTS` (emergency contacts,
    medical data, parent contacts) are written back onto the student profile
    on submission, so the authoritative current value for those lives on
    ``applications.get()``, not on the submit.
    """

    # ── Form definitions ────────────────────────────────────────

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through every form defined for the school.

        Includes both custom forms and the built-in stub forms (enquiry,
        event booking, ...). Each record has ``id``, ``title``, ``form_slug``,
        ``kind``, ``is_active`` and ``is_private``.
        """
        return self._list("forms/staff/", params=filters, page_size=page_size)

    def list_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of form definitions."""
        return self._list_page(
            "forms/staff/", params=filters, page=page, page_size=page_size
        )

    def published(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through published (parent-facing) custom forms only.

        Unlike :meth:`list` this returns the parent-facing view, which
        includes the form's audience rules (``allowed_entry_years``,
        ``allowed_entry_grades``, ``allowed_application_statuses``,
        ``allowed_campuses``) and payment settings.
        """
        return self._list("forms/", params=filters, page_size=page_size)

    def get(self, form_slug: str) -> Dict[str, Any]:
        """Get a single published form by its ``form_slug``.

        Note this endpoint is keyed by **slug**, not UUID.
        """
        return self._get(f"forms/{form_slug}/")

    def find(self, title_or_slug: str) -> Optional[Dict[str, Any]]:
        """Return the first form whose title or slug matches (case-insensitive).

        Convenience for looking up a form's UUID when you only know its name.
        Returns ``None`` if nothing matches.
        """
        needle = title_or_slug.strip().lower()
        for form in self.list(page_size=1000):
            if needle in (
                (form.get("title") or "").lower(),
                (form.get("form_slug") or "").lower(),
            ):
                return form
        return None

    # ── Submits ─────────────────────────────────────────────────

    def submits(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through form submissions.

        Supported filters (confirmed against the API):

        - ``form`` — a form UUID. Note: **not** ``form_id``, even though the
          field is called ``form_id`` in the response.
        - ``entry_year``, ``entry_grade``, ``application_statuses``
        - ``is_completed`` — ``True`` for submitted, ``False`` for started
          but not finished.

        Records are summaries (``form_id``, ``created_at``, ``completed_at``,
        ``form_pdf``, nested ``student_profile``). They carry **neither the
        answers nor the submit's own id**, so you cannot feed them straight
        into :meth:`get_submit`. To get answers in bulk, either use
        :meth:`export_submits` (one request, everything flattened) or
        :meth:`iter_answers`, which walks ``student_profile.id`` back through
        the application detail.
        """
        return self._list(
            "forms/staff-submits/", params=filters, page_size=page_size
        )

    def submits_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of form submissions."""
        return self._list_page(
            "forms/staff-submits/", params=filters, page=page, page_size=page_size
        )

    def get_submit(self, submit_id: str) -> Dict[str, Any]:
        """Get a single submission including ``payload`` and ``form_schema``."""
        return self._get(f"forms/staff-submits/{submit_id}/")

    def submits_for_application(
        self, application_id: str, *, form: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return every submission for one application, with full payloads.

        The ``forms/staff-submits/`` endpoint has no per-application filter, so
        this reads the submit IDs off the application detail and fetches each
        one.

        Args:
            application_id: UUID of the application.
            form: Optional form UUID to return submissions for that form only.

        Each returned submit is annotated with ``form_id`` and
        ``application_id``. The submit detail endpoint does not include them —
        its ``form_schema.id`` is a *schema version* id, not the form's id, so
        without this you cannot tell which form a submit belongs to.
        """
        application = self._get(f"applications/{application_id}/")
        submits = []
        for entry in application.get("custom_form_submits", []):
            if form is not None and entry.get("form") != form:
                continue
            submit = self.get_submit(entry["id"])
            submit["form_id"] = entry.get("form")
            submit["application_id"] = application_id
            submits.append(submit)
        return submits

    def answers_for_application(
        self, application_id: str, *, form: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return labelled answers for one application's submissions.

        Each record is ``{"submit_id", "form_id", "completed_at", "answers"}``
        where ``answers`` is as described in :meth:`answers`.
        """
        return [
            {
                "submit_id": submit["id"],
                "form_id": submit.get("form_id"),
                "completed_at": submit.get("completed_at"),
                "answers": self.answers_from(submit),
            }
            for submit in self.submits_for_application(application_id, form=form)
        ]

    def iter_answers(
        self, *, form: Optional[str] = None, page_size: int = 100, **filters: Any
    ) -> Iterator[Dict[str, Any]]:
        """Yield labelled answers for every submission matching *filters*.

        Accepts the same filters as :meth:`submits`. Yields
        ``{"student_profile", "submit_id", "form_id", "completed_at",
        "answers"}``.

        This makes one request per matching application, because the submits
        list omits the submit id. For a large export prefer
        :meth:`export_submits`, which returns the same data flattened to CSV
        in a single request.
        """
        seen = set()
        for summary in self.submits(form=form, page_size=page_size, **filters):
            profile = summary.get("student_profile") or {}
            profile_id = profile.get("id")
            if not profile_id or profile_id in seen:
                continue
            seen.add(profile_id)
            for record in self.answers_for_application(profile_id, form=form):
                record["student_profile"] = profile
                yield record

    def update_submit(
        self, submit_id: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Overwrite a submission's ``payload`` (staff edit).

        WARNING: This replaces the whole payload. Read it with
        :meth:`get_submit` first, modify, then write it back.
        """
        return self._put(
            f"forms/staff-submits/{submit_id}/", json={"payload": payload}
        )

    def reopen_submit(self, submit_id: str) -> Optional[Dict[str, Any]]:
        """Re-open a completed submission so the parent can edit it again."""
        return self._post(f"forms/staff-submits/{submit_id}/re_open/")

    def export_submits(self, dest_path: str, **filters: Any) -> str:
        """Download the form-submits report as CSV.

        Accepts the same filters as :meth:`submits`. Returns *dest_path*.
        """
        resp = self._http.get(
            self._url("forms/staff-submits/export/"), params=filters
        )
        dest_dir = os.path.dirname(dest_path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    # ── Answers ─────────────────────────────────────────────────

    def answers(self, submit_id: str) -> List[Dict[str, Any]]:
        """Return a submission's answers flattened and labelled.

        Joins the raw ``payload`` against the form's schema so each answer
        carries the question text a parent actually saw, instead of an opaque
        key like ``group_3_social_media``.

        Returns one record per answerable element, in form order::

            {
                "section": "Photograph/Video Permission Form",
                "name": "group_3_social_media",
                "label": "Group 3: Social Media",
                "element_type": "RADIO",
                "value": "Yes",
                "is_profile_backed": False,
            }

        Layout-only elements (HTML blocks, dividers) are skipped. Elements
        flagged ``is_profile_backed`` are copies of profile data taken when the
        form was opened — read the application detail for their current value.

        ``value`` is not always a scalar. ``EMERGENCY_CONTACTS`` is a list of
        contacts, ``MEDICAL_DATA`` a dict, checkbox groups a list of selected
        options, and a ``DOCUMENTS`` element is a document *group* whose files
        live under its ``documents`` key — ``len()`` on the group counts its
        fields, not its files.
        """
        return self.answers_from(self.get_submit(submit_id))

    @staticmethod
    def answers_from(submit: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten and label an already-fetched submit (see :meth:`answers`)."""
        # `payload` holds the parent's own answers; `initial_payload` holds the
        # profile data pre-filled at open time plus blanks for those answers.
        # Overlaying payload on initial_payload gives the final state.
        values = dict(submit.get("initial_payload") or {})
        values.update(submit.get("payload") or {})

        results: List[Dict[str, Any]] = []
        schema = (submit.get("form_schema") or {}).get("schema") or []
        for section in schema:
            section_title = section.get("title", "")
            for element in section.get("elements", []):
                element_type = element.get("element_type", "")
                if element_type in _CONTENT_ELEMENTS:
                    continue
                name = element.get("name")
                results.append(
                    {
                        "section": section_title,
                        "name": name,
                        "label": (element.get("label") or "").strip(),
                        "element_type": element_type,
                        "value": values.get(name),
                        "is_profile_backed": element_type
                        in PROFILE_BACKED_ELEMENTS,
                    }
                )
        return results

    def consents(self, submit_id: str) -> Dict[str, Any]:
        """Return only the yes/no consent answers from a submission.

        Keyed by field name, with the question label and answer::

            {"group_3_social_media": {"label": "Group 3: Social Media",
                                      "value": "Yes"}}

        A permission/consent form models each permission as a RADIO or
        CHECKBOX element, so this filters :meth:`answers` down to those.
        """
        return {
            answer["name"]: {
                "label": answer["label"],
                "value": answer["value"],
            }
            for answer in self.answers(submit_id)
            if answer["element_type"] in ("RADIO", "CHECKBOX", "CHECKBOX_GROUP")
        }
