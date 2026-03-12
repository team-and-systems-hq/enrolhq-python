"""HTTP session wrapper with automatic 401 retry."""

import json
from enum import IntEnum
from typing import Any, Dict, Optional

import requests

from .auth import TokenAuth
from .exceptions import (
    APIError,
    AuthenticationError,
    EnrolHQError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

#: Default request timeout in seconds (connect, read).
DEFAULT_TIMEOUT = (10, 30)

_ERROR_MAP = {
    400: ValidationError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    429: RateLimitError,
}


def _clean_params(params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Strip None values and coerce enums so requests serializes them correctly.

    requests uses str() on param values, which turns IntEnum into
    'ApplicationStatus.ENQUIRY_ONLINE' instead of '0'. This coerces
    IntEnum → int before params reach requests.
    """
    if not params:
        return params

    cleaned = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, list):
            cleaned[k] = [int(i) if isinstance(i, IntEnum) else i for i in v]
        elif isinstance(v, IntEnum):
            cleaned[k] = int(v)
        else:
            cleaned[k] = v
    return cleaned


class HttpClient:
    """Thin wrapper around requests.Session with auto-retry on 401."""

    def __init__(self, auth: TokenAuth, timeout: Any = DEFAULT_TIMEOUT) -> None:
        self.auth = auth
        self.session = requests.Session()
        self.timeout = timeout

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Send an HTTP request, retrying once on 401."""
        kwargs.setdefault("timeout", self.timeout)
        headers = kwargs.pop("headers", {})
        headers.update(self.auth.get_headers())
        kwargs["headers"] = headers

        try:
            resp = self.session.request(method, url, **kwargs)
        except requests.RequestException as exc:
            raise EnrolHQError(f"{method} {url} failed: {exc}") from exc

        if resp.status_code == 401:
            self.auth.authenticate()
            kwargs["headers"].update(self.auth.get_headers())
            try:
                resp = self.session.request(method, url, **kwargs)
            except requests.RequestException as exc:
                raise EnrolHQError(f"{method} {url} failed: {exc}") from exc

        if not resp.ok:
            self._raise_for_status(resp)

        return resp

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        return self.request("GET", url, params=_clean_params(params), **kwargs)

    def post(
        self,
        url: str,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        return self.request(
            "POST", url, json=json, params=_clean_params(params), **kwargs
        )

    def put(self, url: str, json: Any = None, **kwargs: Any) -> requests.Response:
        return self.request("PUT", url, json=json, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", url, **kwargs)

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        detail = None
        try:
            body = resp.json()
            if isinstance(body, dict):
                detail = body.get("detail") or body
            else:
                detail = body
        except (ValueError, json.JSONDecodeError):
            detail = resp.text or None

        exc_class = _ERROR_MAP.get(resp.status_code, APIError)
        if exc_class is AuthenticationError:
            raise AuthenticationError(detail=detail, response=resp)
        if exc_class is RateLimitError:
            raise RateLimitError(
                detail=detail,
                response=resp,
                retry_after=resp.headers.get("Retry-After"),
            )
        raise exc_class(resp.status_code, detail=detail, response=resp)
