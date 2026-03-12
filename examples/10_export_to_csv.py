"""Export applications to CSV."""

import csv

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

FIELDS = [
    "id",
    "first_name",
    "last_name",
    "dob",
    "gender",
    "entry_year",
    "entry_grade",
    "application_status",
]

OUTPUT_FILE = "applications_export.csv"

with open(OUTPUT_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()

    count = 0
    for app in client.applications.list(entry_year=2026, page_size=100):
        writer.writerow(app)
        count += 1

print(f"Exported {count} applications to {OUTPUT_FILE}")
