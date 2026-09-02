"""Copy a student profile from one EnrolHQ instance to another.

`ProfileCopier` reads a student from a source instance and writes them to a
target instance, looking them up there by name and date of birth: an existing
profile is updated, otherwise one is created first. Trashed profiles are
ignored, so a binned record is never revived.

No two instances are configured alike, so the copier filters the payload
through the target's own field schema and translates lookup values (campus,
attendance type, ...) by name, because their IDs differ per instance. Fields
and lookup values the target has no equivalent for are reported on the result.
Documents are not copied — use `client.documents` for those.

Unlike the other examples this one needs two instances, so it takes its
credentials from a SOURCE / TARGET pair of environment variables:

    export ENROLHQ_SOURCE_BASE_URL=https://source-school.enrolhq.com.au/api/v2/
    export ENROLHQ_SOURCE_API_TOKEN=your_source_token
    export ENROLHQ_TARGET_BASE_URL=https://target-school.enrolhq.com.au/api/v2/
    export ENROLHQ_TARGET_API_TOKEN=your_target_token

WARNING: This writes real data to the target instance. The source is only read.
"""

import os

from enrolhq import EnrolHQClient, ProfileCopier

source = EnrolHQClient(
    base_url=os.environ["ENROLHQ_SOURCE_BASE_URL"],
    api_token=os.environ["ENROLHQ_SOURCE_API_TOKEN"],
)
target = EnrolHQClient(
    base_url=os.environ["ENROLHQ_TARGET_BASE_URL"],
    api_token=os.environ["ENROLHQ_TARGET_API_TOKEN"],
)

# Replace with a real application UUID from your source instance.
SOURCE_APPLICATION_ID = "application-uuid"

student = source.applications.get(SOURCE_APPLICATION_ID)
print(f"Copying {student['first_name']} {student['last_name']} ({student['dob']})")
print(f"  from {source.base_url}")
print(f"  to   {target.base_url}")

result = ProfileCopier(source, target).copy(SOURCE_APPLICATION_ID)

print(f"\n{'Created' if result.created else 'Updated'} {result.application_id}")
print(f"  {len(result.copied)} fields copied")

# Fields the target instance does not have, or does not allow writing to.
if result.dropped:
    print(f"  {len(result.dropped)} not accepted: {', '.join(result.dropped)}")

# Lookup values with no equivalent on the target, e.g. a campus that only
# exists at the source school.
for skipped in result.skipped_lookups:
    print(f"  no match on target: {skipped}")

# Check what landed — the copy is idempotent, so running it again updates the
# same profile rather than creating a second one.
copied = target.applications.get(result.application_id)
print(f"\nOn target: {copied['first_name']} {copied['last_name']}")
print(f"  entry: grade {copied['entry_grade']} in {copied['entry_year']}")
print(f"  parent: {copied['user_parent']['first_name']} {copied['user_parent']['last_name']}")