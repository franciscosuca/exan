"""Decode uploaded photos/PDFs into normalised in-memory JPEG pages.

Pages are never written to disk: originals are decoded, orientation-corrected, downscaled and kept
in memory for the current session only.
"""

from __future__ import annotations

import io
import logging
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path, PurePath

from PIL import Image, ImageOps, UnidentifiedImageError

log = logging.getLogger(__name__)

# Phone cameras produce up to ~200 MP images; JPEGs are decoded in reduced "draft" mode anyway.
Image.MAX_IMAGE_PIXELS = 250_000_000

STORE_MAX_SIDE = 2400
THUMB_MAX_SIDE = 360
PDF_RENDER_LONG_SIDE = 2200
MAX_PDF_PAGES = 40
MAX_FILE_BYTES = 60 * 1024 * 1024

_PDF_LOCK = threading.Lock()


class ImageError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class PreparedPage:
    name: str
    width: int
    height: int
    jpeg: bytes
    thumb: bytes


def sniff(data: bytes) -> str:
    head = data[:32]
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head.startswith(b"%PDF") or b"%PDF-" in data[:1024]:
        return "pdf"
    if head[4:8] == b"ftyp" and head[8:12] in (
        b"heic",
        b"heix",
        b"heim",
        b"heis",
        b"hevc",
        b"hevx",
        b"mif1",
        b"msf1",
    ):
        return "heic"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if head[:2] == b"BM":
        return "bmp"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    return "unknown"


def prepare_upload(data: bytes, filename: str) -> list[PreparedPage]:
    """Decode one uploaded file into one or more normalised pages."""
    if not data:
        raise ImageError("empty", "The file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise ImageError("too_large", "The file is larger than 60 MB.")
    stem = PurePath(filename or "page").stem[:80] or "page"
    kind = sniff(data)
    if kind == "pdf":
        images = _render_pdf(data, stem)
    elif kind == "heic":
        images = [(stem, _decode_heic(data))]
    elif kind in ("jpeg", "png", "webp", "gif", "bmp", "tiff"):
        images = [(stem, _decode_image(data))]
    else:
        raise ImageError("unsupported", "Unsupported file type. Use JPG, PNG, WebP or PDF.")
    return [_finish(name, image) for name, image in images]


def _decode_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        if image.format == "JPEG":
            image.draft("RGB", (STORE_MAX_SIDE, STORE_MAX_SIDE))
        image = ImageOps.exif_transpose(image) or image
        image.load()
    except Image.DecompressionBombError as exc:
        raise ImageError("too_large", "The image has too many pixels.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ImageError("unreadable", "The image could not be read.") from exc
    return _to_rgb(image)


def _to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA", "PA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _render_pdf(data: bytes, stem: str) -> list[tuple[str, Image.Image]]:
    import pypdfium2 as pdfium  # imported lazily: only needed for PDF uploads

    with _PDF_LOCK:
        try:
            document = pdfium.PdfDocument(data)
        except pdfium.PdfiumError as exc:
            raise ImageError(
                "unreadable", "The PDF could not be opened (it may be damaged or encrypted)."
            ) from exc
        try:
            count = len(document)
            if count == 0:
                raise ImageError("empty", "The PDF has no pages.")
            if count > MAX_PDF_PAGES:
                raise ImageError("too_many_pages", f"The PDF has more than {MAX_PDF_PAGES} pages.")
            pages: list[tuple[str, Image.Image]] = []
            for number in range(count):
                page = document[number]
                try:
                    width, height = page.get_size()
                    scale = min(4.0, PDF_RENDER_LONG_SIDE / max(width, height, 1.0))
                    bitmap = page.render(scale=scale)
                    try:
                        image = bitmap.to_pil().convert("RGB")
                    finally:
                        bitmap.close()
                finally:
                    page.close()
                label = stem if count == 1 else f"{stem} ({number + 1}/{count})"
                pages.append((label, image))
            return pages
        finally:
            document.close()


def _decode_heic(data: bytes) -> Image.Image:
    """HEIC/HEIF (iPhone photos). Converted with the built-in `sips` tool on macOS."""
    sips = None
    if sys.platform == "darwin":
        sips = shutil.which("sips") or ("/usr/bin/sips" if Path("/usr/bin/sips").exists() else None)
    if sips is None:
        raise ImageError(
            "heic_unsupported",
            "HEIC photos cannot be read on this computer. Use the phone upload (it converts photos "
            "automatically) or export the photos as JPEG.",
        )
    with tempfile.TemporaryDirectory(prefix="exan-heic-") as tmp:
        source = Path(tmp) / "input.heic"
        target = Path(tmp) / "output.jpg"
        source.write_bytes(data)
        try:
            subprocess.run(  # noqa: S603 - fixed system tool, arguments are our own temp paths
                [sips, "-s", "format", "jpeg", str(source), "--out", str(target)],
                check=True,
                capture_output=True,
                timeout=60,
            )
            converted = target.read_bytes()
        except (OSError, subprocess.SubprocessError) as exc:
            raise ImageError("unreadable", "The HEIC photo could not be converted.") from exc
    return _decode_image(converted)


def _encode(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def _finish(name: str, image: Image.Image) -> PreparedPage:
    if max(image.size) > STORE_MAX_SIDE:
        image.thumbnail((STORE_MAX_SIDE, STORE_MAX_SIDE), Image.Resampling.LANCZOS)
    jpeg = _encode(image, 88)
    thumb = image.copy()
    thumb.thumbnail((THUMB_MAX_SIDE, THUMB_MAX_SIDE), Image.Resampling.LANCZOS)
    return PreparedPage(
        name=name, width=image.width, height=image.height, jpeg=jpeg, thumb=_encode(thumb, 80)
    )


def model_image(jpeg: bytes, max_side: int) -> bytes:
    """Return the page as JPEG no larger than `max_side` pixels for the vision model."""
    image = Image.open(io.BytesIO(jpeg))
    if max(image.size) <= max_side:
        return jpeg
    image.draft("RGB", (max_side, max_side))
    image = image.convert("RGB")
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return _encode(image, 90)
