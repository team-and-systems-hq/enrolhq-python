"""Pagination helpers for EnrolHQ list endpoints."""

from collections import deque
from typing import Any, Deque, Dict, Iterator, List, Optional

#: Default safety limit to prevent infinite pagination loops.
MAX_PAGES = 10_000


class PaginatedResponse:
    """A single page of results from a paginated endpoint.

    Supports iteration and len() for convenience::

        page = client.applications.list_page(page_size=10)
        for app in page:
            print(app["first_name"])
        print(f"Got {len(page)} of {page.count} total")
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        self.count: int = data.get("count", 0)
        self.next: Optional[str] = data.get("next")
        self.previous: Optional[str] = data.get("previous")
        self.results: List[Dict[str, Any]] = data.get("results", [])

    def __repr__(self) -> str:
        return f"PaginatedResponse(count={self.count}, page_size={len(self.results)})"

    def __len__(self) -> int:
        """Number of results on this page."""
        return len(self.results)

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over results on this page."""
        return iter(self.results)

    def __getitem__(self, index: Any) -> Any:
        """Index into results on this page."""
        return self.results[index]

    def __bool__(self) -> bool:
        """True if this page has any results."""
        return len(self.results) > 0


class PaginatedIterator:
    """Lazily iterates through all pages of a paginated endpoint.

    Usage::

        for item in PaginatedIterator(http, url, params):
            print(item)
    """

    def __init__(
        self,
        http: Any,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
        max_pages: int = MAX_PAGES,
    ) -> None:
        if page_size < 1:
            raise ValueError("page_size must be >= 1")
        self._http = http
        self._url = url
        self._params = dict(params or {})
        self._params["page_size"] = page_size
        self._max_pages = max_pages
        self._page = 0
        self._buffer: Deque[Dict[str, Any]] = deque()
        self._exhausted = False
        self._total: Optional[int] = None

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return self

    def __next__(self) -> Dict[str, Any]:
        if self._buffer:
            return self._buffer.popleft()
        if self._exhausted:
            raise StopIteration
        self._fetch_next()
        if not self._buffer:
            raise StopIteration
        return self._buffer.popleft()

    def _fetch_next(self) -> None:
        self._page += 1
        if self._page > self._max_pages:
            self._exhausted = True
            return
        params = {**self._params, "page": self._page}
        resp = self._http.get(self._url, params=params)
        data = resp.json()
        page = PaginatedResponse(data)
        self._total = page.count
        self._buffer = deque(page.results)
        if not page.next:
            self._exhausted = True

    @property
    def total_count(self) -> int:
        """Total number of records (available after first page is fetched)."""
        if self._total is None:
            self._fetch_next()
        return self._total
