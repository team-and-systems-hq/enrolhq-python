# EnrolHQ Python SDK

Python SDK for the [EnrolHQ](https://enrolhq.com.au) school enrolments and admissions platform API.

## Installation

```bash
pip install enrolhq
```

Or install from source:

```bash
git clone https://github.com/enrolhq/enrolhq-python.git
cd enrolhq-python
pip install -e .
```

## Quick start

Create a `.env` file with your credentials:

```
ENROLHQ_BASE_URL=https://yourschool.enrolhq.com.au/api/v2/
ENROLHQ_API_TOKEN=your_api_token_here
```

Get your API token from EnrolHQ: **Profile icon (top-right) > API Token**.

```python
from enrolhq import EnrolHQClient, ApplicationStatus

client = EnrolHQClient()  # reads from .env

# List all 2026 Year 7 enquiries
for app in client.applications.list(entry_year=2026, entry_grade=7):
    print(app["first_name"], app["last_name"])

# Get a single application
detail = client.applications.get("application-uuid")

# Upload a document
client.documents.upload("student-uuid", "/path/to/report.pdf", "SCHOOL_REPORT")

# Reference data
campuses = client.reference_data.campuses()
```

You can also pass credentials directly:

```python
client = EnrolHQClient(instance="yourschool", api_token="your_token")
# or
client = EnrolHQClient(base_url="https://yourschool.enrolhq.com.au/api/v2/", api_token="your_token")
```

## Pagination

List methods return a lazy iterator that auto-paginates:

```python
# Iterates through ALL pages automatically
for app in client.applications.list(entry_year=2026):
    print(app["first_name"])

# Or fetch a single page manually
page = client.applications.list_page(page=1, page_size=50)
print(f"Page has {len(page)} of {page.count} total")
for app in page:
    print(app["first_name"])
```

## Resources

| Resource | Access | Operations |
|----------|--------|------------|
| Applications | `client.applications` | list, get, create, update, count, actions, bulk ops |
| Documents | `client.documents` | list, upload, download, delete |
| Notes | `client.notes` | list, create |
| Activity Log | `client.activity_log` | list, create |
| Email Log | `client.email_log` | list |
| Events | `client.events` | list, get, create, update, delete |
| Event Bookings | `client.event_bookings` | list, create, update |
| Payments | `client.payments` | order_lines, batch_update_order_lines |
| Staff | `client.staff` | list, get, create, update, toggle_active |
| Analytics | `client.analytics` | statistics, conversion, status_conversion |
| Reference Data | `client.reference_data` | campuses, countries, languages, etc. |

## Error handling

```python
from enrolhq import NotFoundError, ValidationError, ForbiddenError

try:
    app = client.applications.get("nonexistent-uuid")
except NotFoundError:
    print("Application not found")
except ValidationError as e:
    print(f"Bad request: {e.detail}")
except ForbiddenError:
    print("Permission denied")
```

## Examples

See the [`examples/`](examples/) directory for complete working examples, and the [Examples Guide](examples/GUIDE.md) for a full walkthrough of each one.

## License

MIT
