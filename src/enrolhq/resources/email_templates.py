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


class EmailTemplatesResource(BaseResource):
    """Email templates (*Settings > Email Templates*).

    A template has a ``name``, a ``subject_template`` and an
    ``html_template``, both Django templates that use the merge tags listed by
    :meth:`tags`. ``recipient_type`` is one of :data:`RECIPIENT_TYPES` and
    cannot change after creation.

    Who sends a template depends on ``is_system``. A system template (sign-in
    codes, email verification, offer acceptance links, payment receipts) is
    sent by EnrolHQ itself and cannot be archived or deleted. Every other
    template, including built-in kinds such as ``ENQUIRY_PARENT``, goes out
    only when an automation (:class:`AutomationsResource`) or a staff member
    sends it. More templates of any non-system ``kind`` can be created;
    ``CUSTOM`` and ``MARKETING`` are the usual ones.

    Names are not unique: a school often has the same template once per
    recipient type, so :meth:`find` returns a list.

    The server renders both templates on save and answers 400 for a template
    it cannot render. Writes are a full PUT; :meth:`update_fields` does the
    read-modify-write. Reading needs any staff user, writing needs the email
    template permissions (school Admin or superuser).
    """

    def list(
        self,
        *,
        page_size: int = 100,
        return_html_template: bool = False,
        **filters: Any,
    ) -> PaginatedIterator:
        """Auto-paginate through the school's templates.

        Rows leave out ``html_template`` unless ``return_html_template`` is
        true, which makes the response slow and large. Filters: ``search``
        (name prefix), ``is_archived``, ``kinds``, ``groups`` and
        ``recipient_types``.
        """
        params = dict(filters)
        if return_html_template:
            params["return_html_template"] = "true"
        return self._list("email-templates/", params=params, page_size=page_size)

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

        Required keys: ``name``, ``kind`` (any non-system kind, normally
        ``CUSTOM`` or ``MARKETING``), ``recipient_type``, ``group`` (a group
        id from :meth:`groups`), ``subject_template``, ``html_template``,
        ``from_email`` (may be ``""`` unless the recipient is staff),
        ``staff_recipients``, ``staff_reply_to_type`` (``""``,
        ``PRIMARY_CARER`` or ``CAMPUS_EMAIL``), ``attachments``,
        ``signature`` (an id or ``None``), ``is_base_render_needed`` and
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
        """Flip a template between archived and not. Prefer :meth:`set_archived`.

        The server answers 400 for a system template and for one an
        automation uses.
        """
        return self._post(f"email-templates/{template_id}/toggle_archive/")

    def set_archived(self, template_id: str, archived: bool) -> Dict[str, Any]:
        """Archive a template or bring it back. Safe to repeat."""
        current = self.get(template_id)
        if bool(current.get("is_archived")) == archived:
            return current
        return self.toggle_archive(template_id) or current

    def delete(self, template_id: str) -> None:
        """Delete an archived template.

        The server answers 400 unless the template is archived first, and
        for a system template or one an automation uses.
        """
        self._delete(f"email-templates/{template_id}/")

    def groups(self) -> List[Dict[str, Any]]:
        """List template groups (``{id, name, position, is_system, has_templates}``)."""
        return list(self._list("email-template-groups/", page_size=1000))

    def ensure_group(self, name: str) -> Dict[str, Any]:
        """Return the group with this name, adding it after the others if missing.

        The server only takes the whole list of groups, so adding one sends
        every group back. Do not run this concurrently, or while someone is
        editing groups in the dashboard: the later write replaces the earlier
        one and removes an empty group it did not know about.
        """
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
