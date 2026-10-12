"""Set up tour event kinds and create (or update) a tour with sessions.

WARNING: with --apply this creates/updates a live event families can book.

    python examples/19_tours_and_events.py            # show kinds and events
    python examples/19_tours_and_events.py --apply

Gotchas this example handles:
  - ``kind`` is an event kind id from event settings, not an enum.
  - Session times are ``{"HH": "09", "mm": "30"}`` objects; ``session()``
    builds them from "09:30" strings. Times are in the school's timezone.
  - Sessions are replaced wholesale on update: keep existing ones by id.
"""

import datetime as dt
import sys

from enrolhq import EnrolHQClient, image_data_uri, session

EVENT_NAME = "Principal's Tour"
KIND = "School Tour"
IMAGE = None  # e.g. "assets/campus-1600x900.jpg"

client = EnrolHQClient()  # reads from .env
apply = "--apply" in sys.argv

settings = client.event_settings.get()
print("Event kinds:", [k["label"] for k in settings["event_kind_options"]])
for event in client.events.list():
    print(f"  {event['name']}: {len(event.get('sessions', []))} session(s)")

if not apply:
    print("\nDry run - pass --apply to create or update the event.")
    sys.exit()

# Add the kind if it is missing (existing kinds are kept).
kinds = client.event_settings.ensure_kinds([KIND])
kind_id = next(k["id"] for k in kinds if k["label"] == KIND)

# Two tours a week for the next four weeks.
today = dt.date.today()
dates = [today + dt.timedelta(days=d) for d in range(1, 29)]
sessions = [
    session(f"{day:%A %-d %B}", day, "09:30", "10:30", capacity=20, registrations_limit=6)
    for day in dates
    if day.weekday() in (1, 3)  # Tuesday, Thursday
]

event = {
    "name": EVENT_NAME,
    "kind": kind_id,
    "campus": client.campuses.default()["id"],
    "description": "<p>Join the Principal for a guided tour of the school.</p>",
    "location": "<p>Main Reception</p>",
    "attendees_limit_per_booking": 4,
}
if IMAGE:
    event["image"] = image_data_uri(IMAGE)

existing = client.events.find(EVENT_NAME)
if existing is None:
    created = client.events.create({**event, "sessions": sessions})  # slug is generated
    print(f"Created {created['name']} ({created['slug']})")
else:
    current = client.events.get(existing["id"])
    # Keep the ids of sessions that already exist so their bookings survive.
    by_date = {(s["date"], s["start_time"]["HH"], s["start_time"]["mm"]): s["id"]
               for s in current["sessions"]}
    for s in sessions:
        key = (s["date"], s["start_time"]["HH"], s["start_time"]["mm"])
        if key in by_date:
            s["id"] = by_date[key]
    client.events.update(current["id"], {**event, "slug": current["slug"], "sessions": sessions})
    print(f"Updated {current['name']}")
