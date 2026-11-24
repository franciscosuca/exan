from __future__ import annotations

import io
import sys

import pytest
from PIL import Image

from exan_sidecar import images
from exan_sidecar.images import ImageError, model_image, prepare_upload, sniff

from .conftest import image_size, jpeg_bytes


def _png_with_alpha() -> bytes:
    image = Image.new("RGBA", (300, 200), (0, 0, 0, 0))
    image.paste((0, 0, 0, 255), (0, 0, 100, 100))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf(pages: int) -> bytes:
    frames = [Image.new("RGB", (595, 842), (255, 255, 255)) for _ in range(pages)]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="PDF", save_all=True, append_images=frames[1:], resolution=72)
    return buffer.getvalue()


def test_sniff() -> None:
    assert sniff(jpeg_bytes()) == "jpeg"
    assert sniff(_png_with_alpha()) == "png"
    assert sniff(_pdf(1)) == "pdf"
    assert sniff(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00") == "heic"
    assert sniff(b"hello") == "unknown"


def test_jpeg_is_kept_in_memory_with_thumbnail() -> None:
    (page,) = prepare_upload(jpeg_bytes(640, 800), "C:\\Users\\me\\sheet 1.jpg")
    assert (page.width, page.height) == (640, 800)
    assert page.name == "sheet 1" or page.name.endswith("sheet 1")
    assert image_size(page.jpeg) == (640, 800)
    assert max(image_size(page.thumb)) == images.THUMB_MAX_SIDE


def test_exif_orientation_is_applied() -> None:
    image = Image.new("RGB", (400, 300), (200, 200, 200))
    exif = image.getexif()
    exif[0x0112] = 6  # rotate 90° clockwise when displayed
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    (page,) = prepare_upload(buffer.getvalue(), "rotated.jpg")
    assert (page.width, page.height) == (300, 400)


def test_large_photos_are_downscaled() -> None:
    (page,) = prepare_upload(jpeg_bytes(4000, 3000), "big.jpg")
    assert max(page.width, page.height) <= images.STORE_MAX_SIDE


def test_transparent_png_is_flattened_on_white() -> None:
    (page,) = prepare_upload(_png_with_alpha(), "scan.png")
    with Image.open(io.BytesIO(page.jpeg)) as decoded:
        assert decoded.mode == "RGB"
        assert decoded.getpixel((250, 150))[0] > 240  # transparent area became white
        assert decoded.getpixel((10, 10))[0] < 30


def test_pdf_pages_are_rendered() -> None:
    pages = prepare_upload(_pdf(3), "class-test.pdf")
    assert [p.name for p in pages] == ["class-test (1/3)", "class-test (2/3)", "class-test (3/3)"]
    assert all(p.height > p.width for p in pages)
    assert max(pages[0].width, pages[0].height) == pytest.approx(images.PDF_RENDER_LONG_SIDE, abs=2)


def test_pdf_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(images, "MAX_PDF_PAGES", 2)
    with pytest.raises(ImageError) as error:
        prepare_upload(_pdf(3), "long.pdf")
    assert error.value.code == "too_many_pages"


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"", "empty"),
        (b"not an image at all", "unsupported"),
        (b"\xff\xd8\xff\xe0broken jpeg", "unreadable"),
        (b"%PDF-1.7 broken", "unreadable"),
    ],
)
def test_bad_files(data: bytes, code: str) -> None:
    with pytest.raises(ImageError) as error:
        prepare_upload(data, "bad")
    assert error.value.code == code


def test_heic_without_converter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(ImageError) as error:
        prepare_upload(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64, "IMG_0001.HEIC")
    assert error.value.code == "heic_unsupported"


def test_heic_with_sips(monkeypatch: pytest.MonkeyPatch) -> None:
    converted = jpeg_bytes(300, 500)

    def fake_run(args: list[str], **kwargs: object) -> None:
        out = args[args.index("--out") + 1]
        with open(out, "wb") as handle:
            handle.write(converted)

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(images.shutil, "which", lambda name: "/usr/bin/sips")
    monkeypatch.setattr(images.subprocess, "run", fake_run)
    (page,) = prepare_upload(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64, "IMG_0001.HEIC")
    assert (page.width, page.height) == (300, 500)


def test_model_image_downscales_only_when_needed() -> None:
    small = jpeg_bytes(800, 600)
    assert model_image(small, 1600) == small
    assert max(image_size(model_image(jpeg_bytes(2400, 1800), 1200))) == 1200
