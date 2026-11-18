"""Pull the applications in a school's admission processes, with their answers.

A school can accept several kinds of application (a junior school
application, a scholarship application, ...). Each kind is an admission
process, and a student holds one application per process they have started,
each with its own status and entry details. The student record itself only
shows the primary one.

    python examples/22_admission_processes.py                       # the processes
    python examples/22_admission_processes.py --process scholarship # one process, last 7 days
    python examples/22_admission_processes.py --process scholarship --all
    python examples/22_admission_processes.py --student <student-uuid>

Read-only. Schools without the feature answer with 403.
"""

import argparse
import datetime as dt
import itertools
import sys

from enrolhq import ApplicationStatus, EnrolHQClient, ForbiddenError

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--process", help="part of an admission process title")
parser.add_argument("--student", help="a student (application) UUID")
parser.add_argument("--all", action="store_true",
                    help="every application, not just students changed in the last 7 days")
parser.add_argument("--limit", type=int, default=5,
                    help="how many applications to read answers for (default 5)")
args = parser.parse_args()

client = EnrolHQClient()  # reads from .env

# ── 1. The processes and their forms ────────────────────────

try:
    processes = list(client.admission_processes.list())
except ForbiddenError:
    sys.exit("Admission processes are not enabled for this school.")

titles = {process["id"]: process["title"] for process in processes}
forms = {form["id"]: form for form in client.forms.list(page_size=1000)}


def form_title(form_id):
    return forms.get(form_id, {}).get("title", form_id)


def status(code):
    return ApplicationStatus(code).name


for process in processes:
    state = "" if process["is_enabled"] else " (disabled)"
    print(f"{process['title']}{state}")
    for row in process["forms"]:
        role = "submission form" if row["is_application_submission_form"] else "supporting form"
        kind = forms.get(row["custom_form"], {}).get("kind", "?")
        print(f"  {form_title(row['custom_form'])} [{kind}] - {role},"
              f" opens in {status(row['opening_application_status'])}")

# ── 2. One student's applications ───────────────────────────

if args.student:
    # Not on applications.get(): the v2 student record has no `applications`.
    applications = client.applications.student_applications(args.student)
    print(f"\n{len(applications)} application(s):")
    for application in applications:
        primary = " [primary]" if application["is_primary"] else ""
        submitted = application["submitted_at"] or "not submitted"
        entry = ("entry details not provided"
                 if application["is_new_entry_details_missing"]
                 else f"entry year {application['entry_year']}")
        print(f"  {titles[application['admission_process']]}{primary}:"
              f" {status(application['application_status'])}, {entry}, {submitted}")
        for submit in application["form_submits"]:
            done = submit["completed_at"] or "in progress"
            print(f"    {form_title(submit['form'])}: {done}")

    # The student record mirrors the primary application, so it can read
    # e.g. TRASHED while another of the student's applications is active.
    student = client.applications.get(args.student)
    print("  Student record status:", status(student["application_status"]))

# ── 3. Every application in one process, with its answers ───

if args.process:
    matches = [p for p in processes if args.process.lower() in p["title"].lower()]
    if len(matches) != 1:
        sys.exit(f"--process matched {len(matches)} processes: "
                 f"{[p['title'] for p in matches]}")
    process = matches[0]

    # One sweep of full student records (100 per request), not one request
    # per student. `admission_process` narrows the rows on this side: the
    # server still reads every student, or with `updated_after` every
    # student changed since then.
    since = None if args.all else dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    rows = list(client.applications.iter_student_applications(
        admission_process=process["id"], updated_after=since,
    ))

    scope = "all students" if args.all else f"students changed since {since.date()}"
    print(f"\n{process['title']}: {len(rows)} application(s), {scope}")
    for row in rows:
        student = row["student_profile"]  # id, sid, external_id and names
        primary = "primary" if row["is_primary"] else "not primary"
        # When the flag is set, the row's entry details are the student
        # record's, not this application's: don't report them as its own.
        entry = ("entry details not provided" if row["is_new_entry_details_missing"]
                 else f"entry year {row['entry_year']}")
        print(f"  {student['sid']}: {status(row['application_status'])},"
              f" {entry}, {primary}, submitted {row['submitted_at'] or '-'}")

    # What the family answered. Only custom forms have a readable submission;
    # for the built-in EOI and enrolment forms the answers are the student
    # record itself (client.applications.get).
    for row in rows[:args.limit]:
        for submit in row["form_submits"]:
            if forms.get(submit["form"], {}).get("kind") != "CUSTOM":
                print(f"\n  {row['student_profile']['sid']}: {form_title(submit['form'])}"
                      " is a built-in form, read the student record instead")
                continue
            answers = client.forms.answers(submit["id"])
            answered = [a for a in answers if a["value"] not in (None, "", [], {})]
            print(f"\n  {row['student_profile']['sid']}: {form_title(submit['form'])},"
                  f" {len(answered)} of {len(answers)} elements answered")
            # The form's own questions carry a label; the profile blocks
            # (student details, parents, medical, ...) come back as dicts.
            for answer in answered:
                if answer["label"]:
                    print(f"    {answer['label'][:70]}")

    # ── 4. Every submission of the process's forms ──────────
    #
    # Not every submission is attached to an application: one made before its
    # form joined the process belongs to none, so it is not in the rows
    # above. Going by form reaches every submission.
    for form_row in process["forms"]:
        form_id = form_row["custom_form"]
        if forms.get(form_id, {}).get("kind") != "CUSTOM":
            continue
        total = client.forms.submits_page(form=form_id, page_size=1).count
        line = f"\n{form_title(form_id)}: {total} submission(s) of this form"
        if args.all:
            attached = sum(1 for row in rows for submit in row["form_submits"]
                           if submit["form"] == form_id)
            line += f", {attached} attached to an application"
        print(line)
        for record in itertools.islice(client.forms.iter_answers(form=form_id), args.limit):
            answered = [a for a in record["answers"] if a["value"] not in (None, "", [], {})]
            print(f"  {record['completed_at'] or 'in progress'}:"
                  f" {len(answered)} of {len(record['answers'])} elements answered")
