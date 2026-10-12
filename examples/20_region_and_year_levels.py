"""Set a school's region, year levels and form options (e.g. a New Zealand school).

WARNING: with --apply this changes live school settings.

    python examples/20_region_and_year_levels.py            # show current values
    python examples/20_region_and_year_levels.py --apply

Region is data, not a separate deployment: timezone and country on the school,
currency and GST on payment settings, "Year" wording in CMS settings, and the
year levels offered in entry grade settings (Year 13 is off by default).
"""

import sys

from enrolhq import EnrolHQClient

ENTRY_GRADES = range(9, 14)          # Years 9-13
ENTRY_YEARS = list(range(2027, 2033))
HOW_HEAR = ["Word of mouth", "Open Day", "Website", "Social media", "Other"]

client = EnrolHQClient()  # reads from .env
apply = "--apply" in sys.argv

school = client.school.get()["school"]
payments = client.payment_settings.get()
grades = client.entry_grade_settings.get()
print(f"Timezone/country: {school['tzname']} / {school['country']['alpha_2_code']}")
print(f"Currency/GST:     {payments['currency']} / {payments['gst_percent']}%")
print("Entry grades:     ", [
    row["entry_grade"] for row in grades["entry_grade_settings"]
    if any(c["is_available"] for c in row["campus_entry_years_settings"])
])

if not apply:
    print("\nDry run - pass --apply to write.")
    sys.exit()

# Timezone first: event session times are interpreted in it.
client.school.set_region(tzname="Pacific/Auckland", country="NZ")
client.school.update_fields({"business_number_abbreviation": "NZBN"})
client.payment_settings.update_fields({"currency": "NZD", "gst_percent": "15.0"})
client.cms_settings.update_fields({"school_level_label": "Year"})


def offer_senior_years(row):
    offered = row["entry_grade"] in ENTRY_GRADES
    for campus in row["campus_entry_years_settings"]:
        campus["is_available"] = offered
        for form in ("eoi", "enr", "enq", "evt"):
            campus[f"{form}_entry_years"] = ENTRY_YEARS if offered else []


# NZ children start Year 1 at five, so the predicted entry year uses age 5.
client.entry_grade_settings.modify_grades(offer_senior_years, first_grade_age=5)

# "How did you hear about us?" options are a metafield shared by every form.
client.metafields.update_field("parent", "how_hear", {"options": HOW_HEAR})

print("Region and year levels updated.")
