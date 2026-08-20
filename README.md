# EnrolHQ Python SDK

Python SDK for the [EnrolHQ](https://enrolhq.com.au) school enrolments and admissions platform API.

API Documentation [Swagger](https://demo.enrolhq.com.au/api-docs/swagger/) or [ReDoc](https://demo.enrolhq.com.au/api-docs/redoc/)

## Installation

The SDK is installed from GitHub (it is not published on PyPI). Install it
directly with pip:

```bash
pip install git+https://github.com/team-and-systems-hq/enrolhq-python.git@main
```

Or pin it in your `requirements.txt`:

```txt
enrolhq @ git+https://github.com/team-and-systems-hq/enrolhq-python.git@main
```

For local development, clone the repo and install in editable mode:

```bash
git clone https://github.com/team-and-systems-hq/enrolhq-python.git
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

Most list endpoints use page-number pagination. A few (e.g. the audit log) use
**cursor pagination** instead — they return no total `count`, and iterating
follows the server's `next` cursor automatically:

```python
# Auto-follows cursor pages; no count is available
for entry in client.audit_log.list(student_profile_id="student-uuid"):
    print(entry["updated_at"], entry["changes"])
```

## Resources

| Resource | Access | Operations |
|----------|--------|------------|
| Applications | `client.applications` | list, get, create, update, count, actions, bulk ops |
| Leads | `client.leads` | list, get, create, update, references, create_reference |
| Forms | `client.forms` | list, get, find, submits, get_submit, answers, consents, iter_answers, export_submits |
| Documents | `client.documents` | list, upload, download, delete |
| Notes | `client.notes` | list, create |
| Activity Log | `client.activity_log` | list, create |
| Audit Log | `client.audit_log` | list (by student_profile or parent) |
| Email Log | `client.email_log` | list |
| Events | `client.events` | list, get, create, update, delete |
| Event Bookings | `client.event_bookings` | list, create, update |
| Payments | `client.payments` | order_lines, batch_update_order_lines |
| Staff | `client.staff` | list, get, create, update, toggle_active |
| Analytics | `client.analytics` | statistics, conversion, status_conversion |
| Reference Data | `client.reference_data` | campuses, countries, languages, application_status_settings, etc. |
| CMS Settings | `client.cms_settings` | get |
| Metafields | `client.metafields` | get, field_settings, default_field_settings |

## Emergency contacts, medical data and consents

Two things are commonly reported as "missing from the API". Neither is:

**Emergency contacts, medical data and guardians** are on the application
*detail* serializer only. `applications.list()` returns a lighter summary
serializer that omits them, so iterating the list endpoint never surfaces
them:

```python
# Not there — list() returns the summary serializer
app = next(iter(client.applications.list(page_size=1)))
"emergency_contacts" in app          # False

# There — detail serializer
client.applications.emergency_contacts(application_id)
client.applications.medical_data(application_id)
client.applications.guardians(application_id)
```

**Photo/video consents** are not application fields at all — they are answers
on a custom form, stored in that submission's `payload`:

```python
form = client.forms.find("photo-permission")          # by title or slug
for submit in client.forms.submits_for_application(app_id, form=form["id"]):
    for name, answer in client.forms.consents(submit["id"]).items():
        print(answer["label"], answer["value"])
```

For a bulk load, the CSV export flattens student details, emergency contacts
and every consent answer into one row per submission — in a single request:

```python
client.forms.export_submits("consents.csv", form=form["id"], is_completed=True)
```

If you want structured JSON instead, use `iter_answers()`. Note that the
`submits()` summary records carry `student_profile` but **not** the submit's
own id, so they can't be passed to `get_submit()`; `iter_answers()` resolves
that for you at the cost of one request per application:

```python
for record in client.forms.iter_answers(form=form["id"], is_completed=True):
    print(record["student_profile"]["last_name"], record["answers"])
```

See [`examples/16_emergency_contacts_and_consents.py`](examples/16_emergency_contacts_and_consents.py).

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

## Testing

```bash
pip install -e ".[dev]"
pytest
```

- **Unit tests** (`tests/test_unit.py`) run fully offline and need no credentials.
- **Integration tests** (`tests/test_integration.py`) make real API calls and **only work with a valid `.env` file** providing `ENROLHQ_BASE_URL` and `ENROLHQ_API_TOKEN`. Without valid credentials they cannot authenticate and will fail.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## License

MIT
