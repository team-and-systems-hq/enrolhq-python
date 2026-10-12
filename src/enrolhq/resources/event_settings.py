"""Event settings resource: event kinds, reminders and auto-hide."""

import re
from typing import Any, Dict, List, Optional

from .base import BaseResource


class EventSettingsResource(BaseResource):
    """Read and write event settings (*Settings > Events*).

    ``event-settings/`` holds ``event_kind_options`` (the "kind" every event
    must reference — new schools are seeded with Junior, Senior and Open
    Day), plus ``event_autohide_duration`` (hours),
    ``event_booking_mark_not_attended_duration`` (1-8 hours),
    ``event_booking_reminder_hours``, ``event_reminder_hours``,
    ``event_booking_availability_policy`` (``UNTIL_SESSION_START`` or
    ``UNTIL_SESSION_END``) and ``event_embed_redirect_url``.

    ``event_kind_options`` is replaced wholesale on PUT: kinds without an
    ``id`` are created, kinds you leave out are deleted (400 if an event uses
    one). Requires ``edit_events_settings`` (Registrar role or superuser).
    """

    def get(self) -> Dict[str, Any]:
        """Get the event settings object (including kind slugs)."""
        return self._get("event-settings/")

    def update(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Replace the event settings (full PUT). Start from :meth:`get`."""
        return self._put("event-settings/", json=data)

    def update_fields(self, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Change some settings: GET, deep-merge *changes*, PUT the result."""
        return self._read_modify_write("event-settings/", changes)

    def kind_options(self) -> List[Dict[str, Any]]:
        """List event kinds (``{id, label, is_enabled, created_at}``).

        Uses ``event-kind-options/``, which omits slugs; :meth:`get` has them.
        """
        return list(self._list("event-kind-options/", page_size=1000))

    def ensure_kinds(
        self, labels: List[str], *, remove_others: bool = False
    ) -> List[Dict[str, Any]]:
        """Make sure event kinds with these labels exist and are enabled.

        Existing kinds are matched by label (case-insensitive) and kept with
        their ``id``; missing ones are created with a slug derived from the
        label. With ``remove_others=True`` kinds not in *labels* are deleted
        (the PUT fails with 400 if an event still uses one).

        Parents filter events by kind slug, so a ``ValueError`` is raised
        before anything is written if a new label has no ASCII letters or
        digits to build a slug from, or its slug matches another kind's
        (labels differing only in punctuation). Use :meth:`update` with an
        explicit ``slug`` for those.

        Returns:
            The resulting ``event_kind_options`` list.
        """
        settings = self.get()
        current = settings.get("event_kind_options", [])
        by_label = {k["label"].lower(): k for k in current}
        wanted = []
        for label in labels:
            existing = by_label.get(label.lower())
            if existing:
                wanted.append({**existing, "is_enabled": True})
            else:
                slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:50]
                wanted.append({"label": label, "slug": slug, "is_enabled": True})
        if not remove_others:
            wanted_labels = {label.lower() for label in labels}
            wanted += [k for k in current if k["label"].lower() not in wanted_labels]
        _check_slugs(wanted)
        settings["event_kind_options"] = wanted
        result = self.update(settings) or self.get()
        return result.get("event_kind_options", [])


def _check_slugs(kinds: List[Dict[str, Any]]) -> None:
    """Raise if a new kind (no ``id``) has an empty slug or shares another kind's."""
    for i, kind in enumerate(kinds):
        if "id" in kind:
            continue
        label, slug = kind["label"], kind["slug"]
        if not slug:
            raise ValueError(
                f"Can't derive a slug from event kind label {label!r}; "
                "add it with update() and an explicit slug"
            )
        clash = next(
            (k for j, k in enumerate(kinds) if j != i and k.get("slug") == slug), None
        )
        if clash:
            raise ValueError(
                f"Event kinds {clash['label']!r} and {label!r} would share the "
                f"slug {slug!r}; rename one or set slugs with update()"
            )
