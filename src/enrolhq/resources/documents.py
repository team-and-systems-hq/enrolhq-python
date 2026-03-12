"""Documents resource."""

import os
from typing import Any, Dict, List, Optional

from ..pagination import PaginatedIterator, PaginatedResponse
from .base import BaseResource


class DocumentsResource(BaseResource):
    """Manage application documents (upload, download, delete)."""

    def list(
        self, student_profile_id: str, *, page_size: int = 1000, **filters: Any
    ) -> PaginatedIterator:
        """List all documents for a student profile."""
        filters["student_profile"] = student_profile_id
        return self._list(
            "application-documents/", params=filters, page_size=page_size
        )

    def list_page(
        self,
        student_profile_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        **filters: Any,
    ) -> PaginatedResponse:
        """Fetch a single page of documents for a student profile."""
        filters["student_profile"] = student_profile_id
        return self._list_page(
            "application-documents/",
            params=filters,
            page=page,
            page_size=page_size,
        )

    def upload(
        self,
        student_profile_id: str,
        file_path: str,
        group_kind: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a document for a student profile.

        Args:
            student_profile_id: UUID of the student profile.
            file_path: Local path to the file to upload.
            group_kind: DocumentKind string (e.g. "SCHOOL_REPORT").
            filename: Optional display name; defaults to the file's basename.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if filename is None:
            filename = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            resp = self._http.request(
                "POST",
                self._url("application-documents/"),
                data={
                    "filename": filename,
                    "group_kind": str(group_kind),
                    "student_profile": str(student_profile_id),
                },
                files={"file": (filename, f)},
            )
        return resp.json()

    def download(self, document_url: str, dest_path: str) -> str:
        """Download a document to a local file.

        Args:
            document_url: The full URL of the document (from the ``file`` field).
            dest_path: Local path to save the file.
        """
        resp = self._http.get(document_url)
        dest_dir = os.path.dirname(dest_path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    def delete(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Delete a document by ID."""
        return self._delete(f"application-documents/{document_id}/")

    def print_document(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a printable document (e.g. enrolment summary)."""
        return self._post("applications/print_document/", json=data)
