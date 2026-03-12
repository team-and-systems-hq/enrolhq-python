# EnrolHQ SDK - Examples Guide

Step-by-step walkthrough of the example scripts. Each example is a standalone `.py` file you can run directly.

## Setup

1. Install the SDK:

```bash
pip install -e .
```

2. Create a `.env` file in your project root with your credentials:

```
ENROLHQ_BASE_URL=https://yourschool.enrolhq.com.au/api/v2/
ENROLHQ_API_TOKEN=your_api_token_here
```

Get your API token from EnrolHQ: **Profile icon (top-right) > API Token**.

3. Run any example:

```bash
python examples/01_getting_started.py
```

---

## 01 - Getting Started

**File:** [`01_getting_started.py`](01_getting_started.py)

The simplest possible usage. Creates a client (credentials loaded automatically from `.env`), fetches one page of applications, and lists your campuses.

```python
from enrolhq import EnrolHQClient

client = EnrolHQClient()

page = client.applications.list_page(page_size=5)
print(f"Total applications: {page.count}")
for app in page:
    print(f"  {app['first_name']} {app['last_name']}")

campuses = client.reference_data.campuses()
print(f"Campuses: {len(campuses)} found")
```

Key concepts:
- `EnrolHQClient()` with no arguments reads from `.env`
- `list_page()` returns a `PaginatedResponse` — you can iterate it directly with `for app in page`
- `page.count` is the total across all pages, `len(page)` is just this page

---

## 02 - Search and Filter

**File:** [`02_search_and_filter.py`](02_search_and_filter.py)

Filter applications by name, entry year, grade, and status. Shows how to use `ApplicationStatus` enum values directly — no need to convert to int or string.

```python
from enrolhq import ApplicationStatus, EnrolHQClient

client = EnrolHQClient()

# Single status filter
for app in client.applications.list(
    entry_year=2026,
    application_statuses=ApplicationStatus.ENQUIRY_ONLINE,
):
    print(app["first_name"])

# Multiple statuses (pass a list)
page = client.applications.list_page(
    application_statuses=[ApplicationStatus.EOI, ApplicationStatus.ENROLMENT],
    page_size=5,
)

# Count without fetching results
count = client.applications.count(entry_year=2026)
```

Key concepts:
- Pass `ApplicationStatus` enum values directly — the SDK handles serialisation
- Use a list for multiple status values
- `count()` is a lightweight alternative when you only need the number

---

## 03 - Create Application

**File:** [`03_create_application.py`](03_create_application.py)

Create a new student enquiry. Uses `ApplicationStatus` and `Gender` enums directly in the JSON payload.

```python
from enrolhq import ApplicationStatus, EnrolHQClient, Gender

client = EnrolHQClient()

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
print(f"Created: {new_app['id']}")
```

> **Warning:** This creates real data in your instance.

---

## 04 - Update Application

**File:** [`04_update_application.py`](04_update_application.py)

The API uses **PUT** (full replacement), not PATCH. You must send the complete object back. The safe pattern is: **get -> modify -> update**.

```python
app = client.applications.get("your-uuid")
app["preferred_name"] = "Jenny"
updated = client.applications.update("your-uuid", app)
```

> **Warning:** Omitting fields in the update may reset them to defaults.

---

## 05 - Upload Documents

**File:** [`05_upload_documents.py`](05_upload_documents.py)

Upload files to a student profile. Uses the `DocumentKind` enum for categorisation.

```python
from enrolhq import DocumentKind, EnrolHQClient

client = EnrolHQClient()

doc = client.documents.upload(
    student_profile_id="student-uuid",
    file_path="/path/to/report.pdf",
    group_kind=DocumentKind.SCHOOL_REPORT,
    filename="Year_6_Report.pdf",  # optional display name
)
```

Key concepts:
- `file_path` must be a local file that exists (raises `FileNotFoundError` otherwise)
- `group_kind` categorises the document — see `DocumentKind` for all options
- `filename` is optional; defaults to the local file name

---

## 06 - Download Documents

**File:** [`06_download_documents.py`](06_download_documents.py)

List a student's documents and download each one to a local folder, organised by document kind.

```python
for doc in client.documents.list("student-uuid"):
    file_url = doc.get("file")
    if file_url:
        client.documents.download(file_url, f"downloads/{doc['filename']}")
```

Key concepts:
- `list()` returns an iterator over all documents
- Each document has a `file` URL — pass this to `download()`
- `download()` creates parent directories automatically

---

## 07 - Bulk Operations

**File:** [`07_bulk_operations.py`](07_bulk_operations.py)

Perform actions across multiple applications at once. Includes status changes, bulk notes, enrolment invites, and profile merging.

```python
# Change status for specific applications
client.applications.change_status(
    ["uuid-1", "uuid-2"],
    ApplicationStatus.INTERVIEW,
)

# Add a note to all matching applications
client.applications.bulk_note(
    "Reminder: open day next week",
    entry_year=2026,
    application_statuses=ApplicationStatus.ENQUIRY_ONLINE,
)
```

> **Warning:** Bulk operations modify real data. Double-check your filters.

---

## 08 - Pagination

**File:** [`08_pagination.py`](08_pagination.py)

Shows both pagination styles side by side.

**Auto-pagination** — iterate everything, the SDK fetches pages behind the scenes:

```python
for app in client.applications.list(entry_year=2026, page_size=50):
    print(app["first_name"])
```

**Manual pagination** — fetch one page at a time for full control:

```python
page = client.applications.list_page(page=1, page_size=10)
print(f"Page 1: {len(page)} results of {page.count} total")
if page.next:
    page2 = client.applications.list_page(page=2, page_size=10)
```

---

## 09 - Events and Bookings

**File:** [`09_events_and_bookings.py`](09_events_and_bookings.py)

List events and event bookings.

```python
for event in client.events.list():
    print(event.get("title"), event.get("start_datetime"))

for booking in client.event_bookings.list(page_size=10):
    print(booking["id"])
```

---

## 10 - Export to CSV

**File:** [`10_export_to_csv.py`](10_export_to_csv.py)

A practical example: export all 2026 applications to a CSV file. Uses auto-pagination to iterate through everything.

```python
import csv
from enrolhq import EnrolHQClient

client = EnrolHQClient()

FIELDS = ["id", "first_name", "last_name", "dob", "entry_year", "application_status"]

with open("export.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    for app in client.applications.list(entry_year=2026):
        writer.writerow(app)
```

Key concepts:
- `extrasaction="ignore"` tells `DictWriter` to skip fields not in your `FIELDS` list
- Auto-pagination handles fetching all pages — you just iterate

---

## Error Handling

All examples will raise clear exceptions on failure:

```python
from enrolhq import (
    AuthenticationError,  # 401 — bad or expired token
    ValidationError,      # 400 — invalid request data
    NotFoundError,        # 404 — resource doesn't exist
    ForbiddenError,       # 403 — insufficient permissions
    RateLimitError,       # 429 — too many requests
    EnrolHQError,         # catch-all for any SDK error
)

try:
    app = client.applications.get("some-uuid")
except NotFoundError:
    print("Not found")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after}s")
except EnrolHQError as e:
    print(f"Something went wrong: {e}")
```

All exceptions inherit from `EnrolHQError`, so you can use it as a catch-all. All HTTP errors (including `AuthenticationError`) inherit from `APIError` and have `.status_code`, `.detail`, and `.response` attributes.

---

## Available Enums

### ApplicationStatus

| Name | Value | Description |
|------|-------|-------------|
| `REGISTER_INTEREST` | -1 | Register interest |
| `ENQUIRY_ONLINE` | 0 | Online enquiry |
| `ENQUIRY_EVENT` | 1 | Event enquiry |
| `EOI` | 2 | Expression of interest |
| `ENROLMENT` | 3 | Enrolment |
| `ORIENTATION` | 4 | Orientation |
| `COMMUNITY` | 5 | Community |
| `ALUMNI` | 6 | Alumni |
| `TRASHED` | 7 | Trashed |
| `DECLINED` | 8 | Declined |
| `WAITLIST` | 9 | Waitlist |
| `RESERVED_OFFER` | 10 | Reserved offer |
| `NOT_PROCEEDING` | 11 | Not proceeding |
| `ENROLMENT_OFFER` | 12 | Enrolment offer |
| `INTERVIEW` | 13 | Interview |
| `PENDING` | 14 | Pending |
| `CUSTOM_1` .. `CUSTOM_8` | 15-22 | Custom statuses |

### Gender

| Name | Value |
|------|-------|
| `MALE` | 1 |
| `FEMALE` | 2 |
| `OTHER` | 3 |
| `PREFER_NOT_TO_DISCLOSE` | 4 |

### DocumentKind

`BIRTH_CERT`, `SCHOOL_REPORT`, `NAPLAN`, `PASSPORT`, `VISA`, `STAFF_ONLY`, `ASSESSMENT`, `BAPTISMAL_CERT`, and many more. See `enrolhq.DocumentKind` for the full list.
