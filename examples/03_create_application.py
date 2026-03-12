"""Create a new application (enquiry).

WARNING: This will create real data in your EnrolHQ instance.
"""

from enrolhq import ApplicationStatus, EnrolHQClient, Gender

client = EnrolHQClient()  # reads from .env

new_app = client.applications.create({
    "application_status": ApplicationStatus.ENQUIRY_ONLINE,
    "first_name": "Jane",
    "last_name": "Doe",
    "dob": "2015-03-15",
    "gender": Gender.FEMALE,
    "entry_grade": 7,
    "entry_year": 2027,
    "user_parent": {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "mobile_phone": "+61400000000",
    },
})

print(f"Created application: {new_app['id']}")
print(f"  Student: {new_app['first_name']} {new_app['last_name']}")
