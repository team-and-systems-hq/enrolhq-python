"""Search and filter applications."""

from enrolhq import ApplicationStatus, EnrolHQClient

client = EnrolHQClient()  # reads from .env

# Search by name
page = client.applications.list_page(search="Smith", page_size=10)
print(f"Found {page.count} applications matching 'Smith'")
for app in page:
    print(f"  {app['first_name']} {app['last_name']}")

# Filter by entry year + grade + status
for app in client.applications.list(
    entry_year=2026,
    entry_grade=7,
    application_statuses=ApplicationStatus.ENQUIRY_ONLINE,
):
    print(f"Year 7 2026 enquiry: {app['first_name']} {app['last_name']}")

# Filter by multiple statuses (pass a list)
page = client.applications.list_page(
    application_statuses=[ApplicationStatus.EOI, ApplicationStatus.ENROLMENT],
    page_size=5,
)
print(f"\nEOI + Enrolment: {page.count} total")

# Count without fetching results
count = client.applications.count(entry_year=2026)
print(f"\nTotal 2026 applications: {count}")
