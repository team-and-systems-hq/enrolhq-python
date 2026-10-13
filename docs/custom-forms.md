# Building custom forms through the API

This document describes how to create and edit an EnrolHQ **custom form** (the
forms under *Dashboard > Forms*) through the API instead of the drag-and-drop
builder: what a form is made of, which endpoints read and write it, how
per-form field settings work, where parents' answers end up, how to check a
form without a parent, and how to style it.

It was written from building a 67-element enrolment agreement form from a
school's Word document, and checked against the server source. Anything not
exercised against a live instance is marked as such.

The SDK methods used here:

| Method | Does |
|--------|------|
| `client.forms.definition(form_id)` | The form's settings and latest schema version (draft included). |
| `client.forms.save_schema(form_id, steps, local_fields_settings=, publish=False, settings=)` | Save new steps as a draft (or publish), keeping everything else. |
| `client.forms.update_definition(form_id, data)` | Full PUT of a form, for changes `save_schema` doesn't cover. |
| `client.forms.check_local_fields(overrides)` | Check per-form field overrides against the school's fields before saving. |
| `client.forms.preview(form_slug)` | Staff preview: rendered schema, effective field settings, sample payload. |
| `client.forms.validate_step(form_id, step, answers)` | Validate a step's answers like a real submission, saving nothing. |
| `client.cms_settings.custom_scripts()` / `append_custom_scripts(snippet, marker=)` / `set_custom_scripts(html)` | Read and add to *Settings > Custom Scripts*. |

Errors raise the SDK's exceptions; a 400 is `ValidationError`, with the
server's field errors in `.detail`.

```python
from enrolhq import EnrolHQClient

client = EnrolHQClient()          # ENROLHQ_BASE_URL / ENROLHQ_INSTANCE + ENROLHQ_API_TOKEN
```

---

## 1. The model: a form and its schema versions

A custom form has two layers.

**Form settings** (the `CustomForm`): title, `form_slug` (the URL path, unique
per school), `kind`, `is_active`, who sees it (`allowed_campuses`,
`allowed_application_statuses`, `allowed_entry_grades`, `allowed_entry_years`,
attendance types, custom category options), dependencies (`depends_on`), print
options, payment settings and the per-campus intro and after-submit settings
(`campus_cms_settings`).

**Schema versions** (`CustomFormSchema`): the steps and elements parents fill
in, plus the per-form field settings. A form has numbered versions:

- At most **one unpublished version** (the draft). Saving with
  `is_published: false` creates it, or updates it if one already exists.
- Any number of **published versions**. Parents always get the newest
  published version. Saving with `is_published: true` publishes the draft (or
  creates a new published version).
- The staff **preview** and the dashboard builder show the **latest** version,
  draft included.
- Each save deletes older published versions that have no submissions,
  keeping the newest published one. A submission keeps pointing at the version
  it was made on, so publishing a new version never rewrites old answers.
- A form can only be `is_active: true` once it has a published version.

So a draft can be built, reviewed in the preview and edited freely while the
published version stays live, and nothing changes for parents until someone
publishes.

**Stub forms.** Forms whose `kind` is not `CUSTOM` (enquiry, event booking,
expression of interest, enrolment, enrolment offer, reserved place, register
interest) are built-in. `forms/staff/{id}/` returns 404 for them. Their
title, statuses, dependencies and after-submit settings are edited at
`forms/staff-stub-forms/{id}/`, which has no `schema`.

## 2. Endpoints

All paths are relative to the API base (`client.base_url`, e.g.
`https://<school>.enrolhq.com.au/api/v2/`).

| Method and path | SDK | What it does |
|-----------------|-----|--------------|
| `GET forms/staff/` | `forms.list()` | Every form (custom and stub), summary rows. |
| `GET forms/staff/{id}/` | `forms.definition()` | One custom form: all settings plus `schema` = the **latest** version (`schema_data`, `local_fields_settings`, `is_published`). |
| `PUT forms/staff/{id}/` | `forms.update_definition()`, `forms.save_schema()` | Replace the form: send the whole `GET` object back with your changes. Writes the settings and saves `schema` as described in section 1. |
| `POST forms/staff/` | | Create a custom form (same body shape; `id` omitted). Not exercised; the edit path above was. |
| `POST forms/staff/{id}/reorder/{position}/` | | Move the form in the dashboard list. |
| `GET/PUT forms/staff-stub-forms/{id}/` | | Settings of a built-in (stub) form. |
| `GET forms/previews/{form_slug}/` | `forms.preview()` | Staff preview of the latest version: rendered `schema` with the **effective** field settings (`schema.metafields`) and an `initial_payload` for a sample profile. |
| `POST forms/previews/submit/{form_id}/preview/{step}/` | `forms.validate_step()` | Validate one step's answers with the form's real validation. **Saves nothing.** `step` is 1-based. |
| `GET forms/{form_slug}/` | `forms.get()` | The parent-facing published form. |
| `GET metafields/` | `metafields.get()` | Global field settings (`field_settings`), the keys that per-form overrides refer to. |
| `GET/PATCH extra-frontend-code/` | `cms_settings.custom_scripts()` and friends | *Settings > Custom Scripts*: `{"page_head_html": "..."}`, see section 8. |

The staff preview page itself is `https://<school-domain>/preview/form/{form_slug}/`
(it needs a dashboard login; the API token does not open it in a browser).

## 3. Read, modify, write

The edit endpoint validates the whole object, so read it, change what you mean
to change, and send everything back. `save_schema` does that for the schema:

```python
import json

FORM_ID = "00000000-0000-0000-0000-000000000000"

current = client.forms.definition(FORM_ID)
with open("form_before.json", "w") as f:              # snapshot before writing
    json.dump(current, f)

saved = client.forms.save_schema(
    FORM_ID,
    steps,                                            # section 4
    local_fields_settings=local_fields,               # section 5; None keeps the current ones
    publish=False,                                    # draft: parents see no change
    settings={"allowed_application_statuses": [10]},  # optional: other settings, same call
)
```

For other changes, edit the `definition()` dict and send it back with
`client.forms.update_definition(FORM_ID, data)`.

Rules the server enforces:

- `kind`, `position` and `required_for` are read-only; sending them back is
  harmless.
- `form_slug` is lower-cased, at most 64 characters, unique per school
  ("This url path is already used.").
- `is_active: true` is rejected unless a published version exists or this call
  publishes one.
- A private form (`is_private`) can't be one another form requires, and loses
  its audience filters.
- `payment_settings` can't be removed once set.
- `campus_cms_settings` must not be empty; its `after_submit_settings` can't
  redirect a form to itself or to a form it depends on.

**Before overwriting a form people may have edited in the dashboard**, compare
the live `schema_data` and `local_fields_settings` with what you last wrote,
and stop if they differ. A schema `PUT` replaces the builder's work wholesale.

## 4. The schema: steps and elements

`schema_data` is a list of **steps**; each step is a page of the form:

```json
{"title": "Child's Details", "name": "child_details", "elements": [ ... ]}
```

- Step and element `name`s must be valid, lower-case Python identifiers.
- Step names must be unique, and element names must be unique **across all
  steps** of the form.
- `elements` can't be empty.
- There is no conditional logic (show-if), no table or grid element, and no
  date element: a date is an `INPUT` with a format hint in its description.

Every element has `element_type`, `name`, `is_enabled`, `css_class` and
`css_style` (the last two may be `""`). Beyond that:

### Questions (answers stored on the submission)

| `element_type` | Extra keys | Answer value |
|----------------|------------|--------------|
| `INPUT` | `label`, `description` (HTML, may be `""`), `is_required` | string |
| `TEXTAREA` | same as `INPUT` | string |
| `SELECT` | same, plus `options` (non-empty list of strings) | one option |
| `RADIO` | same, plus `options` | one option |
| `CHECKBOX` | same, plus `options` | list of ticked options |

A required `CHECKBOX` needs at least one tick, not every tick. For statements a
parent must agree to, use one `CHECKBOX` per statement with that statement as
its only option.

```json
{"element_type": "RADIO", "name": "walks_around_campus", "is_enabled": true,
 "css_class": "", "css_style": "", "is_required": true,
 "label": "I give permission for my child to be taken on walks around the campus",
 "description": "<div>Ratios are 1 adult to 6 children.</div>",
 "options": ["Yes", "No"]}
```

### Content and signatures

| `element_type` | Extra keys | Notes |
|----------------|------------|-------|
| `HTML` | `content` | Sanitised on save (section 9). |
| `PARENT_2_NOT_APPLICABLE_HTML` | `content` | Shown when the profile has no second parent. Schools often put one after the signature too, e.g. "We will contact Parent/Carer 2 for their signature, as required". |
| `SIGNATURE` | `signature_settings`: `{"is_enabled": true, "is_identification_documents_required": false, "is_principal_signature_visible": false, "sole_parent_html": ""}` | Parent signatures. |
| `NON_PARENT_SIGNATURE` | `label`, `description`, `is_required` | e.g. a student's signature. |
| `DOCUMENTS` | `label`, `description`, `is_required`, `max_user_docs_count` (1–20), `filename` | A document upload group. |

### Profile-backed blocks (answers written to the student profile)

These render a block of the profile's own fields, pre-filled from the profile,
and write the answers back to the profile on submit. They take only the common
keys. Which fields appear is controlled by the field settings of the
metafield block in the third column (section 5).

| `element_type` | What it shows | Field settings block |
|----------------|---------------|----------------------|
| `STUDENT_PERSONAL_DETAILS` | Names and date of birth (read-only), preferred name, gender, title, photo, interests | `profile` |
| `ENTRY_DETAILS` | Campus, attendance type, entry term, commencement and leaving dates, scholarships; grade, year and DOB read-only | `profile` |
| `DEMOGRAPHICS` | Ethnic origin, social units (iwi in New Zealand), home language, religion, parish, English-literacy help | `profile` |
| `RESIDENTIAL_ADDRESS` / `MAILING_ADDRESS` | The child's address(es) | `profile` + `address` |
| `PARENTS_RELATIONSHIP` | Who the child lives with, custody details, court orders and their upload | `profile` |
| `RESIDENCY_DETAILS`, `CURRENT_SCHOOL`, `CONTACT_DETAILS`, `CULTURAL_REQUIREMENTS`, `CUSTOM_CATEGORIES`, `SCHOOL_CONNECTIONS`, `SIBLINGS`, `AGENT_DETAILS`, `BILLING_DETAILS`, `RELIGION_DETAILS` | As named | `profile` (and the matching block, e.g. `residency_details`, `billing_details`) |
| `PARENT_1_PERSONAL_DETAILS` / `PARENT_2_…` | Parent names (read-only once filled), title, preferred name, gender, DOB, relationship to the student | `parent` |
| `PARENT_1_ADDRESSES` / `PARENT_2_…` | Parent residential and mailing address | `parent` + `address` |
| `PARENT_1_CONTACTS` / `PARENT_2_…` | Home, work (`business_phone`) and mobile phone, email, correspondence preferences | `parent` |
| `PARENT_1_WORK_DETAILS` / `PARENT_2_…` | Occupation, employer, industry, staff-member flag, education level | `parent` |
| `PARENT_x_RELIGION_DETAILS`, `_RESIDENCY_DETAILS`, `_ALUMNUS`, `_DEMOGRAPHICS`, `_HEALTH_CARE`, `_ACARA` | As named | `parent` |
| `HOW_HEAR` | How the family heard about the school | `parent` |
| `GUARDIANS` | Other carers | |
| `EMERGENCY_CONTACTS` | The school's required number of emergency contacts | `emergency_contact` + `address` |
| `MEDICAL_DATA` | Medical details | `medical_data`, `medical_condition`, `doctor` |
| `ABILITIES` | Learning support, dietary needs, activities | `abilities` |
| `ENROLMENT_DOCUMENTS` | The enrolment document groups | `enrolment_documents` |
| `QUESTIONNAIRE` | The school's application questionnaire | `questionnaire` |
| `PRESCHOOL_QUESTIONNAIRE` | The school's preschool questionnaire | `preschool_questionnaire` |

Block behaviours to know:

- **Identity fields are read-only** in custom forms: the student's first,
  middle and last name and date of birth always; a parent's first and last
  name once both are filled (a newly registered parent can still enter them).
- **`PRESCHOOL_QUESTIONNAIRE` only shows for preschool entry grades** (the
  school's preschool questionnaire grade setting). For other grades it is
  skipped, required fields included.
- **Conditional fields:** `home_language` only applies when
  `is_speak_other_language` is yes, so it can be mandatory without forcing an
  answer from English-only families. The same applies to the "if other, please
  specify" fields.
- A questionnaire block's questions are the school's global metafields (labels,
  options, HTML text). Editing those changes every form and the application
  that uses them. For wording specific to one form, add `HTML` or question
  elements next to the block instead.

## 5. Per-form field settings (`local_fields_settings`)

The school's global field settings (`GET metafields/` →
`field_settings[block][field]`) give each field an `enabled` and `mandatory`
flag **per context**: `enr` (enrolment), `eoi`, `enq`, `evt`, `cust` (custom
forms) and `admin`. Custom forms use `cust`.

A schema's `local_fields_settings` overrides those flags for this form only:

```json
{
  "parent": {
    "title":                   {"enabled": false, "mandatory": false},
    "relationship_to_student": {"enabled": true,  "mandatory": true},
    "business_phone":          {"enabled": true,  "mandatory": false}
  },
  "emergency_contact": {
    "residential_address": {"enabled": true, "mandatory": true}
  }
}
```

- A field you don't list keeps its global `cust` setting.
- Keys are **metafield names**, which are not always the serializer field name.
  For example, a parent's relationship is `relationship_to_student` here but
  `student_relationship` in the block's payload.
- **Unknown blocks or fields are dropped without an error.** Check every key
  against `GET metafields/` before writing (example below).
- Fields listed in a block's `_meta.permanent` (e.g. student `first_name`,
  `last_name`, `dob`, `entry_grade`, `entry_year`; parent `first_name`,
  `last_name`, `email`, `mobile_phone`) can't be disabled or made optional.
- Writing this key needs the *edit metafields settings* permission. Without
  it the key is ignored and the previous version's settings are kept, so read
  it back after saving.
- The overrides are merged at render and validation time: the preview's
  `schema.metafields` shows the effective result, flattened to booleans for the
  overridden fields.

```python
problems = client.forms.check_local_fields(local_fields)
# e.g. ['parent.nickname: no such field',
#       'profile.first_name: permanent field, must stay enabled and mandatory']
assert not problems, problems
```

## 6. Where answers end up

- Answers to the form's own questions are stored on the submission, in
  `payload`, keyed by **element name**.
- Answers inside profile-backed blocks are written to the student profile.
  The submission only keeps the values the form was pre-filled with.
- The submissions CSV export (`client.forms.export_submits()`) has one column
  per element **name**, not label. Give similar questions descriptive names:
  three rows of Monday–Friday boxes labelled "Monday" can be named
  `times_enrolled_monday`, `ece_hours_this_service_monday`, … so the export
  stays readable.
- `client.forms.answers()`, `consents()` and `iter_answers()` join the
  payload with the schema to label each answer.

## 7. Checking a form without a parent

Check all of these before anyone publishes:

1. **Read back** with `client.forms.definition(form_id)` and compare
   `schema["schema_data"]` and `schema["local_fields_settings"]` with what you
   sent. The only expected difference is HTML sanitising (section 9).
2. **Effective field settings:** `client.forms.preview(slug)` →
   `["schema"]["metafields"][block][field]` should show your overrides.
3. **Which fields each block includes:** the same response's
   `["initial_payload"][element_name]` lists the fields each block will send.
4. **Validation, without saving:** `client.forms.validate_step(form_id, step,
   answers)` checks one step's answers. A valid step returns normally. A
   wrong-type value for one of your fields is rejected **by field name**,
   which proves the field is part of the form, and a missing required answer
   is caught:

```python
from enrolhq.exceptions import ValidationError

client.forms.validate_step(FORM_ID, 5, step_answers)          # valid: no error

try:
    client.forms.validate_step(FORM_ID, 5, {**step_answers, "times_enrolled_monday": ["x"]})
except ValidationError as exc:
    print(exc.detail)    # {'times_enrolled_monday': ['Not a valid string.']}
```

A real parent submission runs the same validation, then stores the validated
answers in `payload`.

5. **Look at it:** open `/preview/form/{slug}/` and the dashboard builder
   while signed in to the dashboard, and check the layout in both (section 8).

## 8. Layout and styling

- Each step renders as a CSS grid with Bootstrap's `gap-5` (3rem) between
  elements. An element's `css_class` and `css_style` go on its wrapper `<div>`.
- **`css_style` and `css_class` are applied in the dashboard form builder
  too.** A width cap is fine in both places (`"css_style": "max-width: 14rem;"`
  keeps a short-answer box short and still shrinks on a phone). A negative
  margin is not: in the builder it slides each component over the one above,
  hiding labels and misaligning the selection box.
- For spacing that should only affect parents, give elements a class and put
  the rule in **Custom Scripts** (*Settings > Custom Scripts*,
  `extra-frontend-code/`). Its HTML is injected into the `<head>` of
  parent-facing pages only, never the dashboard or print views:

```css
/* Stack a run of short boxes closely (cancels most of the 3rem grid gap). */
.compact-first { margin-top: -1.75rem; }   /* first box under its heading */
.compact       { margin-top: -2.25rem; }   /* the rest: 0.75rem apart */
```

- Custom Scripts is one block of HTML for the whole parent site, usually
  holding the school's branding CSS and tracking scripts. **Append to it,
  never replace it**. `append_custom_scripts` adds a snippet after what is
  there, once: it writes nothing if the marker is already present. Snapshot
  `custom_scripts()` first:

```python
before = client.cms_settings.custom_scripts()          # keep a copy
MARKER = "/* Example form: compact boxes */"
client.cms_settings.append_custom_scripts(
    f"<style>\n{MARKER}\n"
    ".compact-first { margin-top: -1.75rem; }\n"
    ".compact { margin-top: -2.25rem; }\n</style>",
    marker=MARKER,
)
```

  The server strips trailing newlines. Add the CSS **before** publishing
  the form that uses the class: until an element carries the class, the rule
  does nothing.

## 9. Gotchas

- **HTML is sanitised on save** (`nh3`): ordinary tags (`div`, `p`, `h1`–`h6`,
  `ul`/`ol`/`li`, `strong`, `em`, `a`, `br`, tables, `img`, `iframe`) survive.
  `style`, `class`, `id` and `type` attributes survive on any tag. Links get
  `rel="noopener noreferrer"` added, so put it in your source HTML if you
  compare readbacks. Text written in the dashboard builder is `<div>`-based,
  with `<div><br></div>` for blank lines.
- **Emergency contacts:** when a profile has fewer contacts than the school
  requires, the server pads the list with blank contacts built from the
  *global* field settings, not the form's overrides. Check a form that adds
  emergency-contact fields against such a profile in the preview.
- **Dates:** there is no date element. Use `INPUT` with "DD/MM/YYYY" in the
  description, or the `ENTRY_DETAILS` block if the date should land on the
  profile (`commencement_date`, `leaving_date`). That writes the parent's
  answer over the profile value, and the server validates it against the
  entry year.
- **`client.forms.get(slug)`** returns the parent-facing *published* form; use
  `forms/staff/{id}/` for the draft and the settings.
- **Audience:** a form shows to a parent only when the profile matches all of
  its filters (campus, application status, entry grade and year, …).
  Compare with the school's similar forms before choosing statuses.

## 10. Workflow: building a form from a school's document

1. **Read the source** (Word or PDF). List every question, statement,
   signature line and office-use box.
2. **Survey the instance:** `client.forms.list()`, and `GET` a few of the
   school's forms that serve the same families. Copy their conventions (step
   titles, HTML style, the signature element's settings, the
   `PARENT_2_NOT_APPLICABLE_HTML` wording), audience statuses and campus. Note
   overlaps, e.g. a separate media consent form already asking the photo
   questions.
3. **Read the field settings** (`client.metafields.get()`), including any
   existing questionnaire questions that already cover part of the document.
4. **Map** each part of the document to a profile-backed block (with field
   overrides) when the data belongs on the profile, otherwise to question
   elements. Leave out office-use sections, and note every judgment call
   (reworded paper-only instructions, questions merged or left out).
5. **Write a script** that builds `schema_data` and `local_fields_settings` in
   code, validates the override keys, snapshots the current form, and runs as
   a dry run unless told to apply. Keep the script: it is how the form gets
   changed after review.
6. **Save as a draft** (`is_published: false`) and run every check in
   section 7.
7. **Hand over for review** in the preview, with the list of judgment calls.
8. **Publish and activate**: a person's decision, because it changes what
   parents see. Before overwriting a form that people can edit in the
   dashboard, compare it with your last save (section 3).
