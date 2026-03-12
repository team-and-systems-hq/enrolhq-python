"""Unit tests for offline logic (no API calls)."""

import pytest

from enrolhq import (
    APIError,
    ApplicationStatus,
    AuthenticationError,
    DocumentKind,
    EnrolHQClient,
    EnrolHQError,
    ForbiddenError,
    Gender,
    NotFoundError,
    RateLimitError,
    ValidationError,
    __version__,
)
from enrolhq.pagination import PaginatedResponse


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Prevent .env and env vars from leaking into unit tests."""
    monkeypatch.delenv("ENROLHQ_BASE_URL", raising=False)
    monkeypatch.delenv("ENROLHQ_INSTANCE", raising=False)
    monkeypatch.delenv("ENROLHQ_API_TOKEN", raising=False)
    monkeypatch.setattr("enrolhq.client._load_dotenv", lambda: {})


# ── Version ─────────────────────────────────────────────────

def test_version():
    assert __version__ == "0.1.0"


# ── Constants ───────────────────────────────────────────────

def test_application_status_values():
    assert int(ApplicationStatus.ENQUIRY_ONLINE) == 0
    assert int(ApplicationStatus.EOI) == 2
    assert int(ApplicationStatus.ENROLMENT) == 3
    assert int(ApplicationStatus.TRASHED) == 7
    assert int(ApplicationStatus.REGISTER_INTEREST) == -1
    assert int(ApplicationStatus.CUSTOM_8) == 22


def test_application_status_works_as_int():
    assert ApplicationStatus.EOI + 1 == 3
    assert ApplicationStatus.ENROLMENT > ApplicationStatus.EOI


def test_gender_values():
    assert int(Gender.MALE) == 1
    assert int(Gender.FEMALE) == 2
    assert int(Gender.OTHER) == 3
    assert int(Gender.PREFER_NOT_TO_DISCLOSE) == 4


def test_document_kind_is_str_enum():
    assert DocumentKind.SCHOOL_REPORT == "SCHOOL_REPORT"
    assert DocumentKind.BIRTH_CERT == "BIRTH_CERT"
    assert DocumentKind.NAPLAN == "NAPLAN"
    # Should be a real enum
    assert isinstance(DocumentKind.SCHOOL_REPORT, DocumentKind)
    # Should be usable as a plain string
    assert "SCHOOL" in DocumentKind.SCHOOL_REPORT


# ── Exception hierarchy ─────────────────────────────────────

def test_exception_hierarchy():
    assert issubclass(AuthenticationError, EnrolHQError)
    assert issubclass(AuthenticationError, APIError)
    assert issubclass(APIError, EnrolHQError)
    assert issubclass(NotFoundError, APIError)
    assert issubclass(ValidationError, APIError)
    assert issubclass(ForbiddenError, APIError)
    assert issubclass(RateLimitError, APIError)


def test_authentication_error_is_api_error():
    """AuthenticationError should be catchable as APIError."""
    err = AuthenticationError(detail="bad token")
    assert err.status_code == 401
    assert err.detail == "bad token"
    with pytest.raises(APIError):
        raise AuthenticationError(detail="expired")


def test_forbidden_does_not_shadow_builtin():
    """ForbiddenError must not shadow builtins.PermissionError."""
    import builtins
    assert not hasattr(builtins, "ForbiddenError")


def test_api_error_attributes():
    err = APIError(404, detail="not found")
    assert err.status_code == 404
    assert err.detail == "not found"
    assert "404" in str(err)
    assert "not found" in str(err)


def test_rate_limit_error_retry_after():
    err = RateLimitError(detail="slow down", retry_after="30")
    assert err.status_code == 429
    assert err.retry_after == "30"
    assert err.detail == "slow down"


def test_rate_limit_error_retry_after_none():
    err = RateLimitError(detail="slow down")
    assert err.retry_after is None


def test_api_error_catch_as_base():
    with pytest.raises(EnrolHQError):
        raise NotFoundError(404, detail="gone")


# ── Client init ─────────────────────────────────────────────

def test_client_from_instance():
    c = EnrolHQClient(instance="demo", api_token="tok")
    assert c.base_url == "https://demo.enrolhq.com.au/api/v2/"


def test_client_from_base_url():
    c = EnrolHQClient(base_url="https://custom.example.com/api/v2", api_token="tok")
    assert c.base_url == "https://custom.example.com/api/v2/"


def test_client_base_url_trailing_slash():
    c = EnrolHQClient(base_url="https://x.com/api/v2/", api_token="tok")
    assert c.base_url == "https://x.com/api/v2/"


def test_client_explicit_params_override_env(monkeypatch):
    monkeypatch.setenv("ENROLHQ_BASE_URL", "https://env.example.com/api/v2/")
    monkeypatch.setenv("ENROLHQ_API_TOKEN", "env_token")
    c = EnrolHQClient(instance="explicit", api_token="explicit_tok")
    assert c.base_url == "https://explicit.enrolhq.com.au/api/v2/"


def test_client_missing_token():
    with pytest.raises(ValueError, match="api_token"):
        EnrolHQClient(instance="demo")


def test_client_missing_url_and_instance():
    with pytest.raises(ValueError, match="instance"):
        EnrolHQClient(api_token="tok")


def test_client_from_env(monkeypatch):
    monkeypatch.setenv("ENROLHQ_BASE_URL", "https://env.example.com/api/v2/")
    monkeypatch.setenv("ENROLHQ_API_TOKEN", "env_tok")
    c = EnrolHQClient()
    assert c.base_url == "https://env.example.com/api/v2/"


def test_client_repr():
    c = EnrolHQClient(instance="test", api_token="tok")
    assert "test.enrolhq.com.au" in repr(c)


def test_client_has_all_resources():
    c = EnrolHQClient(instance="x", api_token="tok")
    for attr in [
        "applications", "documents", "notes", "activity_log", "email_log",
        "events", "event_bookings", "payments", "staff", "analytics",
        "reference_data",
    ]:
        assert hasattr(c, attr), f"Missing resource: {attr}"


def test_client_dotenv_does_not_mutate_environ(monkeypatch):
    """_load_dotenv should return a dict, not modify os.environ."""
    import os
    from enrolhq.client import _load_dotenv as real_load_dotenv

    # Restore the real _load_dotenv for this test
    monkeypatch.setattr("enrolhq.client._load_dotenv", real_load_dotenv)
    before = dict(os.environ)
    real_load_dotenv()
    after = dict(os.environ)
    assert before == after


# ── PaginatedResponse ───────────────────────────────────────

def test_paginated_response_parses():
    data = {
        "count": 42,
        "next": "http://example.com?page=2",
        "previous": None,
        "results": [{"id": 1}, {"id": 2}],
    }
    page = PaginatedResponse(data)
    assert page.count == 42
    assert page.next == "http://example.com?page=2"
    assert page.previous is None
    assert len(page.results) == 2


def test_paginated_response_empty():
    page = PaginatedResponse({})
    assert page.count == 0
    assert page.results == []
    assert page.next is None


def test_paginated_response_repr():
    page = PaginatedResponse({"count": 10, "results": [1, 2, 3]})
    assert "count=10" in repr(page)
    assert "page_size=3" in repr(page)


def test_paginated_response_len():
    page = PaginatedResponse({"count": 100, "results": [{"id": 1}, {"id": 2}]})
    assert len(page) == 2


def test_paginated_response_iter():
    page = PaginatedResponse({"count": 2, "results": [{"id": 1}, {"id": 2}]})
    items = list(page)
    assert items == [{"id": 1}, {"id": 2}]


def test_paginated_response_getitem():
    page = PaginatedResponse({"count": 2, "results": [{"id": "a"}, {"id": "b"}]})
    assert page[0] == {"id": "a"}
    assert page[1] == {"id": "b"}
    assert page[-1] == {"id": "b"}


def test_paginated_response_bool():
    assert bool(PaginatedResponse({"results": [{"id": 1}]})) is True
    assert bool(PaginatedResponse({"results": []})) is False
    assert bool(PaginatedResponse({})) is False


# ── _clean_params ──────────────────────────────────────────

def test_clean_params_strips_none():
    from enrolhq.http import _clean_params
    assert _clean_params({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}


def test_clean_params_coerces_int_enum():
    from enrolhq.http import _clean_params
    result = _clean_params({"status": ApplicationStatus.ENQUIRY_ONLINE})
    assert result == {"status": 0}
    assert type(result["status"]) is int


def test_clean_params_coerces_int_enum_in_list():
    from enrolhq.http import _clean_params
    result = _clean_params({
        "statuses": [ApplicationStatus.EOI, ApplicationStatus.ENROLMENT],
    })
    assert result == {"statuses": [2, 3]}
    assert all(type(v) is int for v in result["statuses"])


def test_clean_params_passthrough_none():
    from enrolhq.http import _clean_params
    assert _clean_params(None) is None


def test_clean_params_passthrough_empty():
    from enrolhq.http import _clean_params
    assert _clean_params({}) == {}


# ── PaginatedIterator ───────────────────────────────────────

def test_paginated_iterator_rejects_bad_page_size():
    from enrolhq.pagination import PaginatedIterator
    with pytest.raises(ValueError, match="page_size"):
        PaginatedIterator(None, "http://x", page_size=0)
    with pytest.raises(ValueError, match="page_size"):
        PaginatedIterator(None, "http://x", page_size=-1)
