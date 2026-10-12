"""Metafields resource (per-model field configuration)."""

from typing import Any, Dict, List, Optional

from .base import BaseResource, deep_merge


class MetafieldsResource(BaseResource):
    """Access field configuration ("metafields") for the school.

    The ``metafields/`` endpoint returns a single object describing how each
    field on each model (``student``, ``parent``, ``doctor``, ``guardian``,
    ``emergency_contact``, ``medical_data``, ...) is configured. For every
    field there is a ``label`` plus ``enabled`` and ``mandatory`` maps keyed
    by scope:

    - ``enr``   – enrolment form
    - ``eoi``   – expression of interest / GPA form
    - ``enq``   – enquiry form
    - ``evt``   – event booking
    - ``cust``  – custom form
    - ``admin`` – admin / staff view (``enabled`` only)
    """

    def get(self, **params: Any) -> Dict[str, Any]:
        """Get the full metafields object.

        Returns:
            A dict with ``field_settings`` (the school's configured fields)
            and ``default_field_settings`` (the platform defaults).
        """
        resp = self._http.get(self._url("metafields/"), params=params)
        return resp.json()

    def field_settings(self, **params: Any) -> Dict[str, Any]:
        """Return only the configured ``field_settings`` map (by model)."""
        return self.get(**params).get("field_settings", {})

    def default_field_settings(self, **params: Any) -> Dict[str, Any]:
        """Return only the ``default_field_settings`` map (platform defaults)."""
        return self.get(**params).get("default_field_settings", {})

    # ── Writes ───────────────────────────────────────────────
    #
    # Writes need ``edit_meta_fields_settings`` (school Admin or superuser).

    def update_field(
        self, block: str, field: str, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update one field's settings (``PUT metafields/``, one field per call).

        Starts from the field's current settings so ``label``, ``enabled``
        and ``mandatory`` (all required) are always sent; *changes* are
        merged on top (``enabled``/``mandatory`` merge per form code).

        Notes:
            - ``label`` needs at least 3 Latin characters and is stored
              lower-cased.
            - Keys the field does not already support are ignored.
            - For choice fields, ``options`` replaces the list; options
              families have already picked move to ``disabled_options``.

        Example — the "How did you hear about us?" options::

            client.metafields.update_field("parent", "how_hear", {
                "options": ["Word of mouth", "Open Day", "Website", "Other"],
                "mandatory": {"enq": False},
            })

        Returns:
            The field's updated settings.
        """
        current = self.field_settings().get(block, {}).get(field)
        if current is None:
            raise KeyError(f"No metafield {block}.{field}")
        body = deep_merge(current, changes)
        body.pop("disabled_options", None)
        body.update({"block": block, "field": field})
        return self._put("metafields/", json=body)

    def create_field(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a field (``POST metafields/``; questionnaire blocks only)."""
        return self._post("metafields/", json=data)

    def delete_field(self, block: str, field: str) -> None:
        """Delete a custom field (``DELETE metafields/?block=&field=``)."""
        self._delete("metafields/", params={"block": block, "field": field})

    def toggle_block(
        self, block_name: str, form_code: str, is_enabled: bool
    ) -> Optional[Dict[str, Any]]:
        """Enable or disable a whole block on the ``"enr"`` or ``"eoi"`` form."""
        return self._post(
            "metafields/toggle_block/",
            json={"block_name": block_name, "form_code": form_code, "is_enabled": is_enabled},
        )

    def mutate_ordering(
        self, block_name: str, ordering: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Reorder a block's fields (*ordering* lists every field name)."""
        return self._post(
            "metafields/mutate_ordering/",
            json={"block_name": block_name, "ordering": ordering},
        )
