"""List the activity log for a student profile.

The `activity-log/` endpoint returns timestamped activity entries (emails,
status changes, notes, etc.) for a student profile. Each entry has an
`activity_kind`, a `description`, `occurred_at` / `created_at` timestamps,
`created_by`, and an optional `attachment_src`.

`list()` auto-paginates, so iterating walks every page.
"""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

# Replace with a real student profile UUID from your instance.
STUDENT_PROFILE_ID = "student-profile-uuid"

# Iterate every entry (auto-paginates through all pages).
for entry in client.activity_log.list(STUDENT_PROFILE_ID, page_size=1000):
    when = entry.get("occurred_at") or entry.get("created_at")
    who = entry.get("created_by") or "system"
    kind = entry.get("activity_kind", "")
    description = (entry.get("description") or "").splitlines()
    summary = description[0] if description else ""
    print(f"{when} [{kind}] {who}: {summary}")

# Or fetch a single page manually.
page = client.activity_log.list_page(STUDENT_PROFILE_ID, page=1, page_size=25)
print(f"\nPage 1 has {len(page)} of {page.count} total entries")
