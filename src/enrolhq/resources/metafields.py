"""Metafields resource (per-model field configuration)."""

from typing import Any, Dict

from .base import BaseResource


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
