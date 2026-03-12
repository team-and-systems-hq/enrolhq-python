"""Getting started with the EnrolHQ SDK.

Create a .env file with your credentials:
    ENROLHQ_BASE_URL=https://masterclass.enrolhq.com.au/api/v2/
    ENROLHQ_API_TOKEN=your_token

Or pass them directly:
    client = EnrolHQClient(instance="masterclass", api_token="your_token")
"""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

# Fetch the first page of applications
page = client.applications.list_page(page_size=5)
print(f"Total applications: {page.count}")
for app in page:
    print(f"  {app['first_name']} {app['last_name']} — status {app['application_status']}")

# Fetch reference data
campuses = client.reference_data.campuses()
print(f"\nCampuses: {len(campuses)} found")
for c in campuses:
    print(f"  {c['name']}")
