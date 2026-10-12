"""CMS settings resource."""

from typing import Any, Dict, Optional

from .base import BaseResource


class CmsSettingsResource(BaseResource):
    """Access the school's CMS / form configuration settings.

    The ``cms-settings/`` endpoint returns a single configuration object
    covering enquiry, event-booking, GPA/enrolment form copy and labels,
    terms & conditions, parent-dashboard visibility flags, and the school
    policy agreement items shown to applicants.

    It is writable with a full PUT (``change_cmssettings``; school Admin or
    superuser). The nested objects (``event_booking``, ``enquiry``,
    ``gpa_form_tc``, ``enrolment_form_settings``, ...) are updated in place
    and are all required, so start from :meth:`get` or use
    :meth:`update_fields`.

    ``school_policy_agreement_items`` is replaced wholesale. Each item needs
    exactly one of ``file`` (a base64 document — see
    :func:`enrolhq.files.file_data_uri`) or ``url``. Existing items sent back
    with their ``id`` and without ``file`` keep their stored file (the GET
    returns it as ``file_src``).
    """

    def get(self, **params: Any) -> Dict[str, Any]:
        """Get the CMS settings configuration object.

        Returns:
            The full settings dict (e.g. ``event_booking``, ``enquiry``,
            ``enrolment_form_settings``, ``parent_label``,
            ``school_policy_agreement_items``).
        """
        resp = self._http.get(self._url("cms-settings/"), params=params)
        return resp.json()

    def update(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Replace the CMS settings object (full PUT). Start from :meth:`get`."""
        return self._put("cms-settings/", json=data)

    def update_fields(self, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Change some settings: GET, deep-merge *changes*, PUT the result.

        Nested objects merge key by key, so this only touches what you pass::

            client.cms_settings.update_fields({
                "school_level_label": "Year",
                "enquiry": {"page_header": "Enquire about Example Grammar"},
                "event_booking": {"make_booking_button_label": "Book a tour"},
            })
        """
        return self._read_modify_write("cms-settings/", changes)
