"""EnrolHQ Python SDK."""

from ._version import __version__
from .client import EnrolHQClient
from .constants import ApplicationStatus, DocumentKind, Gender
from .exceptions import (
    APIError,
    AuthenticationError,
    EnrolHQError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from .pagination import PaginatedIterator, PaginatedResponse

__all__ = [
    "__version__",
    "EnrolHQClient",
    "ApplicationStatus",
    "DocumentKind",
    "Gender",
    "EnrolHQError",
    "AuthenticationError",
    "APIError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "PaginatedIterator",
    "PaginatedResponse",
]
