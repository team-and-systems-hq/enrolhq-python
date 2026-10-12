"""Campuses resource (contact details, address and branding images)."""

from typing import Any, Dict, List, Optional

from ..files import Source, image_data_uri
from ..pagination import PaginatedIterator
from .base import BaseResource, Replace, deep_merge

#: Branding image slots on a campus (``cms_images``), with the size the
#: EnrolHQ settings screen recommends.
IMAGE_SLOTS: Dict[str, str] = {
    "favicon": "Favicon (200x200, PNG)",
    "logo_light": "Logo for horizontal coloured strip (600x400, light-on-dark)",
    "logo_dark": "Logo (600x400, dark-on-light) - login, offers, print headers",
    "logo_dark_stacked": "Stacked logo (600x600) - parent dashboard header",
    "default_header_image": "Default header background (1920x600)",
    "img_enrolment_header": "Parent dashboard header background (1920x288)",
    "img_enquiry_header": "Enquiry header background (1920x384)",
    "img_event_booking_header": "Event header background (1920x384)",
    "img_gpa_header": "EOI form header background (1920x384)",
    "bg_event": "Event page background (1920x1080)",
    "bg_enquiry": "Enquiry page background (1920x1080)",
    "bg_trade_show": "Register-interest page background (1920x1080)",
    "img_enrolment_sidebar": "Enrolment form sidebar (300x200)",
    "img_gpa_sidebar": "EOI form sidebar (300x200)",
    "img_custom_form_sidebar": "Custom form sidebar (300x200)",
    "logo_email_top": "Email top logo (550x125)",
    "logo_email_bottom": "Email bottom logo",
    "logo_printed_email_top": "Printed email top logo",
    "logo_printed_email_bottom": "Printed email bottom logo",
    "img_attendee_label": "Event attendee label image",
}


class CampusesResource(BaseResource):
    """Create and update campuses, including their branding images.

    A campus carries the school's public contact details (``telephone``
    (max 15 chars), ``website``, ``email``), outbound email settings
    (``from_email``, ``bcc_email``, ``reply_to_staff``), registrar and
    principal names, a ``residential_address`` and the ``cms_images``
    branding slots listed in :data:`IMAGE_SLOTS`.

    Writes are a full PUT. Images are base64 data URIs (see
    :mod:`enrolhq.files`); in ``cms_images`` include only the slots you are
    changing — omitted slots keep their image, ``""``/``None`` clears one.
    :meth:`update_fields` and :meth:`set_images` handle this for you.

    Reads are public; ``create`` needs ``add_campus`` and updates need
    ``change_campus`` (school Admin or superuser). There is no delete.
    """

    def list(self, *, page_size: int = 100) -> PaginatedIterator:
        """Auto-paginate through all campuses."""
        return self._list("school-campuses/", page_size=page_size)

    def get(self, campus_id: str) -> Dict[str, Any]:
        """Get a single campus."""
        return self._get(f"school-campuses/{campus_id}/")

    def default(self) -> Dict[str, Any]:
        """Return the default campus (``is_default``), else the first one."""
        campuses: List[Dict[str, Any]] = list(self.list())
        if not campuses:
            raise LookupError("The school has no campuses")
        return next((c for c in campuses if c.get("is_default")), campuses[0])

    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a campus.

        Required keys: ``name``, ``slug`` (both unique per school),
        ``is_default`` (forced false on create), ``telephone``, ``website``,
        ``email``, ``from_email``, ``residential_address`` (``state`` is
        required; ``country`` as ``{"alpha_2_code": "NZ"}``) and
        ``cms_images`` — pass ``{}`` to copy the default campus's images.
        """
        return self._post("school-campuses/", json=data)

    def update(self, campus_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Replace a campus (full PUT). Prefer :meth:`update_fields`."""
        return self._put(f"school-campuses/{campus_id}/", json=data)

    def update_fields(
        self, campus_id: str, changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Change some campus fields: GET, deep-merge *changes*, PUT.

        ``cms_images`` in the PUT body is reduced to the slots present in
        ``changes["cms_images"]``, because the GET returns image URLs that
        the server rejects on write.

        A ``residential_address.country`` in *changes* replaces the current
        country rather than merging into it (the server looks a country up by
        ``id`` first, so a merged ``{"alpha_2_code": "NZ"}`` would keep the
        old ``id``)::

            client.campuses.update_fields(
                campus["id"],
                {"residential_address": {"country": {"alpha_2_code": "NZ"}}},
            )
        """
        current = self.get(campus_id)
        address = changes.get("residential_address")
        if isinstance(address, dict) and isinstance(address.get("country"), dict):
            changes = {
                **changes,
                "residential_address": {**address, "country": Replace(address["country"])},
            }
        body = deep_merge(current, changes)
        body["cms_images"] = dict(changes.get("cms_images") or {})
        return self.update(campus_id, body)

    def set_images(
        self, campus_id: str, **images: Optional[Source]
    ) -> Optional[Dict[str, Any]]:
        """Upload branding images to a campus.

        Each keyword is a slot from :data:`IMAGE_SLOTS`; each value a file
        path or raw bytes (PNG/JPEG/WebP/BMP/TIFF), or ``None`` to clear it::

            client.campuses.set_images(
                campus["id"],
                logo_dark="assets/logo-dark.png",
                favicon="assets/favicon-512.png",
                default_header_image="assets/campus.jpg",
            )
        """
        if not images:
            raise ValueError("Pass at least one image slot")
        unknown = set(images) - set(IMAGE_SLOTS)
        if unknown:
            raise ValueError(f"Unknown image slot(s): {', '.join(sorted(unknown))}")
        encoded = {
            slot: (None if source is None else image_data_uri(source))
            for slot, source in images.items()
        }
        return self.update_fields(campus_id, {"cms_images": encoded})
