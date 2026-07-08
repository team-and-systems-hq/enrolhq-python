"""Authentication for the EnrolHQ API."""

import json
from typing import Any, Dict

import requests

from .exceptions import AuthenticationError

#: Default request timeout in seconds (connect, read).
DEFAULT_TIMEOUT = (10, 30)


class TokenAuth:
    """Handles token refresh authentication.

    Uses the long-lived api_token to obtain short-lived access tokens
    via the /accounts/refresh/ endpoint.
    """

    def __init__(
        self, base_url: str, api_token: str, timeout: Any = DEFAULT_TIMEOUT
    ) -> None:
        self.base_url = base_url
        self.api_token = api_token
        self.access_token: str = None
        self.timeout = timeout

    def authenticate(self) -> str:
        """Obtain a fresh access token."""
        url = self.base_url + "accounts/refresh/"
        try:
            resp = requests.post(
                url,
                headers={"Authorization": f"Token {self.api_token}"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            err_resp = getattr(exc, "response", None)
            text = getattr(err_resp, "text", str(exc))
            raise AuthenticationError(
                detail=f"Token refresh failed: {text}",
                response=err_resp,
            ) from exc

        try:
            body = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthenticationError(
                detail=f"Invalid JSON response from {url}",
                response=resp,
            ) from exc

        token = body.get("access_token")
        if not token:
            raise AuthenticationError(
                detail="'access_token' not in response",
                response=resp,
            )
        self.access_token = token
        return token

    def get_headers(self) -> Dict[str, str]:
        """Return authorization headers using the current access token."""
        if not self.access_token:
            self.authenticate()
        return {"Authorization": f"Token {self.access_token}"}
