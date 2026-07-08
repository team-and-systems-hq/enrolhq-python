"""Work with leads (pre-enquiry contacts) and lead references.

A lead captures a contact (usually a parent) and optionally a prospective
student before a full application exists — e.g. from a "keep me updated"
website form. This example lists leads, reads lead references, creates a
lead, and updates one.

WARNING: The create/update sections write real data to your instance.
"""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

# ── Lead references ─────────────────────────────────────────
# A lead reference identifies which form/source a lead came from. Use its
# `id` as the `reference` field when creating a lead.

references = client.leads.references()
for ref in references:
    print(f"{ref['name']} ({ref['slug']}): {ref['id']}")

# Create a lead reference. There is no dedicated write endpoint — the SDK
# round-trips the school/ settings object and returns the new record with
# its server-assigned id. Creating an existing slug raises ValueError, so
# reuse the reference if this example has run before.
REF_SLUG = "sdk-example-reference"
existing = [r for r in references if r["slug"] == REF_SLUG]
reference = existing[0] if existing else client.leads.create_reference(
    "SDK Example Reference", REF_SLUG
)
print(f"Using reference: {reference['name']} ({reference['id']})")

# ── List leads ──────────────────────────────────────────────

# Iterate every lead (auto-paginates through all pages).
for lead in client.leads.list(page_size=100):
    student = lead["student"] or {}
    print(lead["email"], lead["first_name"], lead["last_name"],
          student.get("entry_year"))

# Filter: only leads not yet linked to a student profile.
page = client.leads.list_page(has_student_profile=False, page_size=25)
print(f"{page.count} leads without a linked profile")

# ── Get a single lead ───────────────────────────────────────

if page:
    detail = client.leads.get(page[0]["id"])
    print(detail["email"], detail["reference"], detail["lead_status"])

# ── Create a lead ───────────────────────────────────────────

new_lead = client.leads.create({
    "email": "jane.doe@example.com",
    "title": "Mrs",
    "first_name": "Jane",
    "last_name": "Doe",
    "mobile_phone": "+61400000000",
    "reference": reference["id"],
    "student": {
        "first_name": "Sam",
        "last_name": "Doe",
        "dob": "2015-03-15",
        "entry_grade": 7,
        "entry_year": 2028,
        "comment": "Interested in the music program",
        "questions": [],
        "questions_other": "",
    },
    "residential_address": {
        "apartment": "",
        "street_address": "1 Example St",
        "city": "",
        "suburb": "ULTIMO",
        "state": "NSW",
        "postcode": "2007",
        "country": None,
    },
    "how_hear": [],
    "how_hear_other": "",
    # Set this to a student profile UUID to link the lead to an existing
    # application; None creates a standalone lead.
    "student_profile": None,
})
print(f"Created lead: {new_lead['id']}")

# ── Update a lead ───────────────────────────────────────────
# Updates use PUT (full replacement): get -> modify -> update.

lead = client.leads.get(new_lead["id"])
lead["student"]["comment"] = "Followed up by phone"
updated = client.leads.update(lead["id"], lead)
print(f"Updated: {updated['student']['comment']}")
