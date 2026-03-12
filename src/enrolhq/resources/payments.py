"""Payments resource."""

from typing import Any, Dict, List, Optional

from .base import BaseResource


class PaymentsResource(BaseResource):
    """Manage order lines and manual payments."""

    def order_lines(
        self, student_profile_id: str, payment_kind: Optional[str] = None
    ) -> Any:
        """Get order lines for a student profile.

        Args:
            student_profile_id: UUID of the student profile.
            payment_kind: Optional filter (e.g. "enr-f", "enr-a").
        """
        params: Dict[str, Any] = {"student_profile": student_profile_id}
        if payment_kind:
            params["payment_kind"] = payment_kind
        resp = self._http.get(self._url("payment/order-lines/"), params=params)
        return resp.json()

    def batch_update_order_lines(
        self,
        student_profile_id: str,
        payment_kind: str,
        paying_parent_id: str,
        data: List[Dict[str, Any]],
    ) -> Any:
        """Batch update order lines for a student profile.

        Args:
            student_profile_id: UUID of the student profile.
            payment_kind: Payment kind string.
            paying_parent_id: UUID of the paying parent.
            data: List of order line objects.
        """
        params = {
            "student_profile": student_profile_id,
            "payment_kind": payment_kind,
            "paying_parent": paying_parent_id,
        }
        resp = self._http.post(
            self._url("payment/order-lines/batch_update_for_profile/"),
            json=data,
            params=params,
        )
        return resp.json()
