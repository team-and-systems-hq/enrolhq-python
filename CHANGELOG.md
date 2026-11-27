# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation

- **Limited-permission API tokens.** Any staff user with *Create API Token*
  can create a token (previously superusers only). A non-superuser's token is
  only accepted by the leads endpoints, within the user's role permissions.
  README section *Limited-permission API tokens* covers the push-only lead
  setup, revoking and expiry.
- Leads: document `is_lead_submitted_system_event_should_be_dispatched`. The
  guide wrongly said to drop it on v2; without it follow-up rules do not run.
  `examples/15_leads.py` now sets it.

### Fixed

- `client.applications.cancel_interview(application_id, booking)` now takes
  the booking's id. It sent no body before, which the server always answered
  with 400.

### Added

- **Email templates** (`client.email_templates`, `email-templates/`): `list`,
  `get`, `find` (names repeat per recipient type, so it returns a list),
  `create`, `update`, `update_fields`, `set_archived`, `toggle_archive`,
  `delete`, `groups`, `ensure_group` (a new school has no group for its own
  templates), `tags` (the merge tags a template may use) and the signature methods
  `signatures`, `get_signature`, `create_signature`, `update_signature`.
- **Automations** (`client.automations`, `followups/`): `list`, `get`, `find`
  (a list too: names are not unique),
  `create`, `update`, `update_fields`, `set_active`, `delete`, `groups`,
  `ensure_group` and `event_codes`. README section *Email templates and automations* covers
  both.
- **Enrolment journey stages** (`client.application_status_settings`,
  `application-status-settings/`): `list`, `update` and `update_fields`, which
  renames stages, switches them on or off, shows them to parents and reorders
  them. `client.reference_data.application_status_settings()` still reads them.
- **Interview set-up** (`client.interviews`): the settings and interview types
  (`get_settings`, `update_settings`, `update_settings_fields`, `types`,
  `ensure_types`), interviewers (`interviewers`, `get_interviewer`,
  `find_interviewers`, `create_interviewer`, `update_interviewer`,
  `delete_interviewer`), locations (`locations`, `create_location`,
  `update_location`, `ensure_location`) and availability (`availabilities`,
  `get_availability`, `create_availability`, `update_availability`,
  `delete_availability`), the review sheet's questions (`question_sections`,
  `get_question_section`, `create_question_section`,
  `update_question_section`, `delete_question_section`) and layout
  (`get_pdf_settings`, `update_pdf_settings`), and one student's interviews
  (`student_interviews`, `assign`, `unassign`, `delete_interview`,
  `open_times`, `book`, `cancel_booking`). README section *Enrolment journey
  stages and interviews* covers both.
- `client.forms.create(title, form_slug, schema_data, campus_id)`: a new
  custom form with its first draft, inactive and unpublished, with the
  settings the dashboard gives a new form.
- `client.forms.update_settings(form_id, changes)`: change a form's title,
  audience or page settings without touching its steps.
- **Admission processes** (several applications per student), read-only:
  - `client.admission_processes` (`admission-processes/`): `list`,
    `list_page` and `get`. Each process has a title, the forms that belong to
    it, the status a new application opens in and which form submits it.
    Schools without the feature answer with 403.
  - `client.applications.student_applications(application_id)`: the student's
    applications, one per process, each with its own status, entry details,
    `is_primary`, `submitted_at`, `completed_at` and `form_submits`. The
    student record (`get()`, `list()`) only shows the primary application's
    status and entry details.
  - `client.applications.iter_student_applications(admission_process=,
    updated_after=)`: every application at the school in one sweep, each row
    carrying the student's id and names. `admission_process` keeps one
    process's rows (or several) and raises `ValueError` up front for
    anything that is not a UUID, or for an empty collection. `updated_after`
    is the only filter the server applies. A sweep of a large school runs
    for many minutes, so each request gets a 120-second read timeout and is
    repeated up to three times if it times out or meets a 5xx or 429. If it
    still fails the error is raised and `next()` asks for the same page
    again. Each student is yielded once even when pages shift under the
    sweep.
  - The server only puts `applications` on the `v3alpha` student record; v2
    has no such key. These two methods call `v3alpha` whatever version the
    base URL names. Nothing else changes version.
  - README section *Admission processes and multiple applications*,
    `examples/22_admission_processes.py` (pulls one process's applications
    and their form answers, and every submission of its forms, including
    those attached to no application), offline unit tests and read-only
    integration tests. `docs/custom-forms.md` notes what the server rejects when saving a
    form that belongs to a process.
- `PaginatedIterator(retries=, timeout=)`: opt-in. With `retries`, a page
  that fails for a passing reason (timeout, dropped connection, 5xx, 429) is
  asked for again, waiting 5, 10, 20, ... seconds or as long as a 429's
  `Retry-After` says, five minutes at most: a 429 asking for longer is raised
  at once. Other errors (400, 401, 403, 404) are never retried.
  The `list()` methods are unchanged: they do not retry.
- `ApplicationStatus.CUSTOM_9` to `CUSTOM_16` (23-30). The server has 16
  custom statuses; the enum stopped at 8, so `ApplicationStatus(23)` raised.
- `client.applications.field_choices()`: the label for every coded field,
  read from `OPTIONS applications/` (e.g. a parent's `relationship_to_student`
  `0` → "Mother"). README section *Decoding coded fields* and
  `examples/21_field_choices.py` cover it, including the raw HTTP call.
- `client.activity_log.delete(entry_id)` and the `ActivityKind` enum for Comms
  Log entry types.
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

- `PaginatedIterator` skipped a page after an error: the page number moved on
  before the request, so calling `next()` again after a failure asked for the
  following page. It now stays on the page that failed.
- A list whose last page was emptied while it was being read ended in
  `NotFoundError`: the previous page said there was more, and the server
  answers 404 for a page past the end. `PaginatedIterator` now treats a 404
  on any page after the first as the end of the list.
- `client.activity_log.create()` never worked: it sent a `text` field the
  server doesn't have and left out the required `activity_kind` and
  `occurred_at`. It is now `create(student_profile_id, activity_kind,
  description="", *, occurred_at=None, attachment=None)`. `occurred_at`
  defaults to now; a naive datetime or an unknown kind raises `ValueError`.
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
