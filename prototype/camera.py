"""Temporary image handling for Streamlit camera uploads.

User photos are not stored permanently. Streamlit provides image bytes; this
module writes them to a temporary file only because PlantNet expects multipart
file upload, then deletes the file after the API call.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import tempfile
from typing import BinaryIO, Iterator


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

