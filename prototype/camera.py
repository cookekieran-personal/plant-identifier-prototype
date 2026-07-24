"""Temporary image handling for Streamlit camera uploads.

User photos are not stored permanently. Streamlit provides image bytes; this
module writes them to a temporary file only because PlantNet expects multipart
file upload, then deletes the file after the API call.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import BinaryIO, Iterator


@dataclass(frozen=True)
class UploadedImageSnapshot:
    """In-memory copy of a Streamlit image upload for a later rerun."""

    data: bytes
    type: str
    name: str = "plant-photo.jpg"

    def getvalue(self) -> bytes:
        """Match Streamlit's uploaded-file interface used by temporary_image_file."""

        return self.data


@contextmanager
def temporary_image_file(uploaded_file: BinaryIO, suffix: str = ".jpg") -> Iterator[Path]:
    """Write an uploaded image to a temporary file and remove it afterwards."""

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = Path(temp.name)
    try:
        temp.write(uploaded_file.getvalue())
        temp.close()
        yield temp_path
    finally:
        temp.close()
        temp_path.unlink(missing_ok=True)


def image_suffix(uploaded_file: object) -> str:
    """Infer a safe image suffix from a Streamlit uploaded file."""

    mime_type = getattr(uploaded_file, "type", "") or ""
    if mime_type == "image/png":
        return ".png"
    return ".jpg"


def snapshot_uploaded_image(uploaded_file: object) -> UploadedImageSnapshot:
    """Copy a Streamlit camera/upload object so it survives later reruns."""

    mime_type = getattr(uploaded_file, "type", "") or "image/jpeg"
    name = getattr(uploaded_file, "name", "") or f"plant-photo{image_suffix(uploaded_file)}"
    return UploadedImageSnapshot(data=uploaded_file.getvalue(), type=mime_type, name=name)
