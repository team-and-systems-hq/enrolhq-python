"""Base resource with shared HTTP helpers."""

from typing import Any, Dict, List, Optional

from ..http import HttpClient
from ..pagination import PaginatedIterator, PaginatedResponse


class BaseResource:
    """Base class for all API resources."""

    def __init__(self, http: HttpClient, base_url: str) -> None:
        self._http = http
        self._base_url = base_url

    def _url(self, path: str = "") -> str:
        return self._base_url + path

    def _list(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> PaginatedIterator:
        """Return a PaginatedIterator over all results."""
        return PaginatedIterator(
            self._http, self._url(endpoint), params=params, page_size=page_size
        )

    def _list_page(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> PaginatedResponse:
        """Return a single PaginatedResponse page."""
        params = dict(params or {})
        params["page"] = page
        params["page_size"] = page_size
        resp = self._http.get(self._url(endpoint), params=params)
        return PaginatedResponse(resp.json())

    def _get(self, endpoint: str) -> Any:
        resp = self._http.get(self._url(endpoint))
        return resp.json()

    def _post(
        self,
        endpoint: str,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        resp = self._http.post(
            self._url(endpoint), json=json, params=params, **kwargs
        )
        if not resp.content:
            return None
        return resp.json()

    def _put(self, endpoint: str, json: Any = None) -> Optional[Dict[str, Any]]:
        resp = self._http.put(self._url(endpoint), json=json)
        if not resp.content:
            return None
        return resp.json()

    def _delete(self, endpoint: str) -> Optional[Dict[str, Any]]:
        resp = self._http.delete(self._url(endpoint))
        if not resp.content:
            return None
        return resp.json()
