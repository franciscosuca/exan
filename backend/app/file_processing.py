"""Utilities for processing uploaded files (PDF and images)."""

import io

import fitz  # PyMuPDF
from PIL import Image

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/jpg"}
SUPPORTED_PDF_TYPES = {"application/pdf"}
SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_PDF_TYPES


def get_mime_type(filename: str, content_type: str | None) -> str:
    """Determine MIME type from filename or content type header."""
    if content_type and content_type in SUPPORTED_TYPES:
        return content_type

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    mime_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    return mime_map.get(ext, "application/octet-stream")


def pdf_to_images(pdf_bytes: bytes) -> list[tuple[bytes, str]]:
    """Convert PDF pages to PNG images. Returns list of (image_bytes, mime_type)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        # Render at 2x resolution for better OCR
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        images.append((img_bytes, "image/png"))
    doc.close()
    return images


def process_upload(file_bytes: bytes, mime_type: str) -> list[tuple[bytes, str]]:
    """Process an uploaded file into a list of (image_bytes, mime_type) pairs.

    PDFs are converted to per-page images. Images are passed through directly.
    """
    if mime_type == "application/pdf":
        return pdf_to_images(file_bytes)

    if mime_type in SUPPORTED_IMAGE_TYPES:
        # Validate it's actually an image
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
        return [(file_bytes, mime_type)]

    raise ValueError(f"Unsupported file type: {mime_type}")
