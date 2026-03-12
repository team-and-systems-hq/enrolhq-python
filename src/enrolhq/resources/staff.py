"""Staff resource."""

from typing import Any, Dict, Optional

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class StaffResource(BaseResource):
    """List and manage staff members."""

    def list(self, *, page_size: int = 100, **filters: Any) -> PaginatedIterator:
        """Auto-paginate through all staff members."""
        return self._list("staff/", params=filters, page_size=page_size)

    def list_page(
        self, *, page: int = 1, page_size: int = 100, **filters: Any
    ) -> PaginatedResponse:
        """Fetch a single page of staff members."""
        return self._list_page(
            "staff/", params=filters, page=page, page_size=page_size
        )

    def get(self, staff_id: str) -> Dict[str, Any]:
        """Get a single staff member by ID."""
        return self._get(f"staff/{staff_id}/")

    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new staff member."""
        return self._post("staff/", json=data)

    def update(
        self, staff_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a staff member."""
        return self._put(f"staff/{staff_id}/", json=data)

    def toggle_active(self, staff_id: str) -> Optional[Dict[str, Any]]:
        """Toggle active status of a staff member."""
        return self._post(f"staff/{staff_id}/toggle_active/")
