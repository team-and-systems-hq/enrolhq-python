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

## Rate limiting

EnrolHQ instances sit behind a reverse proxy that returns **HTTP 429** when you
send requests too quickly. Bulk jobs (fetching detail for thousands of
applications, backfills, reconciliation scripts) will hit this unless you pace
them.

### Reuse one client

The single biggest cause of unexpected 429s is **creating a client per thread or
per request**. Each `EnrolHQClient` lazily calls `accounts/refresh/` to exchange
your long-lived API token for a short-lived access token, so every new client is
an extra hit on the auth endpoint — and that endpoint rate-limits harder than the
rest of the API.

```python
# BAD: a client per worker means a token refresh per worker
def fetch(app_id):
    client = EnrolHQClient()          # authenticates every call
    return client.applications.get(app_id)

# GOOD: build once, reuse everywhere
client = EnrolHQClient()
def fetch(app_id):
    return client.applications.get(app_id)
```

A single client holds one `requests.Session` (connection pooling) and one access
token, refreshed automatically only when it expires.

### Go sequential, with a small delay

Concurrency is where bulk jobs fall over. Six worker threads against a
production instance is enough to trigger 429s within seconds. Sequential
requests with a short sleep are slower per request but finish sooner overall,
because you never spend time backing off:

```python
import time

for app_id in app_ids:
    detail = client.applications.get(app_id)
    ...
    time.sleep(0.15)   # ~6 req/s, sustained without 429s
```

If you do need concurrency, keep it to 2–3 workers sharing **one** client, and
add backoff.

### Back off and retry

Retry 429s with exponential backoff rather than tight-looping:

```python
from enrolhq import RateLimitError

def with_backoff(fn, *args, attempts=6):
    for attempt in range(attempts):
        try:
            return fn(*args)
        except RateLimitError as exc:
            wait = int(exc.retry_after or 0) or 5 * (2 ** attempt)
            time.sleep(wait)
    raise RuntimeError("still rate limited after retries")
```

`RateLimitError` exposes the `Retry-After` header via `.retry_after` when the
server sends one; fall back to exponential delays when it doesn't.

> **Gotcha:** a 429 on the *token refresh* endpoint surfaces as
> `AuthenticationError`, not `RateLimitError`. The SDK auto-retries once on 401,
> which triggers a re-authentication — so if the proxy is throttling you, the
> failure arrives as `AuthenticationError: HTTP 401: Token refresh failed: <429
> Too Many Requests HTML>`. Match on the message, not just the exception type:
>
> ```python
> try:
>     detail = client.applications.get(app_id)
> except Exception as exc:
>     if "429" in str(exc) or "Too Many" in str(exc):
>         ...  # treat as rate limiting, back off and retry
>     else:
>         raise
> ```

### Make bulk jobs resumable

Cache results to disk as you go and skip what you already have. A job that dies
2,000 records in should resume, not restart:

```python
import json, os

cache = json.load(open("cache.json")) if os.path.exists("cache.json") else {}
todo = [i for i in app_ids if i not in cache]

for n, app_id in enumerate(todo, 1):
    cache[app_id] = client.applications.get(app_id)
    time.sleep(0.15)
    if n % 100 == 0:                       # checkpoint periodically
        json.dump(cache, open("cache.json", "w"))

json.dump(cache, open("cache.json", "w"))
```

### Fetch less

Prefer one paginated sweep over many single-record lookups — `list()` with a
large `page_size` returns 100–200 records per request instead of one:

```python
# One sweep, ~40 requests for 4,000 records
by_external_id = {}
for app in client.applications.list(page_size=200):
    if app["external_id"]:
        by_external_id[app["external_id"]] = app
```

Note that some documented filters are **ignored server-side** — passing
`external_id=` to `applications.list()` returns the full unfiltered result set,
not a single match. Always verify a filter narrowed the results (check
`page.count`) before relying on it; otherwise build a local index as above.

Detail (`get()`) returns fields the list serializer omits — `payments`,
addresses, medical data. Only drop to per-record fetches for the fields you
genuinely need.

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
