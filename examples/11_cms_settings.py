"""Read the school's CMS / form configuration settings.

The `cms-settings/` endpoint is read-only and returns a single config object
covering enquiry & event-booking copy, form labels, terms & conditions,
parent-dashboard visibility flags, and the policy documents shown to applicants.
"""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

settings = client.cms_settings.get()

# Top-level labels used throughout the parent-facing forms
print("Parent label:        ", settings.get("parent_label"))
print("Plural parent label: ", settings.get("parents_label_plural"))
print("School level label:  ", settings.get("school_level_label"))
print("Student code enabled:", settings.get("is_student_code_enabled"))

# Event-booking page copy is nested under its own object
event_booking = settings.get("event_booking", {})
print("\nEvent booking page header:", event_booking.get("page_header"))
print("Make-booking button label:", event_booking.get("make_booking_button_label"))

# Policy documents applicants must agree to (PDFs / links)
policies = settings.get("school_policy_agreement_items", [])
print(f"\nPolicy agreement items: {len(policies)}")
for item in policies:
    print(f"  - {item.get('label')}: {item.get('file_src') or item.get('url')}")
