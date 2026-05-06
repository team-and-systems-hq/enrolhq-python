"""Applications resource."""

from typing import Any, Dict, List, Optional, Union

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class ApplicationsResource(BaseResource):
    """Interact with student applications."""

    # ── List / Get ──────────────────────────────────────────────

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through all applications matching *filters*.

        Supported filters: entry_year, entry_grade, application_statuses,
        search, campus, gender, first_name, last_name, dob, is_favorite,
        ordering, has_external_id, external_id,
        exclude_application_statuses, exclude_docs, etc.
        """
        return self._list("applications-list/", params=filters, page_size=page_size)

    def list_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of applications."""
        return self._list_page(
            "applications-list/", params=filters, page=page, page_size=page_size
        )

    def count(self, **filters: Any) -> int:
        """Return the total count of applications matching *filters*."""
        resp = self._http.get(self._url("applications-list/count/"), params=filters)
        return resp.json().get("count", 0)

    def get(self, application_id: str) -> Dict[str, Any]:
        """Get full detail for a single application."""
        return self._get(f"applications/{application_id}/")

    # ── Create / Update ─────────────────────────────────────────

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new application (CreateStudentProfile schema)."""
        return self._post("applications/", json=data)

    def update(self, application_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Full-replacement update (PUT) of an application.

        WARNING: This is a PUT, not a PATCH. You must send the complete
        application object. Omitted fields may be reset to defaults.
        Recommended pattern: get() -> modify dict -> update().
        """
        return self._put(f"applications/{application_id}/", json=data)

    def attach(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Attach a student to an existing parent."""
        return self._post("applications/attach/", json=data)

    # ── Actions ─────────────────────────────────────────────────

    def change_status(
        self,
        application_ids: List[str],
        status: Union[int, "ApplicationStatus"],
    ) -> Optional[Dict[str, Any]]:
        """Change the status of one or more applications.

        Args:
            application_ids: List of application UUIDs.
            status: Target ApplicationStatus value.
        """
        ids = [str(i) for i in application_ids]
        # The API expects repeated `id` query params (e.g. ?id=a&id=b), not
        # `id__in=`. Without a recognised filter the endpoint refuses with
        # "Bulk action on all items is not allowed".
        return self._post(
            "applications-list/change_status/",
            json={"application_status": int(status)},
            params={"id": ids[0] if len(ids) == 1 else ids},
        )

    def send_mail(
        self, application_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Send an email to the application's parent."""
        return self._post(f"applications/{application_id}/send_mail/", json=data)

    def email_preview(
        self, application_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Preview an email before sending."""
        return self._post(f"applications/{application_id}/email_preview/", json=data)

    def toggle_favorite(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Toggle the favourite flag on an application."""
        return self._post(f"applications/{application_id}/toggle_favorite/")

    def regenerate_sid(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Regenerate the student ID."""
        return self._post(f"applications/{application_id}/regenerate_sid/")

    def book_interview(
        self, application_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Book an interview for the application."""
        return self._post(
            f"applications/{application_id}/book_interview/", json=data
        )

    def cancel_interview(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Cancel an interview booking."""
        return self._post(
            f"applications/{application_id}/cancel_interview_booking/"
        )

    def send_enrolment_invite(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Send an enrolment invite."""
        return self._post(
            f"applications/{application_id}/send_enrolment_invite/"
        )

    def decline_by_parent(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Decline an application (parent-initiated)."""
        return self._post(
            f"applications/{application_id}/decline_student_by_parent/"
        )

    def decline_by_staff(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Decline an application (staff-initiated)."""
        return self._post(
            f"applications/{application_id}/decline_student_by_staff/"
        )

    def cancel_decline_by_parent(
        self, application_id: str
    ) -> Optional[Dict[str, Any]]:
        """Cancel a parent-initiated decline."""
        return self._post(
            f"applications/{application_id}/cancel_decline_student_by_parent/"
        )

    def cancel_decline_by_staff(
        self, application_id: str
    ) -> Optional[Dict[str, Any]]:
        """Cancel a staff-initiated decline."""
        return self._post(
            f"applications/{application_id}/cancel_decline_student_by_staff/"
        )

    # ── Offer Management ────────────────────────────────────────

    def cancel_offer(
        self, application_id: str, offer_kind: str
    ) -> Optional[Dict[str, Any]]:
        """Cancel an offer."""
        return self._post(
            f"applications/{application_id}/cancel_offer/{offer_kind}/"
        )

    def delay_offer(
        self, application_id: str, offer_kind: str
    ) -> Optional[Dict[str, Any]]:
        """Delay an offer."""
        return self._post(
            f"applications/{application_id}/delay_offer/{offer_kind}/"
        )

    # ── Parent Management ───────────────────────────────────────

    def create_non_user_parent(
        self, application_id: str, data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a non-user parent for the application."""
        return self._post(
            f"applications/{application_id}/create_non_user_parent/", json=data
        )

    def delete_non_user_parent(
        self, application_id: str
    ) -> Optional[Dict[str, Any]]:
        """Delete the non-user parent from the application."""
        return self._post(
            f"applications/{application_id}/delete_non_user_parent/"
        )

    def switch_parents(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Swap the primary and secondary parents."""
        return self._post(f"applications/{application_id}/switch_parents/")

    # ── Bulk Operations ─────────────────────────────────────────

    def bulk_send_email(
        self, data: Dict[str, Any], **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Send bulk email to applications matching filters."""
        return self._post(
            "applications-list/bulk_send_email/", json=data, params=filters
        )

    def bulk_send_sms(
        self, data: Dict[str, Any], **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Send bulk SMS to applications matching filters."""
        return self._post(
            "applications-list/bulk_send_sms/", json=data, params=filters
        )

    def bulk_note(self, text: str, **filters: Any) -> Optional[Dict[str, Any]]:
        """Add a note to all applications matching filters."""
        return self._post(
            "applications-list/bulk_note/", json={"text": text}, params=filters
        )

    def bulk_enrolment_invite(self, **filters: Any) -> Optional[Dict[str, Any]]:
        """Send enrolment invites to applications matching filters."""
        return self._post(
            "applications-list/bulk_enrolment_invite/", params=filters
        )

    def bulk_close(self, **filters: Any) -> Optional[Dict[str, Any]]:
        """Close applications matching filters."""
        return self._post("applications-list/bulk_close/", params=filters)

    def bulk_reopen(self, **filters: Any) -> Optional[Dict[str, Any]]:
        """Reopen applications matching filters."""
        return self._post("applications-list/bulk_reopen/", params=filters)

    def bulk_make_offer(
        self, offer_kind: str, **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Make an offer to applications matching filters."""
        return self._post(
            f"applications-list/bulk_make_offer/{offer_kind}/", params=filters
        )

    def bulk_change_campus(
        self, data: Dict[str, Any], **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Change campus for applications matching filters."""
        return self._post(
            "applications-list/bulk_change_campus/", json=data, params=filters
        )

    def bulk_make_manual_payments(
        self, data: Dict[str, Any], **filters: Any
    ) -> Optional[Dict[str, Any]]:
        """Create manual payments for applications matching filters."""
        return self._post(
            "applications-list/bulk_make_manual_payments/",
            json=data,
            params=filters,
        )

    def merge_profiles(
        self,
        profile_to_keep: str,
        profile_not_to_keep: str,
        swap_parents: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Merge two student profiles."""
        return self._post(
            "applications-list/merge_profiles/",
            json={
                "profile_to_keep": str(profile_to_keep),
                "profile_not_to_keep": str(profile_not_to_keep),
                "is_profile_not_to_keep_parents_swapped": swap_parents,
            },
        )

    def delete_profiles(self, **filters: Any) -> Optional[Dict[str, Any]]:
        """Delete applications matching filters."""
        return self._post(
            "applications-list/delete-profiles/", params=filters
        )
