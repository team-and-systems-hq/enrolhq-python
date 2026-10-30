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
# schools hosted on enrolhq.net.au (or set ENROLHQ_DOMAIN=enrolhq.net.au)
client = EnrolHQClient(instance="yourschool", domain="enrolhq.net.au", api_token="your_token")
```

Always use the school's **canonical host**. EnrolHQ answers any other host with
a 301 redirect, and following a redirect drops the `Authorization` header and
turns a POST/PUT into a GET. The SDK therefore does not follow redirects on
writes; it raises `EnrolHQError` naming the canonical URL instead.

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
| Applications | `client.applications` | list, get, create, update, count, field_choices, actions, bulk ops |
| Leads | `client.leads` | list, get, create, update, references, create_reference |
| Forms | `client.forms` | list, get, find, definition, save_schema, update_definition, check_local_fields, preview, validate_step, submits, get_submit, answers, consents, iter_answers, export_submits |
| Documents | `client.documents` | list, upload, download, delete |
| Notes | `client.notes` | list, create |
| Activity Log (Comms Log) | `client.activity_log` | list, create, delete |
| Audit Log | `client.audit_log` | list (by student_profile or parent) |
| Email Log | `client.email_log` | list |
| Events | `client.events` | list, get, create, update, delete |
| Event Bookings | `client.event_bookings` | list, create, update |
| Payments | `client.payments` | order_lines, batch_update_order_lines |
| Staff | `client.staff` | list, get, create, update, toggle_active |
| Analytics | `client.analytics` | statistics, conversion, status_conversion |
| Reference Data | `client.reference_data` | campuses, countries, languages, application_status_settings, etc. |
| CMS Settings | `client.cms_settings` | get, update, update_fields, custom_scripts, append_custom_scripts, set_custom_scripts |
| Metafields | `client.metafields` | get, field_settings, default_field_settings, update_field, create_field, delete_field, toggle_block, mutate_ordering |
| School settings | `client.school` | get, update, update_fields, set_region, commencement dates |
| Campuses | `client.campuses` | list, get, default, create, update, update_fields, set_images |
| Look and feel | `client.look_and_feel` | get, update, set_palette, set_form_header_themes, set_fonts, font_library, upload_font, find_or_upload_font |
| Event settings | `client.event_settings` | get, update, update_fields, kind_options, ensure_kinds |
| Entry grade settings | `client.entry_grade_settings` | get, update, modify_grades |
| Payment settings | `client.payment_settings` | get, update, update_fields |

## Comms Log entries and notes

The Comms Log on a student profile is `client.activity_log`. Each entry has an
`activity_kind`, a `description` and an `occurred_at` time:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from enrolhq import ActivityKind

entry = client.activity_log.create(
    "student-uuid",
    ActivityKind.PHONE_CALL,
    "Mum called to confirm the Term 1 start date.",
    occurred_at=datetime(2026, 3, 2, 14, 15, tzinfo=ZoneInfo("Australia/Sydney")),
)
client.activity_log.delete(entry["id"])  # undo
```

`occurred_at` defaults to now. A naive datetime is rejected so that imported
history keeps its real time; pass an aware datetime or an ISO 8601 string with
an offset. Kinds: `INTERNAL_NOTE`, `EMAIL`, `PHONE_CALL`, `SMS`,
`FACE_TO_FACE_MEETING`, `SCHOOL_EVENT`, `LETTER`, `PRIVATE_TOUR`,
`ITEM_POSTED`, `OTHER`. To attach a file, pass `attachment=file_data_uri(path)`.

Notes (the Notes tab) are separate: `client.notes.create("student-uuid", "text")`.
Neither sends anything to families. Entries and notes are created as the staff
user the API token belongs to.

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

## Decoding coded fields

Some fields come back as numbers, not text. A parent's
`relationship_to_student` is `0` for Mother and `1` for Father, and
`student_resides_with` is `0` for "Both Parents Together". Neither the settings
API (`school/`) nor metafields lists these codes. The applications endpoint
does, in its `OPTIONS` metadata, and `field_choices()` reads it for you:

```python
choices = client.applications.field_choices()
relationships = choices["user_parent.relationship_to_student"]

app = client.applications.get(application_id)
for key in ("user_parent", "non_user_parent"):
    parent = app.get(key) or {}
    code = parent.get("relationship_to_student")       # e.g. 0, or None if unanswered
    print(parent.get("first_name"), relationships.get(code))   # "Mother"
```

Keys are field paths: nested fields are joined with dots and list items drop
their index (`emergency_contacts.relationship_to_student`). Each value maps a
code to its label. It covers about 35 fields, including
`student_resides_with`, `residency_details.residency_status`, `entry_grade`,
`aboriginal_statuses` and the `enrolment_review` / `gpa_review` approvals.

The parent relationship codes (`user_parent` and `non_user_parent`) are:

| Code | Relationship | Code | Relationship |
|------|--------------|------|--------------|
| 0 | Mother | 10 | Agent |
| 1 | Father | 11 | Cousin |
| 2 | Legal Guardian (court-appointed) | 12 | Adult sister |
| 4 | Stepmother | 13 | Adult brother |
| 5 | Stepfather | 14 | Carer (nominated by parent) |
| 6 | Grandmother | 15 | Foster Carer |
| 7 | Grandfather | 16 | Caseworker/Manager |
| 8 | Aunt | 17 | Exchange Programme Host |
| 9 | Uncle | | |

There is no code 3. The value is `null` when the parent hasn't answered.
Prefer `field_choices()` over hard-coding this table, so new codes are picked
up.

Things that look related but aren't:

- **`parents_relationships`** (`client.reference_data.parent_relationships()`,
  `school/` and the application's `parents_relationships` list of ids) is how
  the parents relate to *each other*: Parents Married, Parents Divorced, Single
  Parent and so on.
- **Emergency contact** relationships are text, not codes ("Aunt", "Family
  Friend"). Each school sets its own list, which is also in metafields under
  `emergency_contact.relationship_to_student.options`. "Other" fills in
  `relationship_to_student_other`.
- **Guardian** relationships are free text.

Without the SDK, trade the API token for an access token, then send an
`OPTIONS` request (not a `GET`) to `applications/`:

```bash
BASE="https://yourschool.enrolhq.com.au/api/v2"

ACCESS=$(curl -s -X POST "$BASE/accounts/refresh/" \
  -H "Authorization: Token $ENROLHQ_API_TOKEN" | jq -r .access_token)

curl -s -X OPTIONS "$BASE/applications/" \
  -H "Authorization: Token $ACCESS" \
  -H "Accept: application/json" \
  | jq '.actions.POST.user_parent.children.relationship_to_student.choices'
# [{"value": 0, "display_name": "Mother"}, {"value": 1, "display_name": "Father"}, ...]
```

The response describes the fields `POST applications/` accepts. Nested objects
list their fields under `children`, and lists describe their items under
`child` (for example
`.actions.POST.emergency_contacts.child.children.relationship_to_student.choices`).

See [`examples/21_field_choices.py`](examples/21_field_choices.py).

## Configuring a school

Everything set up under *Settings* when onboarding a school can be written
through the API: name and region, campus contact details and branding images,
colours and fonts, form copy and policy documents, year levels, event kinds and
tours, "How did you hear about us?" options, and currency/GST.

```python
from enrolhq import EnrolHQClient, session

client = EnrolHQClient()

client.school.set_region(tzname="Pacific/Auckland", country="NZ")
client.school.update_fields({"name": "Example Grammar"})

campus = client.campuses.default()
client.campuses.update_fields(campus["id"], {"telephone": "+6490000000"})
client.campuses.set_images(
    campus["id"],
    logo_dark="logo-dark.png",
    favicon="favicon-512.png",
    default_header_image="campus-1920x600.jpg",
)

client.look_and_feel.set_palette(primary_color="#08080A", secondary_color="#8B7347")
brand = client.look_and_feel.find_or_upload_font("Playfair Display", "pf.woff", "pf.woff2")
client.look_and_feel.set_fonts(brand=brand["id"])

client.cms_settings.update_fields({"enquiry": {"page_header": "Enquire with us"}})

kinds = client.event_settings.ensure_kinds(["School Tour"])
client.events.create({
    "name": "Principal's Tour",
    "kind": kinds[0]["id"],
    "campus": campus["id"],
    "sessions": [session("Tuesday tour", "2027-02-02", "09:30", "10:30", capacity=20)],
})
```

Things the settings endpoints have in common:

- **No PATCH.** Each object takes a full PUT validated in full. The
  `update_fields()` helpers do GET → deep-merge → PUT, so you only pass what
  changes. Nested dicts merge; wrap a value in `Replace(...)` to replace a dict
  wholesale (e.g. a country, which the server looks up by `id` first).
  `school.set_region()` and `campuses.update_fields()` do this for `country`.
- **Nested lists are replaced wholesale.** Rows with a known `id` are updated,
  rows without one are created, and existing rows you leave out are deleted.
  This applies to event sessions, event kinds, attendance types and policy
  items.
- **Files are base64 data URIs in the JSON body, not multipart uploads.**
  `image_data_uri()` and `file_data_uri()` build them; PNG/JPEG/WebP only, so
  convert SVG, ICO and GIF first. A GET returns URLs, which the server rejects
  on write; the campus helpers only send the image slots you change.
- **Permissions.** A permanent API token belongs to a superuser and can write
  all of this. With a regular login, the default *Admin* role covers school,
  CMS, campus and metafields settings, and *Registrar* covers events, event
  settings, payments and email.

See [`examples/18_school_branding.py`](examples/18_school_branding.py),
[`19_tours_and_events.py`](examples/19_tours_and_events.py) and
[`20_region_and_year_levels.py`](examples/20_region_and_year_levels.py).

## Receiving sync signals (integration service)

EnrolHQ can push sync signals *out* to a service you host — the URL configured
under **Settings > Integrations > Integration Service Edit**. It `POST`s JSON
carrying student profile ids, authenticated with the shared bearer token from
that screen; you read the profiles with this SDK, write them into the school's
SIS, and report the outcome back.

There are two protocols (which one fires depends on the school's `NEW_SYNC`
feature flag, so handle both): a legacy synchronous one where you return the
result in the HTTP response body within the configured timeout, and an async one
that hands you a `sync_request` id to acknowledge immediately and answer later
via `POST {school_domain}/api/v2/integrations/sync/finished/`.

See [docs/integration-service.md](docs/integration-service.md) for the payload
shapes, response schemas, what the token and timeout actually control, and a
working receiver.

## Building custom forms

Build or change a form's steps and questions through the API, for example
from a school's Word or PDF document. Save the new schema as a draft, check
it with the staff preview and the no-save step validation, then publish:

```python
assert not client.forms.check_local_fields(overrides)
client.forms.save_schema(form_id, steps, local_fields_settings=overrides)  # draft
client.forms.validate_step(form_id, 1, step_one_answers)                  # saves nothing
client.forms.save_schema(form_id, steps, publish=True)                     # parents see it
```

See [docs/custom-forms.md](docs/custom-forms.md) for the schema and element
types, per-form field settings, where answers are stored, styling, and a
step-by-step workflow.

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
