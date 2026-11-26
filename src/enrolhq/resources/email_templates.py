"""Email templates, their groups, signatures and merge tags."""

from typing import Any, Dict, List, Optional

from ..pagination import PaginatedIterator
from .base import BaseResource, deep_merge

RECIPIENT_TYPES: Dict[str, str] = {
    "PRIMARY_CARER": "Primary Carer",
    "SECONDARY_CARERS": "Secondary Carers",
    "CARERS": "All Carers",
    "STAFF": "Staff",
    "PAYER": "Payer",
}

CREATABLE_KINDS = ("CUSTOM", "MARKETING")


class EmailTemplatesResource(BaseResource):
    """Email templates (*Settings > Email Templates*).

    A template has a ``name``, a ``subject_template`` and an
    ``html_template``, both Django templates that use the merge tags listed by
    :meth:`tags`. ``kind`` says what sends it: built-in kinds such as
    ``ENQUIRY_PARENT`` go out when the matching thing happens, while
    ``CUSTOM`` and ``MARKETING`` templates are sent by staff or by an
    automation (:class:`AutomationsResource`). Only the kinds in
    :data:`CREATABLE_KINDS` can be created; the school already has every
    built-in template. ``recipient_type`` is one of :data:`RECIPIENT_TYPES`
    and cannot change after creation.

    Names are not unique: a school often has the same template once per
    recipient type, so :meth:`find` returns a list.

    The server renders both templates on save and answers 400 for a template
    it cannot render. Writes are a full PUT; :meth:`update_fields` does the
    read-modify-write. Reading needs any staff user, writing needs the email
    template permissions (school Admin or superuser).
    """

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through the school's templates, without their bodies.

        Filters: ``search`` (name prefix), ``is_archived``, ``kinds``,
        ``groups`` and ``recipient_types``. Pass
        ``return_html_template=True`` to include ``html_template``.
        """
        return self._list("email-templates/", params=filters, page_size=page_size)

    def get(self, template_id: str) -> Dict[str, Any]:
        """Get one template, including ``html_template``."""
        return self._get(f"email-templates/{template_id}/")

    def find(
        self, name: str, *, recipient_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return the templates with this name (case-insensitive), without bodies."""
        needle = name.strip().lower()
        return [
            row
            for row in self.list(page_size=1000)
            if (row.get("name") or "").strip().lower() == needle
            and recipient_type in (None, row.get("recipient_type"))
        ]

    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a template.

        Required keys: ``name``, ``kind`` (one of :data:`CREATABLE_KINDS`),
        ``recipient_type``, ``group`` (a group id from :meth:`groups`),
        ``subject_template``, ``html_template``, ``from_email`` (may be
        ``""`` unless the recipient is staff), ``staff_recipients``,
        ``staff_reply_to_type`` (``""``, ``PRIMARY_CARER`` or
        ``CAMPUS_EMAIL``), ``attachments``, ``signature`` (an id or
        ``None``), ``is_base_render_needed`` and
        ``is_single_email_per_recipient``.
        """
        return self._post("email-templates/", json=data)

    def update(
        self, template_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Replace a template (full PUT). Prefer :meth:`update_fields`."""
        return self._put(f"email-templates/{template_id}/", json=data)

    def update_fields(
        self, template_id: str, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Change some template fields: GET, merge *changes*, PUT.

        Attachments and the per-template logos are kept unless *changes*
        names them.
        """
        return self.update(template_id, deep_merge(self.get(template_id), changes))

    def toggle_archive(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Archive a template, or bring an archived one back."""
        return self._post(f"email-templates/{template_id}/toggle_archive/")

    def delete(self, template_id: str) -> None:
        """Delete a template. Built-in templates cannot be deleted."""
        self._delete(f"email-templates/{template_id}/")

    def groups(self) -> List[Dict[str, Any]]:
        """List template groups (``{id, name, position, is_system, has_templates}``)."""
        return list(self._list("email-template-groups/", page_size=1000))

    def ensure_group(self, name: str) -> Dict[str, Any]:
        """Return the group with this name, adding it after the others if missing."""
        groups = self.groups()
        wanted = name.strip()
        for group in groups:
            if (group.get("name") or "").strip().lower() == wanted.lower():
                return group
        body = [{"id": group["id"], "name": group["name"]} for group in groups]
        saved = self._put(
            "email-template-groups/batch_update/", json=[*body, {"name": wanted}]
        )
        return next(group for group in saved or [] if group.get("name") == wanted)

    def tags(self) -> List[Dict[str, Any]]:
        """List the merge tags a template may use.

        Each is ``{kind, label, description, example_result, tag}``, where
        ``tag`` is the text to put in the template, such as
        ``{{ profile.first_name }}``.
        """
        return self._get("all-email-tags/")

    def signatures(self) -> List[Dict[str, Any]]:
        """List email signatures (``{id, name, created_at}``), without bodies."""
        return list(self._list("email-signatures/", page_size=1000))

    def get_signature(self, signature_id: str) -> Dict[str, Any]:
        """Get one signature, including ``html_template``."""
        return self._get(f"email-signatures/{signature_id}/")

    def create_signature(
        self, name: str, html_template: str
    ) -> Optional[Dict[str, Any]]:
        """Create a signature. ``html_template`` may use merge tags."""
        return self._post(
            "email-signatures/", json={"name": name, "html_template": html_template}
        )

    def update_signature(
        self, signature_id: str, name: str, html_template: str
    ) -> Optional[Dict[str, Any]]:
        """Replace a signature's name and body."""
        return self._put(
            f"email-signatures/{signature_id}/",
            json={"name": name, "html_template": html_template},
        )
