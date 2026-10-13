# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **School configuration resources** — everything set under *Settings* when
  onboarding a school:
  - `client.school` (`school/`): `get`, `update`, `update_fields`,
    `set_region(tzname=, country=)` and commencement date CRUD.
  - `client.campuses` (`school-campuses/`): `list`, `get`, `default`, `create`,
    `update`, `update_fields`, and `set_images(campus_id, **slots)` for the 20
    branding image slots (`IMAGE_SLOTS`: logos, favicon, header and background
    images, email logos). `update_fields` replaces
    `residential_address.country` rather than merging it.
  - `client.look_and_feel` (`cms-look-and-feel/`, `cms-fonts/`):
    `set_palette`, `set_form_header_themes`, `set_fonts`, `font_library`,
    `upload_font` and `find_or_upload_font`.
  - `client.event_settings` (`event-settings/`): `get`, `update`,
    `update_fields`, `kind_options` and `ensure_kinds(labels)`. Before
    writing, `ensure_kinds` rejects a new label that yields an empty slug or
    one another kind already uses.
  - `client.entry_grade_settings` (`entry-grade-settings/`): `get`, `update`
    and `modify_grades(fn, **top_level)`. Year 13 is hidden by default.
  - `client.payment_settings` (`payment/settings/`): `get`, `update` and
    `update_fields` (currency, GST, fees).
  - `client.cms_settings.update()` / `update_fields()`. CMS settings were
    previously read-only in the SDK.
  - `client.metafields.update_field()`, `create_field()`, `delete_field()`,
    `toggle_block()` and `mutate_ordering()`, e.g. to set the "How did you hear
    about us?" options.
- **`enrolhq.files`**: `image_data_uri()` and `file_data_uri()` build the base64
  data URIs that settings endpoints expect for images, documents and fonts.
  They check types up front: SVG, ICO and GIF are rejected, and a filename is
  required for documents.
- **`Replace`** and `deep_merge` support read-modify-write on full-PUT
  endpoints. `Replace` swaps a nested dict wholesale instead of merging it.
- **`session()` and `json_time()`** build event sessions. Times become the
  server's `{"HH": "09", "mm": "30"}` shape, so a GET → PUT round trip compares
  equal. `json_time()` also accepts `"HH:MM:SS"`, ignoring the seconds.
  `events.create()` now fills in the required `slug` and
  `after_submit_settings` keys, `events.update()` copies them from the current
  event when they are missing, and `events.find(name)` looks up an event by
  exact name (falling back to a full scan, because the server's full-text
  `search` misses names like "Principal's Tour").
- **`domain=` / `ENROLHQ_DOMAIN`** builds the base URL for schools hosted on
  `enrolhq.net.au` from `instance=`.
- Examples `18_school_branding.py`, `19_tours_and_events.py` and
  `20_region_and_year_levels.py` (dry run unless `--apply`), with Examples Guide
  sections, a README "Configuring a school" section, offline unit tests
  (`tests/test_configuration.py`) and read-only integration tests.

### Fixed

- `events.preview()` called `staff-events/preview/`, which does not exist (404).
  It now calls `staff-events-preview/`.
- Writes to a non-canonical host (e.g. `school.enrolhq.com.au` for a
  `.net.au` school) used to follow the server's 301. That dropped the
  `Authorization` header and turned the POST/PUT into a GET. Writes and the
  token refresh no longer follow redirects; they raise an error naming the
  canonical URL. `AuthenticationError` takes an optional `status_code`, so a
  token refresh that is redirected or fails (e.g. 429) reports the real status,
  not 401.

- **`docs/custom-forms.md`** — how to build and edit custom forms through the
  API: form settings versus versioned schemas (draft, publish, preview), the
  `forms/staff/{id}/` read-modify-write, the step and element schema with every
  element type, per-form field settings (`local_fields_settings`), where answers
  are stored, checking a form with the no-save preview validation endpoint,
  styling through `css_class` and *Custom Scripts*, and a workflow for building
  a form from a school's document.
- **Form building on `client.forms`:** `definition(form_id)` (`GET
  forms/staff/{id}/`, the latest schema version, draft included),
  `update_definition()` (full PUT), `save_schema(form_id, steps,
  local_fields_settings=, publish=False, settings=)` (draft by default; keeps
  the form's settings and, unless given, its field overrides),
  `check_local_fields()` (unknown or permanent override keys, which the server
  would otherwise drop or reject), `preview(form_slug)` and
  `validate_step(form_id, step, answers)` (the submission validation, saving
  nothing).
- **Custom Scripts on `client.cms_settings`:** `custom_scripts()`,
  `append_custom_scripts(snippet, marker=)` (adds once, keeps the school's
  existing HTML) and `set_custom_scripts(html)` (`extra-frontend-code/`, parent
  pages only).
- `HttpClient.patch()`. Like the other writes, it does not follow redirects.
- **`docs/integration-service.md`** — how to build the service that receives
  EnrolHQ's outbound sync signals (the **Integration Service URL** on
  *Settings > Integrations*). Covers both protocols (legacy synchronous and the
  async `sync_request` callback to `integrations/sync/finished/`), the inbound
  payload shapes, the response schemas and their validation rules, what the
  Integration Service Token and Timeout actually control, and a minimal Flask
  receiver.
- **`client.forms`** — custom forms and parent submissions, the home of
  photo/video permission and consent answers. Form definitions via `list()` /
  `list_page()` (`GET forms/staff/`), `published()` (`GET forms/`, includes
  audience rules), `get(form_slug)` and `find(title_or_slug)`. Submissions via
  `submits()` / `submits_page()` (`GET forms/staff-submits/`; filters: `form`,
  `entry_year`, `entry_grade`, `application_statuses`, `is_completed`),
  `get_submit()`, `submits_for_application()`, `update_submit()`,
  `reopen_submit()` and `export_submits()` (CSV, one flat row per submission).
- **`client.forms.answers()` / `answers_from()` / `consents()`** — join a
  submission's `payload` against its form schema so answers carry the question
  text the parent saw, instead of opaque keys like `group_3_social_media`.
  `consents()` narrows this to the yes/no permission answers.
- **`client.forms.iter_answers()` / `answers_for_application()`** — labelled
  answers in bulk. The `forms/staff-submits/` list omits each submit's own
  id, so its records cannot be passed to `get_submit()`; these resolve the
  submit ids via the application detail (one request per application).
- **`examples/17_custom_form_answers.py`** — discovery-driven example with no
  hardcoded ids: list custom forms, pick one, find a student who submitted
  it, and read their labelled answers.
- **`client.applications.emergency_contacts()`, `.medical_data()`,
  `.guardians()`** — convenience accessors for nested data that exists on the
  application *detail* serializer only. `applications.list()` returns a
  summary serializer that omits these fields, which is why they appear absent
  from list-based exports.
- **`client.leads`** — full leads resource on the v2 API: `list()` /
  `list_page()` (filters: `is_email_unique`, `has_student_profile`), `get()`,
  `create()`, `update()` (PUT full-replacement), and `references()` for lead
  references (`GET lead-references/`). Set `student_profile` to a profile UUID
  to link a lead to an existing application. Replaces the legacy v1 Zapier
  `POST /api/v1/leads/` integration.
- **`client.leads.create_reference(name, slug=None)`** — create a lead
  reference. There is no dedicated write endpoint, so it round-trips the
  `school/` settings object (get -> append to `lead_references` -> put) and
  returns the new record with its server-assigned `id`. Raises `ValueError`
  on a duplicate slug.
- `client.reference_data.lead_references()` — lead references alongside the
  other lookup lists.
- Example `15_leads.py` with a matching Examples Guide section (including
  v1-Zapier migration notes), plus offline unit tests and read-only
  integration tests for leads.
- `bandit` security linting via pre-commit (`.pre-commit-config.yaml`);
  `bandit` and `pre-commit` added to the `dev` extras.
- Example `14_activity_log.py` and a matching Examples Guide section for the
  existing `client.activity_log` resource (uses a placeholder UUID).
- Offline unit tests for `ActivityLogResource` (`list` / `list_page`).

### Fixed

- The token-refresh request in `TokenAuth` now applies the default `(10, 30)`
  timeout (previously it could hang indefinitely). `EnrolHQClient(timeout=...)`
  is now passed through to auth requests as well.

### Documentation

- Document that the integration test suite makes real API calls and only runs
  with a valid `.env` (`ENROLHQ_BASE_URL` + `ENROLHQ_API_TOKEN`); unit tests run
  offline with no credentials. Added a "Testing" section to the README.

## [0.2.0] - 2026-06-26

### Added

- **`client.audit_log`** — read the audit / change log for a student profile or
  parent (`GET audit/log/`). Filter with `student_profile_id` or `parent_id`;
  returns a `CursorPaginatedIterator` that auto-follows cursor pages.
- **`CursorPaginatedIterator`** — follows DRF cursor pagination by chasing the
  server's `next` URL, for endpoints that paginate by cursor and omit `count`.
  Exported from the package top level alongside `PaginatedIterator`.
- **`client.cms_settings.get()`** — read the school's CMS / form configuration
  (`GET cms-settings/`): enquiry & event-booking copy, form labels, terms &
  conditions, parent-dashboard visibility flags, and policy agreement items.
- **`client.metafields`** — read per-model field configuration
  (`GET metafields/`) with `get()`, plus `field_settings()` and
  `default_field_settings()` accessors.
- **`client.reference_data.application_status_settings()`** — list application
  status settings (`GET application-status-settings/`): per-status labels and
  enabled / dashboard-visibility flags, keyed to the `ApplicationStatus` enum.
- Examples `11_cms_settings.py`, `12_metafields.py`, and `13_audit_log.py`,
  documented in the [Examples Guide](examples/GUIDE.md).

### Notes

- All of the above endpoints are exposed read-only (`GET`).
- `client.notes.list(...)` already forwards arbitrary query params, so result
  ordering works without code changes, e.g.
  `client.notes.list("<uuid>", page_size=1000, ordering="-is_pinned,-created_at")`.

## [0.1.0] - 2026-03-12

### Added

- Initial release. Resources: applications, documents, notes, activity log,
  email log, events, event bookings, payments, staff, analytics, and reference
  data. Token-refresh authentication, lazy auto-pagination, and a typed
  exception hierarchy.
