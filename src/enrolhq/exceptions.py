"""EnrolHQ SDK exception hierarchy."""

from typing import Any, Optional


class EnrolHQError(Exception):
    """Base exception for all EnrolHQ SDK errors."""


class APIError(EnrolHQError):
    """Raised for non-success HTTP responses."""

    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        response: Optional[object] = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.response = response
        msg = f"HTTP {status_code}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class AuthenticationError(APIError):
    """Raised when authentication fails (401)."""

    def __init__(
        self,
        detail: Any = None,
        response: Optional[object] = None,
    ) -> None:
        super().__init__(401, detail=detail, response=response)


class NotFoundError(APIError):
    """Raised when a resource is not found (404)."""


class ValidationError(APIError):
    """Raised for validation errors (400)."""


class ForbiddenError(APIError):
    """Raised when the user lacks permission (403)."""


class RateLimitError(APIError):
    """Raised when rate-limited (429).

    The ``retry_after`` attribute contains the value of the Retry-After
    header (as a string), or *None* if the header was absent.
    """

    def __init__(
        self,
        status_code: int = 429,
        detail: Any = None,
        response: Optional[object] = None,
        retry_after: Optional[str] = None,
    ) -> None:
        super().__init__(status_code, detail=detail, response=response)
        self.retry_after = retry_after
