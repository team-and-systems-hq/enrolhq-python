"""Payment settings resource (currency, GST, processor and fee lists)."""

from typing import Any, Dict, Optional

from .base import BaseResource


class PaymentSettingsResource(BaseResource):
    """Read and write payment settings (*Settings > Payments*).

    ``payment/settings/`` holds ``currency`` (e.g. ``AUD``, ``NZD``),
    ``currency_symbol``, ``gst_percent`` (e.g. ``"15.0"`` for New Zealand),
    the ``payment_processor`` and its credentials, card surcharges and the
    fee lists (``entry_grade_fees``, ``sibling_fees``, ``grant_fees``,
    ``default_order_lines``, ``form_payment_settings``, ``attendance_types``).

    The PUT is validated in full and every list is replaced wholesale —
    ``attendance_types: []`` deletes the school's attendance types. Secret
    fields read back as ``{"masked": "****1234"}``; ``masked`` is read-only,
    so sending them back unchanged keeps the stored secret (send
    ``{"secret": "..."}`` to change one). Requires ``change_paymentsettings``.
    """

    def get(self) -> Dict[str, Any]:
        """Get the payment settings object."""
        return self._get("payment/settings/")

    def update(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Replace the payment settings (full PUT). Start from :meth:`get`."""
        return self._put("payment/settings/", json=data)

    def update_fields(self, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Change some settings: GET, deep-merge *changes*, PUT the result::

            client.payment_settings.update_fields(
                {"currency": "NZD", "gst_percent": "15.0"}
            )
        """
        return self._read_modify_write("payment/settings/", changes)
