"""Encode local files for EnrolHQ's base64-in-JSON file fields.

EnrolHQ settings endpoints do not take multipart uploads. Image and file
fields (campus logos, event images, policy PDFs, font files) are sent as
base64 data URIs inside the JSON body:

- Images: ``data:image/png;base64,<b64>``. The server sniffs the type from
  the bytes; png, jpeg, webp, bmp and tiff are accepted. SVG, ICO and GIF are
  rejected, so favicons must be PNG.
- Files: ``data:application/pdf;filename:policy.pdf;base64,<b64>``. The
  ``filename:`` part is mandatory and its extension must be one the field
  allows (e.g. pdf/docx for policy documents, woff/woff2 for fonts).

Sending ``""`` or ``None`` clears a file; omitting the key keeps it. A GET
returns file fields as URLs, which the server rejects if you PUT them back,
so drop URL values before re-sending (see :func:`is_data_uri`).
"""

import base64
import mimetypes
import os
from typing import Optional, Tuple, Union

Source = Union[str, "os.PathLike[str]", bytes, bytearray]

IMAGE_MIME_TYPES = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
}

_FILE_MIME_TYPES = {
    "woff": "font/woff",
    "woff2": "font/woff2",
    "pdf": "application/pdf",
}


def _read(source: Source) -> Tuple[bytes, Optional[str]]:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source), None
    path = os.fspath(source)
    with open(path, "rb") as f:
        return f.read(), os.path.basename(path)


def sniff_image_type(data: bytes) -> Optional[str]:
    """Return the image kind (``png``, ``jpeg``, ...) from magic bytes."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"BM"):
        return "bmp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    return None


def image_data_uri(source: Source) -> str:
    """Encode an image (path or bytes) as a data URI for an image field.

    Raises:
        ValueError: If the bytes are not a type EnrolHQ accepts (png, jpeg,
            webp, bmp, tiff). Convert SVG/ICO/GIF to PNG first.
    """
    data, _ = _read(source)
    kind = sniff_image_type(data)
    if kind is None:
        raise ValueError(
            "Unsupported image type: EnrolHQ accepts png, jpeg, webp, bmp or "
            "tiff (convert SVG, ICO and GIF to PNG first)"
        )
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{IMAGE_MIME_TYPES[kind]};base64,{encoded}"


def file_data_uri(
    source: Source,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> str:
    """Encode a file (path or bytes) as a data URI for a document/font field.

    Args:
        source: Path to the file, or its raw bytes.
        filename: Name sent to the server; its extension is validated
            server-side. Defaults to the file's basename (required when
            *source* is bytes).
        mime_type: Defaults to a guess from the filename's extension.
    """
    data, basename = _read(source)
    filename = filename or basename
    if not filename:
        raise ValueError("filename is required when encoding raw bytes")
    if ";" in filename or "," in filename:
        raise ValueError("filename must not contain ';' or ','")
    if mime_type is None:
        ext = os.path.splitext(filename)[1][1:].lower()
        mime_type = (
            _FILE_MIME_TYPES.get(ext)
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};filename:{filename};base64,{encoded}"


def is_data_uri(value: object) -> bool:
    """True if *value* is a base64 data URI (i.e. safe to PUT to a file field)."""
    return isinstance(value, str) and value.startswith("data:") and ";base64," in value
