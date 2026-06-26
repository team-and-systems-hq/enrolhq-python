# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
