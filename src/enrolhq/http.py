"""HTTP session wrapper with automatic 401 retry."""

import json
from enum import IntEnum
from typing import Any, Dict, Optional

import requests

from .auth import DEFAULT_TIMEOUT, TokenAuth
from .exceptions import (
    APIError,
    AuthenticationError,
    EnrolHQError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

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
        """Send an HTTP request, retrying once on 401.

        Writes do not follow redirects: EnrolHQ answers a non-canonical host
        (e.g. ``school.enrolhq.com.au`` for a ``.net.au`` school) with a 301,
        and following it would drop the ``Authorization`` header and turn the
        POST/PUT into a GET. A redirect on a write raises :class:`EnrolHQError`
        naming the canonical URL instead.
        """
        kwargs.setdefault("timeout", self.timeout)
        if method.upper() != "GET":
            kwargs.setdefault("allow_redirects", False)
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

        if resp.is_redirect and not kwargs.get("allow_redirects", True):
            location = resp.headers.get("Location", "")
            raise EnrolHQError(
                f"{method} {url} was redirected ({resp.status_code}) to "
                f"{location}. Use the school's canonical host in base_url "
                "(or pass domain=) so writes are not redirected."
            )

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

    def patch(self, url: str, json: Any = None, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", url, json=json, **kwargs)

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
