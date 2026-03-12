"""Upload documents for a student.

WARNING: This will upload real files to your EnrolHQ instance.
Replace the file paths and student ID below with real values.
"""

from enrolhq import DocumentKind, EnrolHQClient

client = EnrolHQClient()  # reads from .env

STUDENT_ID = "your-student-profile-uuid"  # replace with a real UUID

# Upload a school report
doc = client.documents.upload(
    student_profile_id=STUDENT_ID,
    file_path="/path/to/report.pdf",  # replace with a real file path
    group_kind=DocumentKind.SCHOOL_REPORT,
    filename="Year_6_Report.pdf",  # optional display name
)
print(f"Uploaded document: {doc['id']}")
print(f"  Filename: {doc['filename']}")
print(f"  Kind: {doc['group_kind']}")

# Upload a birth certificate
doc2 = client.documents.upload(
    student_profile_id=STUDENT_ID,
    file_path="/path/to/birth_cert.pdf",  # replace with a real file path
    group_kind=DocumentKind.BIRTH_CERT,
)
print(f"Uploaded: {doc2['filename']}")
