"""Integration tests against the live EnrolHQ API.

These tests make real network calls and ONLY work with a valid ``.env`` file
in the project root providing credentials::

    ENROLHQ_BASE_URL=https://yourschool.enrolhq.com.au/api/v2/
    ENROLHQ_API_TOKEN=your_api_token_here

Without valid credentials the ``client`` fixture cannot authenticate and these
tests will fail. The unit tests in ``test_unit.py`` need no credentials and run
fully offline.
"""

import itertools

import pytest

from enrolhq import (
    ApplicationStatus,
    CursorPaginatedIterator,
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


# ── Leads ───────────────────────────────────────────────────

class TestApplicationNestedData:
    """Nested data that exists on the detail serializer only."""

    def _first_application_id(self, client):
        page = client.applications.list_page(page_size=1)
        if not page:
            pytest.skip("No applications in this instance")
        return page[0]["id"]

    def test_list_serializer_omits_emergency_contacts(self, client):
        page = client.applications.list_page(page_size=1)
        if not page:
            pytest.skip("No applications in this instance")
        # This is why list-based exports appear to be missing the data.
        assert "emergency_contacts" not in page[0]
        assert "medical_data" not in page[0]

    def test_detail_serializer_includes_them(self, client):
        detail = client.applications.get(self._first_application_id(client))
        assert "emergency_contacts" in detail
        assert "medical_data" in detail
        assert "custom_form_submits" in detail

    def test_emergency_contacts_accessor(self, client):
        contacts = client.applications.emergency_contacts(
            self._first_application_id(client)
        )
        assert isinstance(contacts, list)
        for contact in contacts:
            assert "first_name" in contact
            assert "relationship_to_student" in contact

    def test_medical_data_accessor(self, client):
        assert isinstance(
            client.applications.medical_data(self._first_application_id(client)),
            dict,
        )

    def test_submits_for_application_annotates_form_id(self, client):
        app_id = self._first_application_id(client)
        for submit in client.forms.submits_for_application(app_id):
            assert submit["application_id"] == app_id
            assert submit["form_id"]
            assert "payload" in submit


class TestForms:
    def test_list_forms(self, client):
        page = client.forms.list_page(page_size=5)
        assert isinstance(page, PaginatedResponse)
        if not page:
            pytest.skip("No forms in this instance")
        form = page[0]
        assert "id" in form
        assert "title" in form
        assert "form_slug" in form
        assert "kind" in form

    def test_published_forms(self, client):
        forms = list(client.forms.published(page_size=5))
        for form in forms:
            # The parent-facing serializer carries the audience rules.
            assert "allowed_entry_years" in form
            assert "allowed_application_statuses" in form

    def test_get_form_by_slug(self, client):
        forms = list(client.forms.published(page_size=1))
        if not forms:
            pytest.skip("No published forms in this instance")
        slug = forms[0]["form_slug"]
        assert client.forms.get(slug)["form_slug"] == slug

    def test_find_returns_none_for_unknown(self, client):
        assert client.forms.find("no-such-form-xyz") is None

    def test_submits_page(self, client):
        page = client.forms.submits_page(page_size=5)
        assert isinstance(page.count, int)
        if not page:
            pytest.skip("No form submits in this instance")
        submit = page[0]
        assert "form_id" in submit
        assert "completed_at" in submit
        assert "student_profile" in submit

    def test_submits_form_filter_narrows_results(self, client):
        page = client.forms.submits_page(page_size=1)
        if not page:
            pytest.skip("No form submits in this instance")
        total = page.count
        # The filter is `form`, not `form_id` — `form_id` is silently ignored.
        filtered = client.forms.submits_page(
            form=page[0]["form_id"], page_size=1
        )
        assert filtered.count <= total

    def test_submits_summary_omits_submit_id(self, client):
        """The list endpoint gives no submit id — hence iter_answers()."""
        page = client.forms.submits_page(page_size=5)
        if not page:
            pytest.skip("No form submits in this instance")
        assert all("id" not in submit for submit in page)
        assert all(submit["student_profile"]["id"] for submit in page)

    def test_get_submit_and_answers(self, client):
        page = client.forms.submits_page(is_completed=True, page_size=1)
        if not page:
            pytest.skip("No completed form submits in this instance")
        # The summary has no submit id, so resolve it via the application.
        profile_id = page[0]["student_profile"]["id"]
        submits = client.forms.submits_for_application(profile_id)
        if not submits:
            pytest.skip("No submits on the application detail")
        detail = client.forms.get_submit(submits[0]["id"])
        assert "payload" in detail
        assert "form_schema" in detail
        for answer in client.forms.answers_from(detail):
            assert {"section", "name", "label", "element_type", "value"} <= set(
                answer
            )

    def test_iter_answers_yields_labelled_records(self, client):
        records = list(
            itertools.islice(client.forms.iter_answers(is_completed=True), 2)
        )
        if not records:
            pytest.skip("No completed form submits in this instance")
        for record in records:
            assert record["submit_id"]
            assert record["student_profile"]["id"]
            for answer in record["answers"]:
                assert "label" in answer
                assert "element_type" in answer

    def test_get_nonexistent_submit_raises_not_found(self, client):
        with pytest.raises(NotFoundError):
            client.forms.get_submit("00000000-0000-0000-0000-000000000000")


class TestLeads:
    def test_list_page(self, client):
        page = client.leads.list_page(page_size=5)
        assert isinstance(page, PaginatedResponse)
        assert isinstance(page.count, int)
        if not page:
            pytest.skip("No leads in this instance")
        lead = page[0]
        assert "id" in lead
        assert "email" in lead
        assert "student" in lead

    def test_list_with_filters(self, client):
        page = client.leads.list_page(
            is_email_unique=False, has_student_profile=False, page_size=5
        )
        assert isinstance(page.count, int)

    def test_get_lead(self, client):
        page = client.leads.list_page(page_size=1)
        if not page:
            pytest.skip("No leads in this instance")
        lead_id = page[0]["id"]
        detail = client.leads.get(lead_id)
        assert detail["id"] == lead_id
        assert "residential_address" in detail

    def test_get_nonexistent_raises_not_found(self, client):
        with pytest.raises(NotFoundError):
            client.leads.get("00000000-0000-0000-0000-000000000000")

    def test_references(self, client):
        refs = client.leads.references()
        assert isinstance(refs, list)
        if refs:
            assert "id" in refs[0]
            assert "name" in refs[0]
            assert "slug" in refs[0]

    def test_reference_data_alias(self, client):
        assert client.reference_data.lead_references() == client.leads.references()


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


# ── Audit Log ──────────────────────────────────────────────

class TestAuditLog:
    def test_list_returns_cursor_iterator(self, client):
        page = client.applications.list_page(page_size=1)
        app_id = page[0]["id"]
        it = client.audit_log.list(student_profile_id=app_id, page_size=5)
        assert isinstance(it, CursorPaginatedIterator)

    def test_list_by_student_profile(self, client):
        page = client.applications.list_page(page_size=1)
        app_id = page[0]["id"]
        entries = list(client.audit_log.list(student_profile_id=app_id, page_size=5))
        assert isinstance(entries, list)
        for entry in entries:
            assert "changes" in entry
            assert "updated_at" in entry

    def test_list_requires_filter(self, client):
        with pytest.raises(ValueError):
            client.audit_log.list()


# ── CMS Settings ───────────────────────────────────────────

class TestCmsSettings:
    def test_get(self, client):
        settings = client.cms_settings.get()
        assert isinstance(settings, dict)
        assert "parent_label" in settings
        assert "event_booking" in settings


# ── Metafields ─────────────────────────────────────────────

class TestMetafields:
    def test_get(self, client):
        data = client.metafields.get()
        assert isinstance(data, dict)
        assert "field_settings" in data
        assert "default_field_settings" in data

    def test_field_settings_accessor(self, client):
        fs = client.metafields.field_settings()
        assert isinstance(fs, dict)
        assert len(fs) > 0

    def test_default_field_settings_accessor(self, client):
        dfs = client.metafields.default_field_settings()
        assert isinstance(dfs, dict)


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

    def test_application_status_settings(self, client):
        settings = client.reference_data.application_status_settings()
        assert isinstance(settings, list)
        assert len(settings) > 0
        row = settings[0]
        assert "application_status" in row
        assert "status_label" in row
        assert "is_status_enabled" in row


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
