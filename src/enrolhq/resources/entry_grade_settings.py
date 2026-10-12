"""Entry grade settings resource (year levels and entry years)."""

from typing import Any, Callable, Dict, Optional

from .base import BaseResource


class EntryGradeSettingsResource(BaseResource):
    """Read and write which year levels and entry years families can choose.

    ``entry-grade-settings/`` returns ``is_entry_year_disabled``,
    ``first_grade_age`` (4-7; predicted entry year is
    ``dob.year + first_grade_age + grade - 1``),
    ``commencement_date_edge_status`` and ``entry_grade_settings`` — exactly
    one row per grade from -5 (Reserved) to 13. Each row has ``entry_grade``,
    a ``label`` override (blank uses ``default_label``, e.g. "Year 9"),
    ``availability_for_current_school`` (``APPLICATION_ALLOWED``,
    ``APPLICATION_NOT_ALLOWED`` or ``HIDDEN``) and
    ``campus_entry_years_settings`` — per campus: ``is_available``,
    ``gender`` and the entry years offered on each form (``eoi_``, ``enr_``,
    ``enq_``, ``evt_entry_years``).

    Grade 13 is hidden and unavailable by default; enable it for schools that
    run to Year 13 (e.g. New Zealand). The PUT must contain all 19 rows (rows
    cannot be added or removed), so modify the GET result — see
    :meth:`modify_grades`. Requires ``change_entrygradesettings``.
    """

    def get(self) -> Dict[str, Any]:
        """Get the entry grade settings object."""
        return self._get("entry-grade-settings/")

    def update(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Replace the entry grade settings (full PUT of all 19 grade rows)."""
        return self._put("entry-grade-settings/", json=data)

    def modify_grades(
        self,
        fn: Callable[[Dict[str, Any]], None],
        **top_level: Any,
    ) -> Optional[Dict[str, Any]]:
        """GET, call ``fn(row)`` on every grade row, then PUT.

        Keyword arguments set top-level keys (e.g. ``first_grade_age=5``)::

            years = list(range(2027, 2033))

            def senior_school_only(row):
                senior = 9 <= row["entry_grade"] <= 13
                for campus in row["campus_entry_years_settings"]:
                    campus["is_available"] = senior
                    for form in ("eoi", "enr", "enq", "evt"):
                        campus[f"{form}_entry_years"] = years if senior else []

            client.entry_grade_settings.modify_grades(senior_school_only)
        """
        data = self.get()
        for row in data["entry_grade_settings"]:
            fn(row)
        data.update(top_level)
        return self.update(data)
