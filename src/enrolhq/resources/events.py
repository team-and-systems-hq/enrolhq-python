"""Events resource (staff-side)."""

from typing import Any, Dict, List, Optional

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class EventsResource(BaseResource):
    """CRUD operations on staff events."""

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through all staff events."""
        return self._list("staff-events/", params=filters, page_size=page_size)

    def list_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of staff events."""
        return self._list_page(
            "staff-events/", params=filters, page=page, page_size=page_size
        )

    def get(self, event_id: str) -> Dict[str, Any]:
        """Get a single event by ID."""
        return self._get(f"staff-events/{event_id}/")

    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new event."""
        return self._post("staff-events/", json=data)

    def update(self, event_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an event."""
        return self._put(f"staff-events/{event_id}/", json=data)

    def delete(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Delete an event."""
        return self._delete(f"staff-events/{event_id}/")

    def preview(self, **params: Any) -> Any:
        """Preview upcoming events."""
        params.setdefault("page_size", 1000)
        resp = self._http.get(self._url("staff-events/preview/"), params=params)
        return resp.json()
