"""Integration tests against the live masterclass API.

Requires a .env file with ENROLHQ_BASE_URL and ENROLHQ_API_TOKEN.
"""

import pytest

from enrolhq import (
    ApplicationStatus,
    EnrolHQClient,
    ForbiddenError,
    NotFoundError,
    PaginatedIterator,
    PaginatedResponse,
)


# ── Auth ────────────────────────────────────────────────────

class TestAuth:
    def test_client_authenticates(self, client):
        """First real request should trigger authentication."""
        client.applications.list_page(page_size=1)
        assert client._http.auth.access_token is not None


# ── Applications ────────────────────────────────────────────

class TestApplications:
    def test_list_page(self, client):
        page = client.applications.list_page(page_size=5)
        assert isinstance(page, PaginatedResponse)
        assert page.count > 0
        assert len(page) <= 5
        app = page[0]
        assert "id" in app
        assert "first_name" in app
        assert "last_name" in app
        assert "application_status" in app

    def test_list_returns_iterator(self, client):
        it = client.applications.list(page_size=5)
        assert isinstance(it, PaginatedIterator)
        first = next(it)
        assert "id" in first

    def test_list_with_filters(self, client):
        page = client.applications.list_page(entry_year=2026, page_size=5)
        assert isinstance(page.count, int)

    def test_list_with_status_filter(self, client):
        page = client.applications.list_page(
            application_statuses=ApplicationStatus.ENQUIRY_ONLINE,
            page_size=3,
        )
        for app in page:
            assert app["application_status"] == ApplicationStatus.ENQUIRY_ONLINE

    def test_count(self, client):
        count = client.applications.count()
        assert isinstance(count, int)
        assert count > 0

    def test_count_with_filters(self, client):
        all_count = client.applications.count()
        filtered = client.applications.count(
            application_statuses=ApplicationStatus.ENQUIRY_ONLINE,
        )
        assert filtered <= all_count

    def test_get_application(self, client):
        page = client.applications.list_page(page_size=1)
        app_id = page[0]["id"]
        detail = client.applications.get(app_id)
        assert detail["id"] == app_id
        assert "user_parent" in detail or "dob" in detail

    def test_get_nonexistent_raises_not_found(self, client):
        with pytest.raises(NotFoundError):
            client.applications.get("00000000-0000-0000-0000-000000000000")


# ── Pagination ──────────────────────────────────────────────

class TestPagination:
    def test_auto_pagination_iterates_multiple_pages(self, client):
        """With page_size=2, iterating 5 items should cross at least 2 pages."""
        items = []
        for app in client.applications.list(page_size=2):
            items.append(app)
            if len(items) >= 5:
                break
        assert len(items) == 5
        ids = [a["id"] for a in items]
        assert len(set(ids)) == 5

    def test_total_count_property(self, client):
        it = client.applications.list(page_size=5)
        count = it.total_count
        assert isinstance(count, int)
        assert count > 0

    def test_manual_pagination(self, client):
        page1 = client.applications.list_page(page=1, page_size=2)
        assert len(page1) <= 2
        if page1.next:
            page2 = client.applications.list_page(page=2, page_size=2)
            assert len(page2) <= 2
            assert page1[0]["id"] != page2[0]["id"]


# ── Documents ───────────────────────────────────────────────

class TestDocuments:
    def test_list_documents(self, client):
        page = client.applications.list_page(page_size=10)
        for app in page:
            docs_page = client.documents.list_page(app["id"], page_size=5)
            if docs_page:
                doc = docs_page[0]
                assert "id" in doc
                assert "filename" in doc or "file" in doc
                return
        pytest.skip("No applications with documents found")

    def test_upload_rejects_missing_file(self, client):
        with pytest.raises(FileNotFoundError):
            client.documents.upload("fake-id", "/nonexistent/file.pdf", "SCHOOL_REPORT")


# ── Notes ───────────────────────────────────────────────────

class TestNotes:
    def test_list_notes(self, client):
        page = client.applications.list_page(page_size=1)
        app_id = page[0]["id"]
        notes = list(client.notes.list(app_id, page_size=10))
        assert isinstance(notes, list)


# ── Activity Log ────────────────────────────────────────────

class TestActivityLog:
    def test_list_activity(self, client):
        page = client.applications.list_page(page_size=1)
        app_id = page[0]["id"]
        entries = list(client.activity_log.list(app_id, page_size=5))
        assert isinstance(entries, list)


# ── Email Log ──────────────────────────────────────────────

class TestEmailLog:
    def test_list_emails(self, client):
        page = client.applications.list_page(page_size=1)
        app_id = page[0]["id"]
        emails = list(client.email_log.list(app_id, page_size=5))
        assert isinstance(emails, list)


# ── Reference Data ──────────────────────────────────────────

class TestReferenceData:
    def test_campuses(self, client):
        campuses = client.reference_data.campuses()
        assert isinstance(campuses, list)
        assert len(campuses) > 0
        assert "name" in campuses[0]

    def test_countries(self, client):
        countries = client.reference_data.countries()
        assert isinstance(countries, list)
        assert len(countries) > 0

    def test_languages(self, client):
        languages = client.reference_data.languages()
        assert isinstance(languages, list)
        assert len(languages) > 0

    def test_nationalities(self, client):
        nationalities = client.reference_data.nationalities()
        assert isinstance(nationalities, list)

    def test_timezones(self, client):
        timezones = client.reference_data.timezones()
        assert isinstance(timezones, list)

    def test_parent_relationships(self, client):
        rels = client.reference_data.parent_relationships()
        assert isinstance(rels, list)

    def test_profile_categories(self, client):
        cats = client.reference_data.profile_categories()
        assert isinstance(cats, list)


# ── Staff ───────────────────────────────────────────────────

class TestStaff:
    def test_list_staff(self, client):
        page = client.staff.list_page(page_size=5)
        assert isinstance(page, PaginatedResponse)
        assert page.count > 0
        assert "id" in page[0]


# ── Events ──────────────────────────────────────────────────

class TestEvents:
    def test_list_events(self, client):
        page = client.events.list_page(page_size=5)
        assert isinstance(page, PaginatedResponse)
        assert isinstance(page.count, int)


# ── Analytics ───────────────────────────────────────────────

class TestAnalytics:
    def test_statistics(self, client):
        stats = client.analytics.statistics(
            start_date="2025-01-01", end_date="2026-12-31"
        )
        assert isinstance(stats, dict)
        assert "stats" in stats

    def test_conversion(self, client):
        data = client.analytics.conversion(
            start_date="2025-01-01", end_date="2026-12-31"
        )
        assert isinstance(data, dict)
        assert "current_status" in data
