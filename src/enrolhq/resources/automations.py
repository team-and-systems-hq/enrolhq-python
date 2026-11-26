"""Automations: what EnrolHQ does by itself when something happens."""

from typing import Any, Dict, List, Optional

from ..pagination import PaginatedIterator
from .base import BaseResource, deep_merge


class AutomationsResource(BaseResource):
    """Automations (*Settings > Automations*, ``followups/`` in the API).

    An automation waits for an event and then acts on the student's record::

        {
            "name": "Enquiry follow-up",
            "group": None,
            "trigger": {
                "trigger_event_codes": ["ENQUIRY_FORM_SUBMITTED"],
                "cancel_event_codes": ["EOI_SUBMITTED"],
                "delay_hours": 72,
                "is_active": False,
            },
            "email_templates": ["<template id>"],
            "carer_sms_templates": [],
            "target_application_status": None,
            "identity_lock_action": "",
            "custom_categories_options": [],
            "exclude_application_statuses": [],
            "allowed_application_statuses": [],
            "allowed_entry_grades": [],
            "allowed_entry_years": [],
            "allowed_custom_categories_options": [],
            "allowed_attendance_types": [],
            "allowed_campuses": [],
        }

    ``trigger_event_codes`` start it and ``cancel_event_codes`` stop a pending
    run. :meth:`event_codes` lists the codes. A code in its ``complex`` list
    needs the id of the thing it is about after a colon: a custom form id for
    the ``custom_form`` codes, an event kind id for ``event_booking``, a lead
    reference id for ``lead`` and an interview type id for ``interview``,
    for example ``EVENT_BOOKING_FORM_SUBMITTED:<event kind id>``.

    The actions are ``email_templates``, ``carer_sms_templates``,
    ``target_application_status``, ``identity_lock_action`` (``""``, ``SET``
    or ``RESET``) and ``custom_categories_options``. The ``allowed_*`` and
    ``exclude_application_statuses`` lists narrow which students it runs for;
    an empty list means no limit.

    An active automation emails families without anyone pressing send, and
    the server refuses to activate one that has no action. Turning one on
    only affects events from then on. Writes are a full PUT and need the
    automation permissions (school Admin or superuser).
    """

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through automations.

        Filters: ``search`` (name prefix), ``is_active`` and ``group``.
        """
        return self._list("followups/", params=filters, page_size=page_size)

    def get(self, automation_id: str) -> Dict[str, Any]:
        """Get one automation."""
        return self._get(f"followups/{automation_id}/")

    def find(self, name: str) -> List[Dict[str, Any]]:
        """Return the automations with this name (case-insensitive).

        Names are not unique, so check for exactly one before changing it.
        """
        needle = name.strip().lower()
        return [
            row
            for row in self.list(page_size=1000)
            if (row.get("name") or "").strip().lower() == needle
        ]

    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create an automation. Every key in the class example is required."""
        return self._post("followups/", json=data)

    def update(
        self, automation_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Replace an automation (full PUT). Prefer :meth:`update_fields`."""
        return self._put(f"followups/{automation_id}/", json=data)

    def update_fields(
        self, automation_id: str, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Change some fields: GET, merge *changes*, PUT. Lists are replaced."""
        return self.update(automation_id, deep_merge(self.get(automation_id), changes))

    def set_active(
        self, automation_id: str, is_active: bool
    ) -> Optional[Dict[str, Any]]:
        """Turn an automation on or off. Turning it off cancels pending runs."""
        return self.update_fields(automation_id, {"trigger": {"is_active": is_active}})

    def delete(self, automation_id: str) -> None:
        """Delete an automation. It must be turned off first."""
        self._delete(f"followups/{automation_id}/")

    def groups(self) -> List[Dict[str, Any]]:
        """List automation groups (``{id, name, position, has_followups}``)."""
        return list(self._list("followup-groups/", page_size=1000))

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
        saved = self._put("followup-groups/batch_update/", json=[*body, {"name": wanted}])
        return next(group for group in saved or [] if group.get("name") == wanted)

    def event_codes(self) -> Dict[str, Any]:
        """Return the event codes an automation can use.

        ``choices`` is a list of ``[code, label]`` with the school's own
        wording. ``complex`` lists the codes that need an id after a colon,
        and ``custom_form``, ``event_booking``, ``lead``, ``interview`` and
        ``review`` say which kind of id each takes. ``reminder_hours_map``
        gives the hours before the date at which each reminder code fires.
        """
        return self._get("followups/system_event_codes/")
