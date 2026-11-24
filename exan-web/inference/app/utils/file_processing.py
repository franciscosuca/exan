"""Utilities for processing uploaded files (PDF, images, and Word documents)."""

import io

import fitz  # PyMuPDF
from docx import Document
from PIL import Image

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/jpg"}
SUPPORTED_PDF_TYPES = {"application/pdf"}
SUPPORTED_WORD_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_PDF_TYPES | SUPPORTED_WORD_TYPES


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
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
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


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text content from a PDF file."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n\n".join(text_parts)


def extract_text_from_word(file_bytes: bytes) -> str:
    """Extract text content from a Word document (.docx)."""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text(file_bytes: bytes, mime_type: str) -> str:
    """Extract text from a PDF or Word document for text-based evaluation."""
    if mime_type == "application/pdf":
        return extract_text_from_pdf(file_bytes)

    if mime_type in SUPPORTED_WORD_TYPES:
        return extract_text_from_word(file_bytes)

    raise ValueError(f"Text extraction not supported for: {mime_type}. Use PDF or Word documents.")


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
