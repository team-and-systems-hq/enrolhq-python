"""School settings resource (``school/``) and commencement dates."""

from typing import Any, Dict, List, Optional

from .base import BaseResource, Replace


class SchoolResource(BaseResource):
    """Read and write the school-wide settings object.

    ``school/`` is a single object (no list or detail routes) holding the
    school name, region (timezone and country, under the nested ``school``
    key), business number, prospectus link, and the lookup lists edited on
    *Settings > School*: ``attendance_types``, ``parents_relationships``,
    ``custom_categories``, ``lead_references``, ``siblings_statuses``,
    ``profile_priorities``, ``medical_condition_options``,
    ``residency_status_configs`` and ``gender_options``.

    Writes are a full PUT validated in full — every key is required. Nested
    lists are replaced wholesale: rows with a known ``id`` are updated, rows
    without one are created, and existing rows you leave out are deleted.
    Use :meth:`update_fields` to change a few keys safely.

    Requires the ``change_schoolsettings`` permission (school Admin or
    superuser).
    """

    def get(self) -> Dict[str, Any]:
        """Get the school settings object."""
        return self._get("school/")

    def update(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Replace the school settings object (full PUT).

        *data* must be a complete object — start from :meth:`get`.
        """
        return self._put("school/", json=data)

    def update_fields(self, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Change some settings: GET, deep-merge *changes*, PUT the result.

        Nested dicts merge key by key; lists replace the current list (so
        include existing rows, with their ``id``, to keep them). Wrap a value
        in :class:`~enrolhq.Replace` to replace a dict wholesale.

        Example::

            client.school.update_fields({
                "name": "Example Grammar",
                "business_number_abbreviation": "NZBN",
            })
        """
        return self._read_modify_write("school/", changes)

    def set_region(
        self,
        *,
        tzname: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Set the school's timezone and/or country.

        Args:
            tzname: IANA timezone, e.g. ``"Pacific/Auckland"`` (choices from
                ``dictionaries/timezones/``). Event session times and all
                request handling use this timezone.
            country: ISO alpha-2 code, e.g. ``"NZ"``. Also filters the
                ``dictionaries/school-options/`` list of current schools.
        """
        region: Dict[str, Any] = {}
        if tzname is not None:
            region["tzname"] = tzname
        if country is not None:
            region["country"] = Replace({"alpha_2_code": country.upper()})
        if not region:
            raise ValueError("Pass tzname and/or country")
        return self.update_fields({"school": region})

    # ── Commencement dates ──────────────────────────────────

    def commencement_dates(self) -> List[Dict[str, Any]]:
        """List commencement dates (``{id, year, grade, commencement_date}``)."""
        return list(self._list("school/commencement_dates/", page_size=1000))

    def create_commencement_date(
        self, year: int, commencement_date: str, grade: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a commencement date for an entry year (optionally per grade).

        Args:
            year: Entry year, e.g. ``2027``.
            commencement_date: ``"YYYY-MM-DD"``.
            grade: Entry grade, or ``None`` for all grades.
        """
        return self._post(
            "school/commencement_dates/",
            json={"year": year, "grade": grade, "commencement_date": commencement_date},
        )

    def update_commencement_date(
        self, commencement_date_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a commencement date (full PUT)."""
        return self._put(f"school/commencement_dates/{commencement_date_id}/", json=data)

    def delete_commencement_date(self, commencement_date_id: str) -> None:
        """Delete a commencement date."""
        self._delete(f"school/commencement_dates/{commencement_date_id}/")
