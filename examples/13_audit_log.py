"""Read the audit / change log for a student profile or a parent.

The `audit/log/` endpoint is read-only and cursor-paginated. Each entry has a
list of human-readable `changes`, plus `updated_at` and `updated_by`. Filter by
either a student profile or a parent.

The audit log is cursor-paginated (no total `count`); iterating follows the
server's `next` cursor automatically.
"""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

STUDENT_PROFILE_ID = "312d6e0c-ab79-4a71-8e47-ec769791861b"
PARENT_ID = "657d463d-044d-4bff-8925-b4a5074f5920"

# Audit log for a student profile — iterate every page automatically.
print(f"Audit log for student {STUDENT_PROFILE_ID}:")
for entry in client.audit_log.list(student_profile_id=STUDENT_PROFILE_ID):
    who = entry.get("updated_by") or "system"
    for change in entry.get("changes", []):
        print(f"  {entry['updated_at']} — {who}: {change}")

# Audit log for a parent.
print(f"\nAudit log for parent {PARENT_ID}:")
for entry in client.audit_log.list(parent_id=PARENT_ID, page_size=25):
    for change in entry.get("changes", []):
        print(f"  {entry['updated_at']}: {change}")
