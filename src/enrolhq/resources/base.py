"""Base resource with shared HTTP helpers."""

import copy
from typing import Any, Dict, List, Optional

from ..http import HttpClient
from ..pagination import (
    CursorPaginatedIterator,
    PaginatedIterator,
    PaginatedResponse,
)


class Replace:
    """Mark a value in a ``changes`` dict to replace, not merge.

    :func:`deep_merge` merges nested dicts key by key. Wrap a dict in
    ``Replace`` when the server looks it up as a whole — e.g. a country, which
    is resolved by ``id`` before ``alpha_2_code``, so merging
    ``{"alpha_2_code": "NZ"}`` into the current country would keep the old
    ``id`` and silently stay on the old country::

        client.school.update_fields(
            {"school": {"country": Replace({"alpha_2_code": "NZ"})}}
        )
    """

    def __init__(self, value: Any) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Replace({self.value!r})"


def deep_merge(base: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *base* with *changes* merged in.

    Nested dicts are merged key by key; every other value (including lists)
    in *changes* replaces the value in *base*, as does any value wrapped in
    :class:`Replace`. Used for read-modify-write on settings endpoints, which
    only accept a full PUT.
    """
    merged = copy.deepcopy(base)
    for key, value in changes.items():
        if isinstance(value, Replace):
            merged[key] = copy.deepcopy(value.value)
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


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

    def _list_cursor(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> CursorPaginatedIterator:
        """Return a CursorPaginatedIterator over all results (cursor pagination)."""
        return CursorPaginatedIterator(
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

    def _delete(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        if params:
            resp = self._http.delete(self._url(endpoint), params=params)
        else:
            resp = self._http.delete(self._url(endpoint))
        if not resp.content:
            return None
        return resp.json()

    def _read_modify_write(
        self, endpoint: str, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """GET a settings object, deep-merge *changes*, PUT the whole object.

        Settings endpoints have no PATCH and validate the PUT body in full,
        so partial updates must round-trip the current object.
        """
        current = self._get(endpoint)
        return self._put(endpoint, json=deep_merge(current, changes))
