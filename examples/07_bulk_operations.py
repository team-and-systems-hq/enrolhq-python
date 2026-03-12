"""Bulk operations on applications.

WARNING: These operations modify real data in bulk. Double-check your
filters before running against a production instance.
"""

from enrolhq import ApplicationStatus, EnrolHQClient

client = EnrolHQClient()  # reads from .env

# Change status for specific applications
app_ids = ["uuid-1", "uuid-2", "uuid-3"]  # replace with real UUIDs
client.applications.change_status(app_ids, ApplicationStatus.INTERVIEW)
print("Status changed to Interview")

# Add a note to all Year 7 2026 enquiries
client.applications.bulk_note(
    "Reminder: open day next week",
    entry_year=2026,
    entry_grade=7,
    application_statuses=ApplicationStatus.ENQUIRY_ONLINE,
)
print("Bulk note added")

# Send enrolment invites to all EOI students
client.applications.bulk_enrolment_invite(
    application_statuses=ApplicationStatus.EOI,
    entry_year=2026,
)
print("Enrolment invites sent")

# Merge two duplicate profiles
client.applications.merge_profiles(
    profile_to_keep="keep-this-uuid",      # replace with real UUID
    profile_not_to_keep="remove-this-uuid", # replace with real UUID
)
print("Profiles merged")
