"""Events and event bookings."""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

# List upcoming events
print("=== Events ===")
for event in client.events.list():
    print(f"  {event.get('title', 'Untitled')} — {event.get('start_datetime', '?')}")

# Get a single event
# event_detail = client.events.get("event-uuid")

# Create a new event
# new_event = client.events.create({
#     "title": "Open Day 2026",
#     "start_datetime": "2026-05-01T09:00:00+10:00",
#     "end_datetime": "2026-05-01T12:00:00+10:00",
# })

# List bookings
print("\n=== Bookings ===")
for booking in client.event_bookings.list(page_size=10):
    print(f"  Booking {booking['id']}")
