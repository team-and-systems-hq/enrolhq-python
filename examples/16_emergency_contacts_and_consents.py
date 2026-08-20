"""Pull emergency contacts, medical data, and photo/video consents.

These are the two things a list-based export appears to be "missing":

1. **Emergency contacts and medical data** live on the application *detail*
   serializer only. ``applications.list()`` returns a lighter summary
   serializer that omits them, so iterating the list endpoint never surfaces
   them no matter which filters you pass. Fetch the detail record per
   application (or use the convenience accessors below).

2. **Photo/video consents** are not application fields at all. They are
   answers on a *custom form* the parent submits, and live in that submit's
   ``payload`` — reachable via ``client.forms``.

This mirrors the dashboard's "Custom Form Submits" report
(``/dashboard/reports/form-submits/``).
"""

import csv

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

APPLICATION_ID = "your-application-uuid"

# ── 1. Emergency contacts (detail serializer) ───────────────

for contact in client.applications.emergency_contacts(APPLICATION_ID):
    print(f"{contact['title']} {contact['first_name']} {contact['last_name']}"
          f" ({contact['relationship_to_student']})"
          f" mobile={contact['mobile_phone']} home={contact['home_phone']}")

# Medical data and guardians come off the same detail record.
medical = client.applications.medical_data(APPLICATION_ID)
print(medical.get("doctor", {}).get("name"), medical.get("medicare_number"))

# One detail call is enough if you want several of them at once — the
# convenience accessors each make their own request.
application = client.applications.get(APPLICATION_ID)
print(len(application["emergency_contacts"]), "contacts",
      len(application["guardians"]), "guardians")

# ── 2. Which forms exist ────────────────────────────────────

for form in client.forms.list(page_size=100):
    print(f"{form['kind']:12s} {form['title']} ({form['form_slug']}) {form['id']}")

# Look a form up by title or slug when you only know its name.
permission_form = client.forms.find("medical-update")

# ── 3. Consents for one application ─────────────────────────

# `submits_for_application` reads the submit IDs off the application detail
# and fetches each one, because the submits endpoint has no per-application
# filter. Pass `form=` to narrow it to a single form.
submits = client.forms.submits_for_application(
    APPLICATION_ID, form=permission_form["id"]
)

for submit in submits:
    print(f"submitted {submit['completed_at']}")

    # `consents` returns just the yes/no answers, keyed by field name.
    for name, answer in client.forms.consents(submit["id"]).items():
        print(f"  {answer['label']}: {answer['value']}   [{name}]")

    # `answers_from` gives every element, labelled and in form order —
    # useful when you want the free-text and structured answers too.
    for answer in client.forms.answers_from(submit):
        if answer["is_profile_backed"]:
            # EMERGENCY_CONTACTS / MEDICAL_DATA / PARENT_*_CONTACTS are a
            # snapshot taken when the form was opened. The application detail
            # is authoritative for their current value.
            continue
        print(f"  [{answer['element_type']}] {answer['label']}: {answer['value']}")

# ── 4. Bulk: every submission of a form ─────────────────────

# Filters: form (the form UUID — note it is `form`, not `form_id`),
# entry_year, entry_grade, application_statuses, is_completed.
for submit in client.forms.submits(
    form=permission_form["id"], entry_year=2027, is_completed=True, page_size=100
):
    student = submit["student_profile"]
    print(student["first_name"], student["last_name"], submit["completed_at"])

# Started but never finished — chase these up.
outstanding = client.forms.submits_page(
    form=permission_form["id"], is_completed=False, page_size=1
)
print(f"{outstanding.count} incomplete submissions")

# Careful: these summary records carry `student_profile` but NOT the submit's
# own id, so you cannot pass them to `get_submit()`. `iter_answers` walks
# `student_profile.id` back through the application detail for you.
for record in client.forms.iter_answers(
    form=permission_form["id"], entry_year=2027, is_completed=True
):
    student = record["student_profile"]
    consents = {
        answer["label"]: answer["value"]
        for answer in record["answers"]
        if answer["element_type"] == "RADIO"
    }
    print(student["first_name"], student["last_name"], consents)

# ── 5. Bulk export (fastest path for a warehouse load) ──────

# `iter_answers` costs one request per application. The CSV export flattens
# student details, emergency contacts, medical data and every consent answer
# into one row per submission in a single request — prefer it for a
# warehouse load.
path = client.forms.export_submits(
    "consents.csv", form=permission_form["id"], is_completed=True
)
with open(path, newline="") as f:
    rows = list(csv.DictReader(f))
print(f"{len(rows)} rows, {len(rows[0])} columns")
for row in rows:
    print(row["profile.first_name"], row["payload.group_3_social_media"])
