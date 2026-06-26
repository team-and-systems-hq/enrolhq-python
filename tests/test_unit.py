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
    assert __version__ == "0.2.0"


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
        "reference_data", "audit_log", "cms_settings", "metafields",
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


# ── Fake HTTP for resource/pagination unit tests ────────────

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeHttp:
    """Records GET calls and returns queued JSON payloads in order."""

    def __init__(self, *payloads):
        self._payloads = list(payloads)
        self.calls = []  # list of (url, params)

    def get(self, url, params=None, **kwargs):
        self.calls.append((url, params))
        return _FakeResponse(self._payloads.pop(0))


BASE = "https://x.enrolhq.com.au/api/v2/"


# ── CursorPaginatedIterator ─────────────────────────────────

def test_cursor_iterator_rejects_bad_page_size():
    from enrolhq.pagination import CursorPaginatedIterator
    with pytest.raises(ValueError, match="page_size"):
        CursorPaginatedIterator(None, "http://x", page_size=0)
    with pytest.raises(ValueError, match="page_size"):
        CursorPaginatedIterator(None, "http://x", page_size=-1)


def test_cursor_iterator_single_page():
    from enrolhq.pagination import CursorPaginatedIterator
    http = _FakeHttp({"results": [{"id": 1}, {"id": 2}], "next": None})
    items = list(CursorPaginatedIterator(http, BASE + "audit/log/", page_size=25))
    assert items == [{"id": 1}, {"id": 2}]
    assert len(http.calls) == 1


def test_cursor_iterator_follows_next_url():
    from enrolhq.pagination import CursorPaginatedIterator
    cursor_url = BASE + "audit/log/?cursor=abc&page_size=2"
    http = _FakeHttp(
        {"results": [{"id": 1}], "next": cursor_url},
        {"results": [{"id": 2}], "next": None},
    )
    it = CursorPaginatedIterator(
        http, BASE + "audit/log/", params={"student_profile": "sid"}, page_size=2
    )
    assert list(it) == [{"id": 1}, {"id": 2}]
    # First call carries the filter params + page_size...
    assert http.calls[0][0] == BASE + "audit/log/"
    assert http.calls[0][1] == {"student_profile": "sid", "page_size": 2}
    # ...subsequent calls follow the server's next URL verbatim, no params.
    assert http.calls[1] == (cursor_url, None)


def test_cursor_iterator_empty():
    from enrolhq.pagination import CursorPaginatedIterator
    http = _FakeHttp({"results": [], "next": None})
    assert list(CursorPaginatedIterator(http, BASE + "audit/log/")) == []


def test_cursor_iterator_respects_max_pages():
    """A never-ending cursor must stop at max_pages, not loop forever."""
    from enrolhq.pagination import CursorPaginatedIterator
    always_next = BASE + "audit/log/?cursor=zzz"
    http = _FakeHttp(
        {"results": [{"id": 1}], "next": always_next},
        {"results": [{"id": 2}], "next": always_next},
        {"results": [{"id": 3}], "next": always_next},
    )
    it = CursorPaginatedIterator(http, BASE + "audit/log/", max_pages=2)
    assert list(it) == [{"id": 1}, {"id": 2}]
    assert len(http.calls) == 2


# ── AuditLogResource ────────────────────────────────────────

def test_audit_log_filters_by_student_profile():
    from enrolhq.pagination import CursorPaginatedIterator
    from enrolhq.resources.audit_log import AuditLogResource
    http = _FakeHttp({"results": [{"changes": []}], "next": None})
    res = AuditLogResource(http, BASE)
    it = res.list(student_profile_id="sid")
    assert isinstance(it, CursorPaginatedIterator)
    list(it)  # consume to trigger the request
    url, params = http.calls[0]
    assert url == BASE + "audit/log/"
    assert params["student_profile"] == "sid"
    assert params["page_size"] == 25


def test_audit_log_filters_by_parent():
    from enrolhq.resources.audit_log import AuditLogResource
    http = _FakeHttp({"results": [], "next": None})
    res = AuditLogResource(http, BASE)
    list(res.list(parent_id="pid", page_size=10))
    _, params = http.calls[0]
    assert params["parent"] == "pid"
    assert params["page_size"] == 10


def test_audit_log_requires_a_filter():
    from enrolhq.resources.audit_log import AuditLogResource
    res = AuditLogResource(_FakeHttp(), BASE)
    with pytest.raises(ValueError, match="student_profile_id"):
        res.list()


# ── ActivityLogResource ─────────────────────────────────────

def test_activity_log_filters_by_student_profile():
    from enrolhq.pagination import PaginatedIterator
    from enrolhq.resources.activity_log import ActivityLogResource
    http = _FakeHttp({"results": [{"description": "x"}], "next": None})
    res = ActivityLogResource(http, BASE)
    it = res.list("sid", page_size=1000)
    assert isinstance(it, PaginatedIterator)
    list(it)  # consume to trigger the request
    url, params = http.calls[0]
    assert url == BASE + "activity-log/"
    assert params["student_profile"] == "sid"
    assert params["page_size"] == 1000


def test_activity_log_list_page():
    from enrolhq.resources.activity_log import ActivityLogResource
    http = _FakeHttp(
        {"count": 3, "results": [{"description": "a"}], "next": None}
    )
    res = ActivityLogResource(http, BASE)
    page = res.list_page("sid", page=2, page_size=50)
    url, params = http.calls[0]
    assert url == BASE + "activity-log/"
    assert params["student_profile"] == "sid"
    assert params["page"] == 2
    assert params["page_size"] == 50
    assert page.count == 3


# ── CmsSettingsResource ─────────────────────────────────────

def test_cms_settings_get():
    from enrolhq.resources.cms_settings import CmsSettingsResource
    payload = {"parent_label": "Parent / Carer", "event_booking": {}}
    http = _FakeHttp(payload)
    res = CmsSettingsResource(http, BASE)
    assert res.get() == payload
    assert http.calls[0][0] == BASE + "cms-settings/"


# ── MetafieldsResource ──────────────────────────────────────

def test_metafields_get():
    from enrolhq.resources.metafields import MetafieldsResource
    payload = {"field_settings": {"parent": {}}, "default_field_settings": {}}
    http = _FakeHttp(payload)
    res = MetafieldsResource(http, BASE)
    assert res.get() == payload
    assert http.calls[0][0] == BASE + "metafields/"


def test_metafields_field_settings_accessor():
    from enrolhq.resources.metafields import MetafieldsResource
    fs = {"parent": {"email": {}}}
    res = MetafieldsResource(_FakeHttp({"field_settings": fs}), BASE)
    assert res.field_settings() == fs


def test_metafields_accessors_default_to_empty():
    from enrolhq.resources.metafields import MetafieldsResource
    res = MetafieldsResource(_FakeHttp({}, {}), BASE)
    assert res.field_settings() == {}
    assert res.default_field_settings() == {}


# ── ReferenceDataResource.application_status_settings ───────

def test_reference_data_application_status_settings():
    from enrolhq.resources.reference_data import ReferenceDataResource
    rows = [
        {"application_status": 0, "status_label": "Enquiry"},
        {"application_status": 3, "status_label": "Enrolment"},
    ]
    http = _FakeHttp({"results": rows, "next": None})
    res = ReferenceDataResource(http, BASE)
    result = res.application_status_settings()
    assert result == rows
    assert http.calls[0][0] == BASE + "application-status-settings/"
