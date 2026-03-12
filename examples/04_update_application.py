"""Update an existing application.

WARNING: This will modify real data in your EnrolHQ instance.

The EnrolHQ API uses PUT (full replacement), so you must send the
complete application object. The pattern is: GET -> modify -> PUT.
"""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

APPLICATION_ID = "your-application-uuid"  # replace with a real UUID

# 1. Fetch the current application
app = client.applications.get(APPLICATION_ID)
print(f"Current name: {app['first_name']} {app['last_name']}")

# 2. Modify the fields you want to change
app["preferred_name"] = "Jenny"
app["entry_grade"] = 8

# 3. PUT the full object back
updated = client.applications.update(APPLICATION_ID, app)
print(f"Updated preferred_name: {updated['preferred_name']}")
print(f"Updated entry_grade: {updated['entry_grade']}")
