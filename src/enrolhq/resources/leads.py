"""Leads resource."""

import re
from typing import Any, Dict, List, Optional

from ..exceptions import EnrolHQError
from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class LeadsResource(BaseResource):
    """Interact with leads (pre-enquiry contacts) and lead references.

    A lead captures a contact (parent) and optionally a prospective student
    before a full application exists. Key payload fields:

    - ``email``, ``title``, ``first_name``, ``last_name``, ``mobile_phone``,
      ``home_phone``, ``business_phone`` — contact details.
    - ``reference`` — a lead reference UUID identifying which form/source the
      lead came from (see :meth:`references`).
    - ``student`` — nested dict: ``first_name``, ``last_name``, ``dob``,
      ``entry_grade``, ``entry_year``, ``campus``, ``comment``, ``questions``,
      ``questions_other``.
    - ``residential_address`` — nested dict: ``apartment``, ``street_address``,
      ``city``, ``suburb``, ``state``, ``postcode``, ``country``.
    - ``student_profile`` — a student profile UUID. Set this to link the lead
      to an existing application/profile; leave ``None`` for a standalone lead.
    - ``how_hear`` / ``how_hear_other`` — marketing attribution.
    """

    # ── List / Get ──────────────────────────────────────────────

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through all leads matching *filters*.

        Supported filters include ``is_email_unique`` and
        ``has_student_profile`` (both booleans).
        """
        return self._list("leads/", params=filters, page_size=page_size)

    def list_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of leads."""
        return self._list_page(
            "leads/", params=filters, page=page, page_size=page_size
        )

    def get(self, lead_id: str) -> Dict[str, Any]:
        """Get full detail for a single lead."""
        return self._get(f"leads/{lead_id}/")

    # ── Create / Update ─────────────────────────────────────────

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lead.

        See the class docstring for the payload shape. To link the lead to an
        existing application, set ``student_profile`` to the profile's UUID.
        """
        return self._post("leads/", json=data)

    def update(self, lead_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Full-replacement update (PUT) of a lead.

        WARNING: This is a PUT, not a PATCH. You must send the complete
        lead object. Omitted fields may be reset to defaults.
        Recommended pattern: get() -> modify dict -> update().
        """
        return self._put(f"leads/{lead_id}/", json=data)

    # ── Lead References ─────────────────────────────────────────

    def references(self, *, page_size: int = 1000) -> List[Dict[str, Any]]:
        """List all lead references as a flat list.

        Each record has ``id``, ``name``, ``slug``,
        ``confirmation_redirect_url``, and ``is_removable``. Use a record's
        ``id`` as the ``reference`` field when creating or updating a lead.
        """
        return list(self._list("lead-references/", page_size=page_size))

    def create_reference(
        self,
        name: str,
        slug: Optional[str] = None,
        *,
        confirmation_redirect_url: str = "",
    ) -> Dict[str, Any]:
        """Create a new lead reference and return it (with server-assigned id).

        Lead references have no dedicated write endpoint — they live on the
        school settings object, so this round-trips ``school/``:
        get -> append to ``lead_references`` -> put.

        Args:
            name: Display name for the reference.
            slug: URL slug; defaults to a slugified *name*.
            confirmation_redirect_url: Where the public form redirects after
                submission (empty for the default confirmation page).

        Raises:
            ValueError: If a lead reference with the same slug already exists.
            EnrolHQError: If the reference is missing when read back after
                saving.
        """
        if slug is None:
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        school = self._get("school/")
        references = school.get("lead_references", [])
        if any(r.get("slug") == slug for r in references):
            raise ValueError(
                f"A lead reference with slug {slug!r} already exists"
            )
        school["lead_references"] = references + [
            {
                "name": name,
                "slug": slug,
                "confirmation_redirect_url": confirmation_redirect_url,
                "is_removable": True,
            }
        ]
        self._put("school/", json=school)
        for ref in self.references():
            if ref.get("slug") == slug:
                return ref
        raise EnrolHQError(
            f"Lead reference {slug!r} was not found after saving school settings"
        )
