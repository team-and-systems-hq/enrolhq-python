"""CMS settings resource."""

from typing import Any, Dict

from .base import BaseResource


class CmsSettingsResource(BaseResource):
    """Access the school's CMS / form configuration settings.

    The ``cms-settings/`` endpoint returns a single configuration object
    covering enquiry, event-booking, GPA/enrolment form copy and labels,
    terms & conditions, parent-dashboard visibility flags, and the school
    policy agreement items shown to applicants.
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
