"""Analytics resource."""

from typing import Any, Dict

from .base import BaseResource


class AnalyticsResource(BaseResource):
    """Access application statistics and conversion data."""

    def statistics(self, *, start_date: str, end_date: str, **params: Any) -> Dict[str, Any]:
        """Get application statistics (counts by status, etc.).

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
        """
        params["start_date"] = start_date
        params["end_date"] = end_date
        resp = self._http.get(
            self._url("application-statistics/"), params=params
        )
        return resp.json()

    def status_conversion(self, **params: Any) -> Dict[str, Any]:
        """Get status conversion data."""
        resp = self._http.get(
            self._url("application-status-conversion/"), params=params
        )
        return resp.json()

    def conversion(self, *, start_date: str, end_date: str, **params: Any) -> Dict[str, Any]:
        """Get conversion funnel data.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
        """
        params["start_date"] = start_date
        params["end_date"] = end_date
        resp = self._http.get(self._url("conversion/"), params=params)
        return resp.json()
