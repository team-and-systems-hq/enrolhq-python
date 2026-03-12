"""Download all documents for a student."""

import os

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

STUDENT_ID = "your-student-profile-uuid"
OUTPUT_DIR = "downloads"

for doc in client.documents.list(STUDENT_ID):
    filename = doc.get("filename", "unknown")
    kind = doc.get("group_kind", "OTHER")
    file_url = doc.get("file")

    if not file_url:
        print(f"  Skipping {filename} (no file URL)")
        continue

    dest = os.path.join(OUTPUT_DIR, kind, filename)
    client.documents.download(file_url, dest)
    print(f"  Downloaded: {dest}")

print("Done!")
