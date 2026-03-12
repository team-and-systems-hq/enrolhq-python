"""Reference data resource (campuses, countries, languages, etc.)."""

from typing import Any, Dict, List

from .base import BaseResource


class ReferenceDataResource(BaseResource):
    """Access reference/lookup data.

    All methods return a plain list of records (auto-fetching all pages).
    """

    def _get_all(self, endpoint: str, page_size: int = 1000) -> List[Dict[str, Any]]:
        """Fetch all results from a paginated endpoint as a flat list."""
        return list(self._list(endpoint, page_size=page_size))

    def campuses(self) -> List[Dict[str, Any]]:
        """List all school campuses."""
        return self._get_all("school-campuses/")

    def attendance_types(self) -> List[Dict[str, Any]]:
        """List attendance types."""
        return self._get_all("attendance-types/")

    def countries(self) -> List[Dict[str, Any]]:
        """List all countries."""
        return self._get_all("dictionaries/countries/")

    def languages(self) -> List[Dict[str, Any]]:
        """List all languages."""
        return self._get_all("dictionaries/languages/")

    def nationalities(self) -> List[Dict[str, Any]]:
        """List all nationalities."""
        return self._get_all("dictionaries/nationalities/")

    def school_options(self) -> List[Dict[str, Any]]:
        """List school options."""
        return self._get_all("dictionaries/school-options/")

    def social_units(self) -> List[Dict[str, Any]]:
        """List social units."""
        return self._get_all("dictionaries/social-units/")

    def suburbs(self, **params: Any) -> List[Dict[str, Any]]:
        """Search suburbs."""
        return list(self._list("dictionaries/suburbs/", params=params))

    def timezones(self) -> List[Dict[str, Any]]:
        """List all timezones."""
        return self._get_all("dictionaries/timezones/")

    def medical_condition_options(self) -> List[Dict[str, Any]]:
        """List medical condition options."""
        return self._get_all("medical-condition-options/")

    def parent_relationships(self) -> List[Dict[str, Any]]:
        """List parent relationship types."""
        return self._get_all("parents-relationships/")

    def profile_categories(self) -> List[Dict[str, Any]]:
        """List profile categories."""
        return self._get_all("profile-categories/")

    def profile_category_options(self) -> List[Dict[str, Any]]:
        """List profile category options."""
        return self._get_all("profile-category-options/")
