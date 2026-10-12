"""Look-and-feel resource: brand colours, form header themes and fonts."""

import re
from typing import Any, Dict, List, Optional

from ..files import Source, file_data_uri
from .base import BaseResource

#: Font slots. ``light``/``regular``/``medium``/``bold`` are the four
#: weights (300/400/500/700) of the "School Font" used for all body text;
#: ``brand`` is the single-weight "School Brand Font" used for the large page
#: titles on form headers and the parent dashboard.
FONT_SLOTS = ("light", "regular", "medium", "bold", "brand")

#: Form codes in ``form_header_themes``: lead (register interest), enq
#: (enquiry), evt (event booking), eoi (expression of interest), enr
#: (enrolment), cust (custom forms). Each is ``"dark"`` or ``"light"``.
FORM_CODES = ("lead", "enq", "evt", "eoi", "enr", "cust")

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class LookAndFeelResource(BaseResource):
    """Read and write the school's look and feel (*Settings > Look and Feel*).

    ``cms-look-and-feel/`` holds ``palette`` (``primary_color`` and
    ``secondary_color``, ``#RRGGBB`` — the only colours EnrolHQ themes; both
    are used as button backgrounds with white text), ``form_header_themes``
    and the five ``fonts`` slots (FontFile ids). ``font_library`` (read-only)
    lists every uploaded font.

    Fonts are uploaded with :meth:`upload_font` (``cms-fonts/``, POST only —
    there is no list, update or delete) and then assigned to slots.

    Requires ``change_cmssettings`` (school Admin or superuser).
    """

    def get(self) -> Dict[str, Any]:
        """Get palette, header themes, font slots and the font library."""
        return self._get("cms-look-and-feel/")

    def update(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Replace the look-and-feel object (full PUT).

        ``palette``, ``form_header_themes`` (all six form codes) and
        ``fonts`` are all required.
        """
        return self._put("cms-look-and-feel/", json=data)

    def _write(self, **changes: Any) -> Optional[Dict[str, Any]]:
        current = self.get()
        body = {
            "palette": current["palette"],
            "form_header_themes": current["form_header_themes"],
            "fonts": current["fonts"],
        }
        for key, value in changes.items():
            body[key] = {**body[key], **value}
        return self.update(body)

    def set_palette(
        self,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Set the brand colours (``#RRGGBB``), keeping everything else."""
        palette = {}
        for key, value in (
            ("primary_color", primary_color),
            ("secondary_color", secondary_color),
        ):
            if value is None:
                continue
            if not _HEX.match(value):
                raise ValueError(f"{key} must be #RRGGBB, got {value!r}")
            palette[key] = value
        if not palette:
            raise ValueError("Pass primary_color and/or secondary_color")
        return self._write(palette=palette)

    def set_form_header_themes(self, **themes: str) -> Optional[Dict[str, Any]]:
        """Set header themes per form code (``"dark"`` or ``"light"``)::

            client.look_and_feel.set_form_header_themes(enq="dark", eoi="dark")
        """
        if not themes:
            raise ValueError(f"Pass a theme for at least one of {FORM_CODES}")
        for code, theme in themes.items():
            if code not in FORM_CODES:
                raise ValueError(f"Unknown form code {code!r}; expected one of {FORM_CODES}")
            if theme not in ("dark", "light"):
                raise ValueError(f"Theme for {code!r} must be 'dark' or 'light'")
        return self._write(form_header_themes=themes)

    def set_fonts(self, **slots: Optional[str]) -> Optional[Dict[str, Any]]:
        """Assign uploaded fonts (FontFile ids, or ``None``) to slots::

            client.look_and_feel.set_fonts(regular=font["id"], brand=brand["id"])
        """
        if not slots:
            raise ValueError(f"Pass a font for at least one of {FONT_SLOTS}")
        unknown = set(slots) - set(FONT_SLOTS)
        if unknown:
            raise ValueError(f"Unknown font slot(s): {', '.join(sorted(unknown))}")
        return self._write(fonts=slots)

    def font_library(self) -> List[Dict[str, Any]]:
        """List uploaded fonts as ``{id, name}`` records."""
        return list(self.get().get("font_library", []))

    def upload_font(
        self, name: str, woff: Source, woff2: Source
    ) -> Dict[str, Any]:
        """Upload a font (both WOFF and WOFF2 are required).

        Args:
            name: Library name (max 50 chars), e.g. ``"Roboto Regular"``.
            woff: Path to (or bytes of) the ``.woff`` file.
            woff2: Path to (or bytes of) the ``.woff2`` file.

        Returns:
            The created FontFile, including its ``id`` for :meth:`set_fonts`.
        """
        slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-") or "font"
        result = self._post(
            "cms-fonts/",
            json={
                "name": name,
                "woff": file_data_uri(woff, filename=f"{slug}.woff"),
                "woff2": file_data_uri(woff2, filename=f"{slug}.woff2"),
            },
        )
        return result or {}

    def find_or_upload_font(
        self, name: str, woff: Source, woff2: Source
    ) -> Dict[str, Any]:
        """Return the library font called *name*, uploading it if missing.

        Makes repeated runs idempotent (there is no font delete endpoint, so
        re-uploading would pile up duplicates in the library).
        """
        for font in self.font_library():
            if font.get("name") == name:
                return font
        return self.upload_font(name, woff, woff2)
