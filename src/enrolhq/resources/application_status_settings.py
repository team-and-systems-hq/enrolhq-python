"""Enrolment journey stages: the school's application statuses."""

from typing import Any, Dict, List, Optional

from .base import BaseResource

_WRITABLE = (
    "id",
    "status_label",
    "is_status_enabled",
    "is_parent_dashboard_stage_visible",
)


class ApplicationStatusSettingsResource(BaseResource):
    """Enrolment journey stages (*Settings > Enrolment Journey Stages*).

    Every school has one row per :class:`~enrolhq.ApplicationStatus`::

        {
            "id": "<uuid>",
            "application_status": 9,
            "status_label": "Waiting Pool",
            "default_status_label": "Wait List",
            "is_status_enabled": True,
            "is_status_enabled_editable": True,
            "is_parent_dashboard_stage_visible": False,
        }

    The order of the list is the order of the journey: staff see the stages
    in this order, and parents see the ones with
    ``is_parent_dashboard_stage_visible`` as the steps of their journey.
    ``is_status_enabled`` can only change where
    ``is_status_enabled_editable`` is true; the server keeps the current
    value for the others. Emails, automations and forms refer to a stage by
    its ``application_status`` number, so renaming one does not break them.

    The server only takes the whole list, in the order wanted. Reading and
    writing both need *View/Edit Enrolment Journey Stages* (school Admin or
    superuser); ``client.reference_data.application_status_settings()`` is
    the same endpoint.
    """

    def list(self) -> List[Dict[str, Any]]:
        """Return every stage, in journey order."""
        return list(self._list("application-status-settings/", page_size=1000))

    def update(self, rows: List[Dict[str, Any]]) -> Any:
        """Replace the stages (full PUT). Prefer :meth:`update_fields`.

        *rows* must hold every stage once, each with its ``id``; their order
        becomes the journey order.
        """
        body = [{key: row[key] for key in _WRITABLE if key in row} for row in rows]
        return self._put("application-status-settings/batch_update/", json=body)

    def update_fields(
        self,
        changes: Optional[Dict[int, Dict[str, Any]]] = None,
        *,
        order: Optional[List[int]] = None,
    ) -> Any:
        """Change some stages and, optionally, their order.

        *changes* maps an ``application_status`` number to the keys to
        change, for example ``{9: {"status_label": "Waiting Pool"}}``.

        *order* lists ``application_status`` numbers in the order wanted.
        Those stages are rearranged among the places they hold now and every
        other stage stays where it is, so ``order=[12, 13]`` puts stage 12
        ahead of stage 13 without moving anything else.

        Raises ``ValueError`` for an unknown status or a key that cannot be
        changed, before anything is sent.
        """
        for fields in (changes or {}).values():
            unknown_keys = sorted(set(fields) - set(_WRITABLE[1:]))
            if unknown_keys:
                raise ValueError(
                    f"Cannot change {unknown_keys[0]!r}. "
                    f"Keys: {', '.join(_WRITABLE[1:])}"
                )
        rows = self.list()
        known = {row["application_status"] for row in rows}
        wanted = list(order or [])
        unknown = [code for code in [*(changes or {}), *wanted] if code not in known]
        if unknown:
            raise ValueError(f"Unknown application status: {unknown[0]!r}")
        if len(set(wanted)) != len(wanted):
            raise ValueError("order names a stage twice")
        by_status = {row["application_status"]: row for row in rows}
        places = [
            index
            for index, row in enumerate(rows)
            if row["application_status"] in set(wanted)
        ]
        for index, code in zip(places, wanted):
            rows[index] = by_status[code]
        rows = [
            {**row, **(changes or {}).get(row["application_status"], {})}
            for row in rows
        ]
        return self.update(rows)
