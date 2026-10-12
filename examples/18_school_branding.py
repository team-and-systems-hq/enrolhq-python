"""Brand a school: name, campus details, logos and header images, colours, fonts.

WARNING: with --apply this overwrites the school's live branding.

    python examples/18_school_branding.py            # show current branding
    python examples/18_school_branding.py --apply    # write the values below

Images are sent as base64 data URIs (PNG/JPEG/WebP; no SVG/ICO/GIF). Fonts
need both a .woff and a .woff2 file.
"""

import sys

from enrolhq import EnrolHQClient
from enrolhq.resources.campuses import IMAGE_SLOTS

# ── What to set (edit for your school) ──────────────────────
SCHOOL_NAME = "Example Grammar"
CAMPUS = {
    "telephone": "+61290000000",  # max 15 characters
    "website": "https://www.example.edu.au",
    "email": "enrolments@example.edu.au",
    "from_email": "enrolments@example.edu.au",
    "registrar_title": "Registrar",
}
IMAGES = {
    # slot: local file — see IMAGE_SLOTS for every slot and its size
    "logo_dark": "assets/logo-dark.png",
    "favicon": "assets/favicon-512.png",
    "default_header_image": "assets/campus-1920x600.jpg",
}
PALETTE = {"primary_color": "#0B2341", "secondary_color": "#8B7347"}
BODY_FONT = ("Roboto Regular", "assets/Roboto-Regular.woff", "assets/Roboto-Regular.woff2")
BRAND_FONT = ("Playfair Display", "assets/Playfair.woff", "assets/Playfair.woff2")

client = EnrolHQClient()  # reads from .env
apply = "--apply" in sys.argv

# ── Current state ───────────────────────────────────────────
school = client.school.get()
campus = client.campuses.default()
look = client.look_and_feel.get()

print(f"School:   {school['name']!r} ({school['school']['tzname']})")
print(f"Campus:   {campus['name']} | {campus['telephone']} | {campus['email']}")
print(f"Palette:  {look['palette']}")
print(f"Fonts:    {[f['name'] for f in client.look_and_feel.font_library()]}")
print("Images:")
for slot, description in IMAGE_SLOTS.items():
    status = "set" if campus["cms_images"].get(slot) else "-"
    print(f"  {slot:28} {status:4} {description}")

if not apply:
    print("\nDry run - pass --apply to write the values at the top of this file.")
    sys.exit()

# ── Write ───────────────────────────────────────────────────
# Settings endpoints only take a full PUT; update_fields() does GET -> merge -> PUT.
client.school.update_fields({"name": SCHOOL_NAME})
client.campuses.update_fields(campus["id"], CAMPUS)

# Only the slots you pass are sent; other images are left as they are.
client.campuses.set_images(campus["id"], **IMAGES)

# Both palette colours are button backgrounds with white text - keep them dark
# enough for contrast (WCAG AA is 4.5:1).
client.look_and_feel.set_palette(**PALETTE)

# There is no font delete endpoint, so reuse a library font with the same name.
body = client.look_and_feel.find_or_upload_font(*BODY_FONT)
brand = client.look_and_feel.find_or_upload_font(*BRAND_FONT)
client.look_and_feel.set_fonts(regular=body["id"], brand=brand["id"])

print("\nBranding updated.")
