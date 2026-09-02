# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`ProfileCopier`** — copy a student profile between two EnrolHQ instances.
  `ProfileCopier(source, target).copy(application_id)` looks the student up on
  the target by name and date of birth, creates them if they are not there,
  then copies the values across. Trashed profiles are ignored during the
  lookup, so a record staff deleted is never revived. Returns a `CopyResult`
  listing what was copied, what the target would not accept, and which lookup
  values had no equivalent. Documents are not copied.
- **`client.applications.field_options(verb="POST")`** — the field schema the
  instance accepts, from the API's `OPTIONS` metadata: `type`, `required`,
  `read_only`, `choices`, and `children` for nested objects. No two schools
  enable the same fields, so this allows building a payload for an instance
  whose configuration is not known ahead of time. `ProfileCopier` filters
  through it recursively rather than hardcoding a field list.
- **`client.applications.find(first_name, last_name, dob)`** — find a single
  application by exact name and date of birth. The server-side name filters
  match loosely, so results are re-checked for an exact match. Excludes
  trashed profiles unless `include_trashed=True`.
- `client.reference_data.interview_categories()` and
  `client.reference_data.sibling_statuses()` — lookup lists that live on the
  `school/` settings object (as `profile_priorities` and `siblings_statuses`)
  rather than behind their own endpoints. Sibling statuses are named by
  `label`, not `name`.
- `BaseResource._options()` — shared `OPTIONS` helper alongside the existing
  `_get` / `_post` / `_put` / `_delete`.
- Example `18_copy_application_between_instances.py` with a matching Examples
  Guide section.
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

### Notes

- Lookup tables are school-scoped: campuses, attendance types, parent
  relationships, profile category options, interview categories and sibling
  statuses all use different UUIDs on every instance, so `ProfileCopier`
  matches them by name. This includes the campus and attendance type nested
  inside `alternative_entry_details`, which are separate values from the
  top-level ones. Global dictionaries (countries, languages, schools) share
  IDs across instances and are copied as-is.
- Known gap: `medical_data.medical_conditions_v2[].option` is also
  school-scoped but is not remapped — `LOOKUP_FIELDS` paths address a field
  either at the top level or one list deep, and this one sits behind both a
  nested object and a list.
- Example 18 is the only example that does not read from `.env`, since those
  keys describe a single instance. It uses `ENROLHQ_SOURCE_*` /
  `ENROLHQ_TARGET_*` environment variables instead.

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
