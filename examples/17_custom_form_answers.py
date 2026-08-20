"""Discover custom forms, pick one, and read a student's answers to it.

Nothing here is hardcoded — every id is discovered at runtime:

    list the custom forms
      -> pick one
        -> find a student who submitted it
          -> read that student's answers

Run it as-is against any instance. Set FORM_NAME to a form's title or slug to
target a specific form instead of the busiest one.
"""

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

# Set to a form title or slug (e.g. "photo-permission") to pick that form.
# Leave as None to use whichever custom form has the most submissions.
FORM_NAME = None

# ── 1. Which custom forms exist? ────────────────────────────

# `list()` returns every form including the built-in stubs (enquiry, event
# booking, ...). `kind == "CUSTOM"` narrows it to the school's own forms.
forms = [f for f in client.forms.list(page_size=100) if f["kind"] == "CUSTOM"]

if not forms:
    raise SystemExit("This instance has no custom forms.")

# `submits_page` with page_size=1 is the cheapest way to get a count — the
# response carries the total. Count once and reuse; the API is rate limited,
# so don't re-query per form in the selection step below.
completed_counts = {
    form["id"]: client.forms.submits_page(
        form=form["id"], is_completed=True, page_size=1
    ).count
    for form in forms
}

print(f"{len(forms)} custom forms:\n")
for form in forms:
    print(f"  {form['title']}")
    print(f"    slug={form['form_slug']}  "
          f"completed submissions={completed_counts[form['id']]}")

# ── 2. Choose one ───────────────────────────────────────────

if FORM_NAME:
    form = client.forms.find(FORM_NAME)
    if form is None:
        raise SystemExit(f"No form matching {FORM_NAME!r}.")
else:
    # Default to the busiest form, so the example has something to show on
    # any instance.
    form = max(forms, key=lambda f: completed_counts[f["id"]])
    if not completed_counts[form["id"]]:
        raise SystemExit("No custom form on this instance has a completed submission.")

print(f"\nUsing form: {form['title']} ({form['form_slug']})")

# ── 3. Find a student who submitted it ──────────────────────

# Submits list records carry `student_profile` but NOT the submit's own id,
# so take the profile id here and resolve the submit in the next step.
page = client.forms.submits_page(form=form["id"], is_completed=True, page_size=1)
if not page:
    raise SystemExit(f"No completed submissions for {form['title']!r}.")

student = page[0]["student_profile"]
profile_id = student["id"]
print(f"Student: {student['first_name']} {student['last_name']} "
      f"(Year {student['entry_grade']}, {student['entry_year']}) {profile_id}")

# ── 4. Read that student's answers ──────────────────────────

# `answers_for_application` resolves the submit ids via the application
# detail, then labels each answer using the form's own schema.
records = client.forms.answers_for_application(profile_id, form=form["id"])

for record in records:
    print(f"\nSubmitted {record['completed_at']}")
    section = None
    for answer in record["answers"]:
        if answer["section"] != section:
            section = answer["section"]
            print(f"\n  {section}")

        if answer["is_profile_backed"]:
            # EMERGENCY_CONTACTS / MEDICAL_DATA / PARENT_*_CONTACTS / DOCUMENTS
            # are a snapshot taken when the form was opened. The application
            # detail holds the authoritative current value.
            value = answer["value"]
            if isinstance(value, list):
                summary = f"{len(value)} record(s)"
            elif isinstance(value, dict) and "documents" in value:
                # A DOCUMENTS element is a document *group*, not a list — its
                # files are under "documents".
                summary = f"{len(value['documents'])} file(s)"
            elif isinstance(value, dict):
                summary = f"{len(value)} field(s)"
            else:
                summary = "no data"
            print(f"    [{answer['element_type']}] {answer['label'] or answer['name']}"
                  f": {summary} — see applications.get() for current values")
            continue

        label = answer["label"] or answer["name"]
        print(f"    {label}: {answer['value']}")

# ── 5. The same answers, straight from the profile id ───────

# One call, if you already know the student profile you care about.
for record in client.forms.answers_for_application(profile_id):
    answered = [a for a in record["answers"] if not a["is_profile_backed"]]
    print(f"\n{record['form_id']}: {len(answered)} answers "
          f"({record['completed_at']})")
