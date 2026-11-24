"""Independent workflow services for the inference application."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UploadedDocument:
    """Uploaded bytes in a form that does not depend on FastAPI."""

    content: bytes
    filename: str
    content_type: str | None
