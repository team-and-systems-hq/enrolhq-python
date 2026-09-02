"""Copy student profiles between two EnrolHQ instances."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

#: Fields never copied: documents (copy those with ``client.documents``) and
#: server-owned blobs that mean nothing on another instance.
SKIP_FIELDS = frozenset({
    "authorised_staff_only_documents",
    "avatar",
    "custody_documents",
    "custom_form_documents",
    "enrolment_documents",
    "parent_dashboard_downloads",
    "printed_documents",
    "staff_only_documents",
    "updated_at",
})

#: Fields holding IDs from a school-scoped lookup table, mapped to the
#: :class:`~enrolhq.resources.ReferenceDataResource` method that lists it and
#: the key its records are named by. Values are translated by that name,
#: because the same "Junior Campus" has a different ID on every instance.
#:
#: ``"siblings[].status"`` addresses a field nested inside a list of objects.
#: Global dictionaries (countries, languages, schools) share IDs across
#: instances and are left alone.
#:
#: An alternative entry carries its own campus and attendance type, which are
#: school-scoped for the same reason the top-level ones are. Unlike the
#: top-level ``campus`` both are optional, so an unmatched value is dropped
#: rather than falling back to the target's default.
LOOKUP_FIELDS = {
    "alternative_entry_details[].attendance_type": ("attendance_types", "name"),
    "alternative_entry_details[].campus": ("campuses", "name"),
    "attendance_type": ("attendance_types", "name"),
    "campus": ("campuses", "name"),
    "custom_categories_options": ("profile_category_options", "name"),
    "interview_categories": ("interview_categories", "name"),
    "nationalities": ("nationalities", "name"),
    "parents_relationships": ("parent_relationships", "name"),
    "siblings[].status": ("sibling_statuses", "label"),
}


@dataclass
class CopyResult:
    """What :meth:`ProfileCopier.copy` did."""

    #: The application's ID on the target instance.
    application_id: str
    #: True if the student was created, False if an existing one was updated.
    created: bool
    #: Names of the fields that were copied.
    copied: List[str] = field(default_factory=list)
    #: Source fields the target does not accept, so were not copied.
    dropped: List[str] = field(default_factory=list)
    #: Lookup values with no equivalent on the target, as ``"field=name"``.
    skipped_lookups: List[str] = field(default_factory=list)


class ProfileCopier:
    """Copy a student profile from one EnrolHQ instance to another.

    Two instances rarely agree on their configuration, so the payload is
    filtered through the target's own field schema (``OPTIONS``) and lookup
    UUIDs are translated by name. Anything the target does not accept is
    reported on the :class:`CopyResult` rather than raising.

    Documents are not copied.

    Usage::

        copier = ProfileCopier(source_client, target_client)
        result = copier.copy("application-uuid")
        print(result.application_id, result.created)
    """

    def __init__(self, source: Any, target: Any) -> None:
        self.source = source
        self.target = target
        self._rows: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}

    # ── Copy ────────────────────────────────────────────────────

    def copy(self, application_id: str) -> CopyResult:
        """Copy the source application to the target instance.

        Looks for the student on the target by name and date of birth: an
        existing profile is updated in place, otherwise one is created first.
        Trashed profiles on the target are ignored, so a binned record is
        never revived.

        Args:
            application_id: The application's UUID on the *source* instance.

        Returns:
            A :class:`CopyResult` describing what was copied.
        """
        student = self.source.applications.get(application_id)
        result = CopyResult(application_id="", created=False)

        payload = self.build_payload(student, result)

        existing = self.target.applications.find(
            student["first_name"], student["last_name"], student["dob"]
        )
        if existing:
            result.application_id = existing["id"]
        else:
            result.application_id = self._create(student, payload)["id"]
            result.created = True

        # Same get -> modify -> PUT pattern as a single-instance update: merge
        # onto the target's own record so its row IDs and any field this copy
        # does not set survive.
        current = self.target.applications.get(result.application_id)
        self.target.applications.update(
            result.application_id, _merge(current, payload)
        )
        return result

    def build_payload(
        self, student: Dict[str, Any], result: Optional[CopyResult] = None
    ) -> Dict[str, Any]:
        """Return *student* reduced to what the target instance accepts.

        Drops fields the target does not have or marks read-only (recursively,
        so nested server-owned keys such as ``user_parent.id`` go too), then
        translates lookup UUIDs to their target equivalents.
        """
        schema = self.target.applications.field_options()

        payload = {
            name: _writable_only(value, schema[name])
            for name, value in student.items()
            if name in schema
            and not schema[name].get("read_only")
            and name not in SKIP_FIELDS
        }

        if result is not None:
            result.copied = sorted(payload)
            result.dropped = sorted(set(student) - set(payload) - SKIP_FIELDS)

        for path in LOOKUP_FIELDS:
            self._remap_path(payload, path, result)
        return payload

    # ── Internals ───────────────────────────────────────────────

    def _create(
        self, student: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create the student on the target with the minimum viable fields."""
        parent = student.get("user_parent") or {}
        return self.target.applications.create({
            "application_status": student["application_status"],
            "first_name": student["first_name"],
            "last_name": student["last_name"],
            "dob": student["dob"],
            "gender": student["gender"],
            "entry_grade": student["entry_grade"],
            "entry_year": student["entry_year"],
            "campus": payload.get("campus"),
            "user_parent": {
                "first_name": parent.get("first_name", ""),
                "last_name": parent.get("last_name", ""),
                "email": parent.get("email", ""),
                "mobile_phone": parent.get("mobile_phone", ""),
            },
        })

    def _lookup_rows(self, client: Any, path: str) -> List[Dict[str, Any]]:
        """Fetch (and cache) a lookup table from one instance."""
        cache = self._rows.setdefault(id(client), {})
        if path not in cache:
            method, _ = LOOKUP_FIELDS[path]
            cache[path] = getattr(client.reference_data, method)()
        return cache[path]

    def _remap_path(
        self, payload: Dict[str, Any], path: str, result: Optional[CopyResult]
    ) -> None:
        """Translate the lookup value(s) at *path*, in place.

        *path* is either a field name or ``"field[].child"`` for a field
        nested inside a list of objects, such as a sibling's status.
        """
        if "[]." in path:
            parent, child = path.split("[].", 1)
            for item in payload.get(parent) or []:
                if isinstance(item, dict) and item.get(child):
                    item[child] = self._remap(path, item[child], result)
        elif path in payload:
            payload[path] = self._remap(path, payload[path], result)

    def _remap(
        self, path: str, value: Any, result: Optional[CopyResult]
    ) -> Any:
        """Translate a lookup value from source IDs to target IDs by name.

        The source's shape is preserved: some fields are written back as bare
        IDs, others (nationalities) as the expanded ``{id, name}`` object.
        """
        _, key = LOOKUP_FIELDS[path]
        source_rows = self._lookup_rows(self.source, path)
        target_rows = self._lookup_rows(self.target, path)

        if isinstance(value, list):
            mapped = [
                (v, _match(target_rows, _name_of(source_rows, v, key), key, path, result))
                for v in value
            ]
            return [_shaped(row, original) for original, row in mapped if row]

        row = _match(target_rows, _name_of(source_rows, value, key), key, path, result)
        if row:
            return _shaped(row, value)
        if path == "campus" and target_rows:
            # A campus is required, so fall back to the target's default.
            default = next(
                (c for c in target_rows if c.get("is_default")), target_rows[0]
            )
            return default["id"]
        return None


def _shaped(row: Dict[str, Any], original: Any) -> Any:
    """Return the target row in whatever shape the source used."""
    return dict(row) if isinstance(original, dict) else row["id"]


def _name_of(rows: List[Dict[str, Any]], value: Any, key: str) -> Optional[str]:
    """Resolve a lookup value (an ID, or an expanded object) to its name."""
    if isinstance(value, dict):
        return value.get(key)
    for row in rows:
        if row["id"] == value:
            return row[key]
    return None


def _match(
    rows: List[Dict[str, Any]],
    name: Optional[str],
    key: str,
    path: str,
    result: Optional[CopyResult],
) -> Optional[Dict[str, Any]]:
    """Find the row whose name matches *name*, ignoring case."""
    if not name:
        return None
    for row in rows:
        if row[key].strip().lower() == name.strip().lower():
            return row
    if result is not None:
        result.skipped_lookups.append(f"{path}={name}")
    return None


def _writable_only(value: Any, schema: Dict[str, Any]) -> Any:
    """Strip everything the target's schema marks read-only, recursively."""
    child = schema.get("child") or {}
    children = schema.get("children") or child.get("children")
    if not children:
        return value
    if isinstance(value, list):
        return [_writable_only(item, child or schema) for item in value]
    if not isinstance(value, dict):
        return value
    return {
        key: _writable_only(item, children[key])
        for key, item in value.items()
        if key in children and not children[key].get("read_only")
    }


def _merge(target_value: Any, source_value: Any) -> Any:
    """Overlay source values onto the target's record, merging nested objects."""
    if isinstance(target_value, dict) and isinstance(source_value, dict):
        merged = dict(target_value)
        for key, value in source_value.items():
            merged[key] = _merge(target_value.get(key), value)
        return merged
    return source_value