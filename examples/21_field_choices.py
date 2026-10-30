"""Turn coded fields (0, 1, ...) into labels such as "Mother" and "Father".

Some application fields come back as numbers. A parent's
``relationship_to_student`` is ``0`` for Mother and ``1`` for Father,
``student_resides_with`` is ``0`` for "Both Parents Together", and so on.
Neither the settings API nor metafields lists these codes. The applications
endpoint does, in its ``OPTIONS`` metadata, which ``field_choices()`` reads.

    python examples/21_field_choices.py                    # list the codes
    python examples/21_field_choices.py <application-uuid> # decode one application
"""

import sys

from enrolhq import EnrolHQClient

client = EnrolHQClient()  # reads from .env

# One request. Keys are field paths; each value maps a code to its label.
choices = client.applications.field_choices()

# ── 1. Every coded field ────────────────────────────────────

for path, labels in sorted(choices.items()):
    print(f"{path:55s} {len(labels):3d} values")

# ── 2. Parent relationship codes ────────────────────────────

# The same list applies to both parents (user_parent and non_user_parent).
print("\nParent relationship to student:")
for code, label in choices["user_parent.relationship_to_student"].items():
    print(f"  {code:>2}  {label}")

# ── 3. Decode one application ───────────────────────────────

if len(sys.argv) > 1:
    app = client.applications.get(sys.argv[1])

    def label(path, value):
        """Look up a code's label; None when unanswered or unknown."""
        return choices.get(path, {}).get(value)

    print("\nResides with:",
          label("student_resides_with", app.get("student_resides_with")))

    for key in ("user_parent", "non_user_parent"):
        parent = app.get(key) or {}
        if not parent.get("first_name"):
            continue
        relationship = label(f"{key}.relationship_to_student",
                             parent.get("relationship_to_student"))
        print(f"{parent['first_name']} {parent['last_name']}: {relationship}")

    # Emergency contact relationships are already text, from the school's own
    # list. "Other" puts the family's wording in relationship_to_student_other.
    for contact in app.get("emergency_contacts", []):
        relationship = contact["relationship_to_student"]
        if relationship == "Other":
            relationship = contact.get("relationship_to_student_other") or relationship
        print(f"{contact['first_name']} {contact['last_name']}"
              f" (emergency contact): {relationship}")
