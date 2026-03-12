"""Event bookings resource (staff-side)."""

from typing import Any, Dict, Optional

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class EventBookingsResource(BaseResource):
    """Manage event bookings."""

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through all event bookings."""
        return self._list(
            "staff-event-bookings/", params=filters, page_size=page_size
        )

    def list_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of event bookings."""
        return self._list_page(
            "staff-event-bookings/",
            params=filters,
            page=page,
            page_size=page_size,
        )

    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new event booking."""
        return self._post("staff-event-bookings/", json=data)

    def update(
        self, booking_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update an event booking."""
        return self._put(f"staff-event-bookings/{booking_id}/", json=data)

    def most_recent_for(self, **params: Any) -> Any:
        """Get the most recent booking for a given filter."""
        resp = self._http.get(
            self._url("staff-event-bookings/most_recent_for/"), params=params
        )
        return resp.json()
