# Building an EnrolHQ Integration Service

This document describes the server you build to receive sync signals from
EnrolHQ — the thing that sits behind **Integration Service URL** on
*Settings > Integrations > Integration Service Edit*.

EnrolHQ calls this an "integration service". It is the bridge between EnrolHQ
and a school's SIS (Synergetic, TASS, Sentral, PCSchool, Edumate, Compass,
Veracross, …). EnrolHQ pushes a signal to your URL; you read the student
profiles out of the EnrolHQ API (that's what this SDK is for), write them into
the SIS, and report the outcome back.

> The SDK has no `client.integrations` resource yet. This document covers the
> protocol; the examples use `requests` and, for the callback, the SDK's
> authenticated HTTP client.

---

## 1. The settings screen, field by field

| Field | Model field | What it does |
|-------|-------------|--------------|
| **Integration Service** | `name` | Which SIS this row is for. One row per school per SIS (`unique_together = (school, name)`). The value is echoed back to you in every payload as `integration`. |
| **Active** | `is_active` | Off means EnrolHQ will not call you at all — the sync endpoints 404 on `integration_services.active()`. |
| **Bulk Sync Enabled** | `is_bulk_sync_enabled` | Allows the staff "bulk sync" action over a filtered set of profiles. Off means only one-profile-at-a-time syncs. |
| **Integration Service URL** | `url` | Your HTTPS endpoint. EnrolHQ `POST`s JSON here. This is the *only* outbound destination — there are no other webhooks. |
| **Integration Service Token** | `token` | A shared secret **you** choose and paste in. EnrolHQ sends it as `Authorization: Bearer <token>`. Write-only in the API (`SecretKeyField`), so it is masked after saving — record it somewhere when you set it. Max 255 chars. |
| **Integration Service Timeout** | `timeout` | Seconds EnrolHQ waits for your HTTP response. Default `10`. Passed straight to `requests.post(..., timeout=...)`. |
| **Scheduled Sync Features** | `scheduled_sync_features` | Which sync actions staff can trigger. See [§6](#6-scheduled-sync-a-pull-not-a-push). An empty list hides the sync dropdown entirely. |
| **Additional Sync Instruction** | `sync_instruction` | A private document staff can download from the app. Not sent to you. |

### What the token and timeout actually do

**Token.** There is no HMAC, no signature, no replay protection, no IP
allowlist. Authentication is a static bearer token, chosen by you, compared by
you. So:

- Generate something long and random (`secrets.token_urlsafe(48)`).
- Compare it in constant time (`hmac.compare_digest`), not with `==`.
- Terminate TLS. The token is sent in the clear inside the header.
- Reject anything without a valid token *before* doing any work, and return
  `401`/`403`.

**Timeout.** It bounds EnrolHQ's patience, and it means different things in the
two protocols below:

- **Legacy synchronous protocol** — a staff member is sitting in front of a
  spinner while your service does the entire SIS write. The timeout must cover
  the full round trip. Blow it and the sync is recorded as a failure even if
  the SIS write actually succeeded.
- **Async (`sync_request`) protocol** — the timeout only covers your
  acknowledgement. Return `200` immediately, do the work on a worker, and post
  the result back later. A small timeout (10–30s) is correct here.

Set it in seconds. It is a `PositiveSmallIntegerField` (0–32767) and the API
marks it required, but there is no minimum validator — **do not set `0`**,
because `requests` treats a zero timeout as "give up immediately" and every
sync will fail.

---

## 2. Two protocols

Which payload you receive depends on the `NEW_SYNC` feature flag on the school.
You do not get to choose, and you cannot read the flag over the API — so
**handle both**. They are trivially distinguishable: the async payload has a
`sync_request` key and the legacy one does not.

```
Legacy (synchronous)                  Async (NEW_SYNC)
--------------------                  -----------------
EHQ ──POST──▶ you                     EHQ ──POST──▶ you
              │ writes to SIS                       │
EHQ ◀─result──┘ (within timeout)      EHQ ◀──200────┘ (ack only, empty body)
                                                    │ writes to SIS on a worker
                                      EHQ ◀─POST────┘ /integrations/sync/finished/
```

---

## 3. The inbound request

Always `POST`, from EnrolHQ to your `url`:

```http
POST /your/endpoint HTTP/1.1
Content-type: application/json
Authorization: Bearer <Integration Service Token>

{ ...payload... }
```

`school_domain` is present in every payload and is the school's own EnrolHQ
origin (`https://yourschool.enrolhq.com.au`, no trailing slash). EnrolHQ
resolves the school from the `Host` header on incoming API requests, so
**always** use the `school_domain` from the payload when you call back or read
data — never a hardcoded host. That is what makes one integration service
deployment usable by many schools.

`integration` is the `IntegrationServiceEnum` value for the row that called
you: `SYNERGETIC`, `SENTRAL`, `ENGAGE`, `SCHOOLEDGE`, `SCHOOLPRO`, `PCSCHOOL`,
`TASS`, `EDUMATE`, `KAMAR`, `ZUNIA`, `WONDE`, `COMPASS`, `SYNERGETIC_REST`,
`VERACROSS`, `SHAREPOINT`.

### 3a. Async payload (`NEW_SYNC` schools)

Sent for both single-profile and bulk syncs — the only difference is the length
of `profiles`.

```json
{
  "sync_request": "1b5f6b2e-1f6a-4a6d-9d1e-5d5b2a4c7e01",
  "school_domain": "https://yourschool.enrolhq.com.au",
  "integration": "SYNERGETIC",
  "profiles": [
    "9a7a0b3e-3d2c-4f51-a0e6-2c1b8d9f4a10",
    "0c2e7d41-5b6a-4c3f-8e9d-1a2b3c4d5e6f"
  ]
}
```

`sync_request` is the correlation id. Keep it — you need it to report back, and
EnrolHQ accepts exactly one response per `sync_request`.

### 3b. Legacy payload — single profile

```json
{
  "school_domain": "https://yourschool.enrolhq.com.au",
  "integration": "SENTRAL",
  "profile_id": "9a7a0b3e-3d2c-4f51-a0e6-2c1b8d9f4a10"
}
```

### 3c. Legacy payload — bulk sync

Capped at 100 profiles per call by EnrolHQ.

```json
{
  "school_domain": "https://yourschool.enrolhq.com.au",
  "integration": "SENTRAL",
  "profiles": ["<uuid>", "<uuid>", "..."]
}
```

### Reading the profile data

The payload carries **ids only**. Fetch the detail with this SDK, against the
`school_domain` you were given:

```python
from enrolhq import EnrolHQClient

client = EnrolHQClient(base_url=f"{school_domain}/api/v2/", api_token=API_TOKEN)

app = client.applications.get(profile_id)
contacts = client.applications.emergency_contacts(profile_id)
medical = client.applications.medical_data(profile_id)
docs = list(client.documents.list(profile_id))
```

Remember that emergency contacts, medical data and guardians are on the
*detail* serializer only, and that consents live on custom form submissions —
see the README section "Emergency contacts, medical data and consents".

---

## 4. Responding — async protocol

Two steps.

**Step 1: acknowledge.** Return any `2xx` with an empty body, within the
timeout. EnrolHQ only checks `response.ok`. If you return non-2xx or time out,
EnrolHQ raises a `ServiceError` to the staff user **and rolls the whole
`SyncRequest` back** (`send_request` is wrapped in `transaction.atomic`) — so
there is no `sync_request` row left to respond to. Never do SIS work before
acknowledging.

**Step 2: post the result** to the school's API when the work finishes:

```
POST {school_domain}/api/v2/integrations/sync/finished/
```

Authenticated as a **staff** user — the endpoint requires `IsSchoolStaff`, so a
normal EnrolHQ API token (Profile icon > API Token) belonging to a staff
account is what you want. Body:

```json
{
  "sync_request": "1b5f6b2e-1f6a-4a6d-9d1e-5d5b2a4c7e01",
  "student_profiles": [
    {
      "student_profile": "9a7a0b3e-3d2c-4f51-a0e6-2c1b8d9f4a10",
      "is_success": true,
      "error": "",
      "warning": "Address truncated to 60 chars",
      "external_id": "SIS-10023",
      "user_parent_external_id": "SIS-P-55011",
      "non_user_parent_external_id": "SIS-P-55012"
    },
    {
      "student_profile": "0c2e7d41-5b6a-4c3f-8e9d-1a2b3c4d5e6f",
      "is_success": false,
      "error": "Duplicate student record in Synergetic"
    }
  ],
  "export_file": "data:text/xml;filename:export.xml;base64,PGRhdGE+PC9kYXRhPg=="
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `sync_request` | yes | Must be a known, **unanswered** request. A second response returns `400` — `"The response to the '<id>' request has already been received."` |
| `student_profiles` | yes, non-empty | The set of `student_profile` ids must **exactly match** the ids in the request — no extras, no omissions — or `400` `"The student profiles in the response do not match the profiles in the request."` |
| `student_profiles[].is_success` | yes | Boolean, per profile. |
| `student_profiles[].error` / `.warning` | no | Strings, max 1024 chars each. Default `""`. |
| `student_profiles[].external_id` | no | The SIS id for the student. **Written back onto the student profile** when non-empty. |
| `student_profiles[].user_parent_external_id` | no | SIS id for the parent who has the EnrolHQ login. Written back. |
| `student_profiles[].non_user_parent_external_id` | no | SIS id for the second parent. Written back only if that parent exists. |
| `export_file` | no | A data URI, `xml` or `csv` only: `data:<mime>;filename:<name>.<ext>;base64,<data>`. The `filename:` segment is mandatory — without it the upload is rejected. Virus-scanned and extension-checked on arrival. |

On success EnrolHQ stores the response, writes the external ids, and notifies:

- single-profile sync → an in-app notification to the staff member
  (*"Synchronization to Synergetic for 'Jane Doe' is complete…"*);
- bulk sync → an email report to the staff member who started it, with
  `export_file` attached if you sent one.

It returns `200` with an empty body. A `400` means your payload was rejected
and **nothing was stored** — the `sync_request` is still unanswered, so a
corrected retry will be accepted.

### Sending the callback

The SDK handles the token refresh dance (long-lived API token → short-lived
access token, with automatic retry on `401`). There's no public method for this
endpoint yet, so reach through to the HTTP client:

```python
client = EnrolHQClient(base_url=f"{school_domain}/api/v2/", api_token=API_TOKEN)

client._http.post(                       # private: no public resource yet
    client.base_url + "integrations/sync/finished/",
    json=payload,
)
```

Raw equivalent, if you'd rather not depend on a private attribute:

```python
access = requests.post(
    f"{school_domain}/api/v2/accounts/refresh/",
    headers={"Authorization": f"Token {API_TOKEN}"},
    timeout=(10, 30),
).json()["access_token"]

requests.post(
    f"{school_domain}/api/v2/integrations/sync/finished/",
    headers={"Authorization": f"Token {access}"},
    json=payload,
    timeout=(10, 30),
)
```

Access tokens are short-lived — refresh on `401` and retry once.

---

## 5. Responding — legacy synchronous protocol

You return the result **in the HTTP response body**, as JSON, inside the
timeout.

The single most important rule: **always return `2xx` with a JSON body, even
when the sync failed.** EnrolHQ only reads `response.text` when
`response.ok` is true; on any other status it substitutes `response.reason`
(e.g. `"Bad Gateway"`), which is not JSON, and the sync is logged as a bare
failure with no detail. Report failures in the `errors` array of a `200`
response, not with a `500`.

### Single-profile response

```json
{
  "profile_id": "9a7a0b3e-3d2c-4f51-a0e6-2c1b8d9f4a10",
  "external_id": "SIS-10023",
  "user_parent": { "external_id": "SIS-P-55011" },
  "non_user_parent": { "external_id": "SIS-P-55012" },
  "errors": [],
  "warnings": ["Address truncated to 60 chars"],
  "message": "Application sync successful",
  "file_name": "export.xml",
  "file": "PGRhdGE+PC9kYXRhPg=="
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `profile_id` | yes | UUID, echoed from the request. |
| `external_id` | no | SIS id; written onto the student profile. |
| `user_parent` / `non_user_parent` | no | **Objects**, not strings: `{"external_id": "..."}`. `null` or `{}` is read as `""`. |
| `errors` | no | List of strings. A non-empty list marks the call-log entry `is_success=false`. |
| `warnings` | no | List of strings; shown to staff, not treated as failure. |
| `message` | no | Summary line shown in the UI and the call log (truncated to 1024 chars in the log). |
| `file_name` + `file` | no | Both or neither. `file` is base64 (no data-URI prefix here, unlike the async `export_file`); the browser offers it as a download. The base64 blob is stripped before the response is written to the call log. |

### Bulk response

```json
{
  "profiles": ["<uuid>", "<uuid>"],
  "errors": [],
  "message": "Sync complete",
  "file_name": "syn-bulk.xml",
  "file": "PGRhdGE+PC9kYXRhPg=="
}
```

`profiles` is **required** and each id must be a student profile that exists in
that school — unknown ids are a validation error.

### Failure semantics

- Body that is not valid JSON, an empty body, a non-2xx status, a connection
  error, or a timeout → the raw text is written to the call log and the staff
  user sees `"Error: Profile did not sync."`
- Valid JSON with a non-empty `errors` → logged as a failure, with your
  messages shown.
- Valid JSON with empty/absent `errors` → logged as a success.

---

## 6. Scheduled sync: a pull, not a push

The **Scheduled Sync Features** toggles do *not* create extra outbound calls.
They control which actions staff see:

| Toggle | Value | Effect |
|--------|-------|--------|
| Synchronous sync (default) | `DEFAULT_SYNC` | The immediate sync — this is the one that hits your URL (§3–§5). |
| Push All | `PUSH_ALL` | Queues a `ScheduledSync` row, direction `PUSH_ALL`. |
| Push Documents | `PUSH_DOCS` | Queues a row, direction `PUSH_DOCS`. |
| Pull All | `PULL_ALL` | Queues a row, direction `PULL_ALL`. |
| Cancel | `CANCEL` | Lets staff cancel queued, unprocessed rows. |

With all toggles off the sync dropdown does not appear at all, so at minimum
enable `DEFAULT_SYNC` if you want the webhook to fire.

The three directional features only write a queue row. **Nothing is sent to
your URL** — your service polls for work and reports back:

```python
# 1. Poll for queued work
resp = client._http.get(
    client.base_url + "integrations/scheduled_sync/",
    params={
        "is_processed": False,
        "is_cancelled": False,
        "system_name": "SYNERGETIC",
        "direction": "PUSH_ALL",
    },
)

# 2. Do the SIS work, then mark each one done
client._http.post(
    client.base_url + "integrations/scheduled_sync/mark_processed/",
    json={
        "system_name": "SYNERGETIC",          # integration name
        "student_profile": "<student uuid>",
        "direction": "PUSH_ALL",
        "error": "",                           # non-empty marks it failed
    },
)
```

Each queued row exposes `system_name`, `student_profile`, `direction`,
`created_at`, `processed_at`, `cancelled_at` and `error`. Only one unprocessed,
uncancelled row can exist per (integration, student) pair — re-queueing while
one is pending is a no-op. `mark_processed/` marks the *latest* row for that
triple as processed, and deliberately also settles a row staff cancelled while
you were mid-flight.

---

## 7. Logs

- **Call Log** — the legacy per-profile responses
  (`GET integrations/services/responses/?integration_service=<uuid>`): timestamp,
  student, raw response, message, success flag.
- **Scheduled Sync Log** — the queue
  (`GET integrations/scheduled_sync/`).
- **Sync request log** (async protocol) —
  `GET integrations/sync/` and `GET integrations/sync/for-profile/<uuid>/`,
  showing each request, its profiles, per-profile errors/warnings and the
  exported file.

Malformed async callbacks are logged server-side as
`"Wrong sync response from integration service: sync_request=… ,errors=…"`,
which is what to ask EnrolHQ support for when a callback is being rejected.

---

## 8. A minimal receiver

Handles both protocols, acknowledges first, works on a background thread.

```python
import base64
import hmac
import os
import threading

import requests
from flask import Flask, jsonify, request

from enrolhq import EnrolHQClient

app = Flask(__name__)

INTEGRATION_TOKEN = os.environ["EHQ_INTEGRATION_TOKEN"]  # matches the settings screen
API_TOKEN = os.environ["ENROLHQ_API_TOKEN"]              # staff API token, for callbacks


def authorized(req) -> bool:
    header = req.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    return scheme == "Bearer" and hmac.compare_digest(token, INTEGRATION_TOKEN)


def client_for(school_domain: str) -> EnrolHQClient:
    return EnrolHQClient(base_url=f"{school_domain}/api/v2/", api_token=API_TOKEN)


def push_to_sis(client, profile_id):
    """Return (is_success, error, warning, external_ids). Replace with real work."""
    app_detail = client.applications.get(profile_id)
    contacts = client.applications.emergency_contacts(profile_id)
    ...  # write to the SIS
    return True, "", "", {"external_id": "SIS-10023"}


def build_export_xml(results) -> bytes:
    """Optional SIS import file. Return b"" to send no export_file."""
    return b""


@app.post("/ehq/sync")
def sync():
    if not authorized(request):
        return jsonify({"detail": "invalid token"}), 401

    payload = request.get_json(force=True, silent=True) or {}
    school_domain = payload["school_domain"]

    # --- Async protocol: acknowledge now, report later ---------------------
    if payload.get("sync_request"):
        threading.Thread(
            target=run_async_sync,
            args=(school_domain, payload["sync_request"], payload["profiles"]),
            daemon=True,
        ).start()
        return "", 200

    # --- Legacy protocol: do the work inside the timeout -------------------
    client = client_for(school_domain)

    if "profile_id" in payload:                       # single profile
        profile_id = payload["profile_id"]
        ok, error, warning, ids = push_to_sis(client, profile_id)
        return jsonify({
            "profile_id": profile_id,
            "external_id": ids.get("external_id", ""),
            "user_parent": {"external_id": ids.get("user_parent_external_id", "")},
            "errors": [] if ok else [error],
            "warnings": [warning] if warning else [],
            "message": "Sync complete" if ok else "Sync failed",
        })

    errors = []                                        # bulk
    for profile_id in payload["profiles"]:
        ok, error, _, _ = push_to_sis(client, profile_id)
        if not ok:
            errors.append(f"{profile_id}: {error}")
    return jsonify({
        "profiles": payload["profiles"],
        "errors": errors,
        "message": "Bulk sync complete" if not errors else "Bulk sync finished with errors",
    })


def run_async_sync(school_domain, sync_request, profile_ids):
    client = client_for(school_domain)
    results = []
    for profile_id in profile_ids:
        try:
            ok, error, warning, ids = push_to_sis(client, profile_id)
        except Exception as exc:                        # never drop a profile
            ok, error, warning, ids = False, str(exc)[:1024], "", {}
        results.append({
            "student_profile": profile_id,
            "is_success": ok,
            "error": error[:1024],
            "warning": warning[:1024],
            **ids,
        })

    body = {"sync_request": sync_request, "student_profiles": results}

    xml = build_export_xml(results)                     # optional
    if xml:
        body["export_file"] = (
            "data:text/xml;filename:export.xml;base64,"
            + base64.b64encode(xml).decode()
        )

    client._http.post(client.base_url + "integrations/sync/finished/", json=body)
```

Things this gets right, and that are easy to get wrong:

- **Every requested profile appears in `student_profiles`.** A crash on one
  profile must still produce a row, or the whole callback is rejected for set
  mismatch and the request stays unanswered forever.
- **Acknowledge before working** on the async protocol, so the `SyncRequest`
  isn't rolled back.
- **Never `500`** on the legacy protocol — report failures in `errors` with a
  `200`.
- **`school_domain` from the payload**, never a hardcoded host.
- **Constant-time token comparison**, checked before any work.

---

## 9. Local testing

EnrolHQ ships a built-in simulator on non-production builds. Point **Integration
Service URL** at the school's own instance:

```
http://localhost:8000/api/v1/integrations/simulate/
```

It mirrors both protocols: with no `sync_request` it returns a canned legacy
body (with a `test.xml` export); with one, it queues a Celery task that posts a
synthetic response back to `integrations/sync/finished/` after ~2s — alternating
`is_success` per profile so you can see both branches. Celery workers must be
running for the async path.

Going the other way — testing *your* service against real EnrolHQ signals —
put its public URL in the field, set a token, and trigger a sync from a student
profile (**Sync <SIS>** > *Synchronous sync*), then read the Call Log or the
sync log for what EnrolHQ made of your response.
