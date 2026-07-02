"""Tests for file processing utilities."""

import pytest

from app.file_processing import get_mime_type, pdf_to_images, process_upload


def test_get_mime_type_from_content_type():
    """Content-type header is preferred when valid."""
    assert get_mime_type("file.pdf", "application/pdf") == "application/pdf"
    assert get_mime_type("file.png", "image/png") == "image/png"


def test_get_mime_type_from_extension():
    """Falls back to extension when content-type is missing."""
    assert get_mime_type("exam.pdf", None) == "application/pdf"
    assert get_mime_type("photo.jpg", None) == "image/jpeg"
    assert get_mime_type("photo.jpeg", None) == "image/jpeg"
    assert get_mime_type("scan.png", None) == "image/png"
    assert get_mime_type("scan.webp", None) == "image/webp"


def test_get_mime_type_unknown():
    """Unknown extensions return octet-stream."""
    assert get_mime_type("file.xyz", None) == "application/octet-stream"


def test_pdf_to_images():
    """PDF pages are converted to PNG images."""
    import fitz

    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    images = pdf_to_images(pdf_bytes)
    assert len(images) == 2
    for img_bytes, mime in images:
        assert mime == "image/png"
        assert len(img_bytes) > 0
        # PNG magic bytes
        assert img_bytes[:4] == b"\x89PNG"


def test_process_upload_pdf():
    """process_upload handles PDFs."""
    import fitz

    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()

    result = process_upload(pdf_bytes, "application/pdf")
    assert len(result) == 1
    assert result[0][1] == "image/png"


def test_process_upload_image():
    """process_upload handles valid images."""
    import io

    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    result = process_upload(png_bytes, "image/png")
    assert len(result) == 1
    assert result[0][0] == png_bytes
    assert result[0][1] == "image/png"


def test_process_upload_unsupported():
    """process_upload raises for unsupported types."""
    with pytest.raises(ValueError, match="Unsupported file type"):
        process_upload(b"hello", "text/plain")
