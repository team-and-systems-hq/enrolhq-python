"""Pagination helpers for EnrolHQ list endpoints."""

import time
from collections import deque
from typing import Any, Deque, Dict, Iterator, List, Optional

from .exceptions import APIError, EnrolHQError, RateLimitError

#: Default safety limit to prevent infinite pagination loops.
MAX_PAGES = 10_000

#: Seconds to wait before the first retry of a failed page; doubles each time.
RETRY_BASE_DELAY = 5

#: The longest a single wait may be, in seconds. Backing off never waits
#: longer, and a 429 that asks for more is raised instead of waited out.
MAX_RETRY_WAIT = 300


def _is_transient(exc: EnrolHQError) -> bool:
    """Whether repeating the same GET could succeed.

    True for failures below HTTP (timeouts, dropped connections), for server
    errors and for rate limiting. False for every other HTTP error: a 403 or
    404 will be the same next time.
    """
    if not isinstance(exc, APIError):
        return True
    return exc.status_code == 429 or exc.status_code >= 500


def _retry_delay(exc: EnrolHQError, attempt: int) -> Optional[float]:
    """Seconds to wait before retry number *attempt* (0-based).

    ``None`` means do not retry: the server asked for a wait longer than
    :data:`MAX_RETRY_WAIT`, and sleeping that long would look like a hang.
    """
    if isinstance(exc, RateLimitError):
        try:
            asked = max(float(exc.retry_after), 0)
        except (TypeError, ValueError):
            pass  # no usable Retry-After header: back off as usual
        else:
            return asked if asked <= MAX_RETRY_WAIT else None
    return min(RETRY_BASE_DELAY * 2 ** attempt, MAX_RETRY_WAIT)


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

    A page that fails raises, and the iterator stays on that page, so calling
    ``next()`` again asks for the same page rather than skipping it. With
    ``retries``, a page that fails for a passing reason (a timeout, a dropped
    connection, a 5xx or a 429) is asked for again that many times first,
    waiting 5, 10, 20, ... seconds between tries (or as long as a 429's
    ``Retry-After`` says). No wait is longer than five minutes: a 429 that
    asks for more is raised straight away. ``timeout`` overrides the client's
    timeout for these requests.
    """

    def __init__(
        self,
        http: Any,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
        max_pages: int = MAX_PAGES,
        retries: int = 0,
        timeout: Any = None,
    ) -> None:
        if page_size < 1:
            raise ValueError("page_size must be >= 1")
        if retries < 0:
            raise ValueError("retries must be >= 0")
        self._http = http
        self._url = url
        self._params = dict(params or {})
        self._params["page_size"] = page_size
        self._max_pages = max_pages
        self._retries = retries
        self._timeout = timeout
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
        number = self._page + 1
        if number > self._max_pages:
            self._exhausted = True
            return
        data = self._get_page({**self._params, "page": number})
        # Only move on once the page has arrived (see the class docstring).
        self._page = number
        page = PaginatedResponse(data)
        self._total = page.count
        self._buffer = deque(page.results)
        if not page.next:
            self._exhausted = True

    def _get_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        kwargs = {} if self._timeout is None else {"timeout": self._timeout}
        attempt = 0
        while True:
            try:
                return self._http.get(self._url, params=params, **kwargs).json()
            except EnrolHQError as exc:
                if attempt >= self._retries or not _is_transient(exc):
                    raise
                delay = _retry_delay(exc, attempt)
                if delay is None:
                    raise
                time.sleep(delay)
                attempt += 1

    @property
    def total_count(self) -> int:
        """Total number of records (available after first page is fetched)."""
        if self._total is None:
            self._fetch_next()
        return self._total


class CursorPaginatedIterator:
    """Lazily iterates through a cursor-paginated endpoint.

    Some endpoints (e.g. ``audit/log/``) use DRF cursor pagination: each page
    is ``{"next": "<url-with-cursor>", "previous": ..., "results": [...]}`` with
    no ``count``. Unlike :class:`PaginatedIterator` (which sends ``page=N``),
    this follows the server-provided ``next`` URL verbatim — sending a page
    number would be ignored by the cursor endpoint and re-fetch the first page.

    Usage::

        for entry in CursorPaginatedIterator(http, url, params):
            print(entry)
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
        self._next_url: Optional[str] = url
        self._params: Optional[Dict[str, Any]] = dict(params or {})
        self._params["page_size"] = page_size
        self._max_pages = max_pages
        self._page = 0
        self._buffer: Deque[Dict[str, Any]] = deque()
        self._exhausted = False

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
        if self._next_url is None or self._page > self._max_pages:
            self._exhausted = True
            return
        # First request carries the filter params; the `next` URL returned by
        # the server already encodes cursor + page_size + filters, so follow it
        # verbatim with no extra params.
        resp = self._http.get(self._next_url, params=self._params)
        self._params = None
        data = resp.json()
        self._buffer = deque(data.get("results", []))
        self._next_url = data.get("next")
        if not self._next_url:
            self._exhausted = True
