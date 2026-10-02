from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest

from exan_sidecar import __version__

from .conftest import SECRET

SIDECAR_DIR = Path(__file__).resolve().parents[1]


def sidecar_command() -> list[str]:
    frozen = os.environ.get("EXAN_SIDECAR_BINARY")
    return [frozen] if frozen else [sys.executable, "-m", "exan_sidecar"]


def launch(tmp_path: Path, **extra: str) -> subprocess.Popen[str]:
    env = {
        **os.environ,
        "PYTHONPATH": str(SIDECAR_DIR),
        "EXAN_SECRET": SECRET,
        "EXAN_DATA_DIR": str(tmp_path / "data"),
        "EXAN_LOG_DIR": str(tmp_path / "logs"),
        "EXAN_WATCH_STDIN": "1",
        **extra,
    }
    return subprocess.Popen(
        sidecar_command(),
        cwd=SIDECAR_DIR,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def read_port(process: subprocess.Popen[str], timeout: float = 60) -> int:
    lines: queue.Queue[str] = queue.Queue()

    def pump() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            lines.put(line)

    threading.Thread(target=pump, daemon=True).start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            line = lines.get(timeout=0.5)
        except queue.Empty:
            if process.poll() is not None:
                break
            continue
        if line.startswith("EXAN_PORT="):
            return int(line.strip().split("=", 1)[1])
    process.kill()
    raise AssertionError(f"no handshake; stderr: {process.stderr.read() if process.stderr else ''}")


def wait_healthy(port: int) -> httpx.Response:
    deadline = time.monotonic() + 30
    while True:
        try:
            return httpx.get(
                f"http://127.0.0.1:{port}/api/health",
                headers={"Authorization": "Bearer " + SECRET},
                trust_env=False,
            )
        except httpx.TransportError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)


def test_handshake_auth_and_shutdown_command(tmp_path: Path) -> None:
    process = launch(tmp_path)
    try:
        port = read_port(process)
        health = wait_healthy(port)
        assert health.status_code == 200 and health.json()["version"] == __version__
        anonymous = httpx.get(f"http://127.0.0.1:{port}/api/health", trust_env=False)
        assert anonymous.status_code == 401
        assert process.stdin is not None
        process.stdin.write("shutdown\n")
        process.stdin.flush()
        assert process.wait(timeout=15) == 0
    finally:
        if process.poll() is None:
            process.kill()
    log = (tmp_path / "logs" / "sidecar.log").read_text(encoding="utf-8")
    assert "listening on 127.0.0.1" in log
    assert SECRET not in log


def test_exits_when_the_shell_disappears(tmp_path: Path) -> None:
    process = launch(tmp_path)
    try:
        wait_healthy(read_port(process))
        assert process.stdin is not None
        process.stdin.close()  # the desktop shell died: stdin reaches EOF
        assert process.wait(timeout=15) == 0
    finally:
        if process.poll() is None:
            process.kill()


def test_fixed_port(tmp_path: Path) -> None:
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    process = launch(tmp_path, EXAN_PORT=str(free_port))
    try:
        assert read_port(process) == free_port
    finally:
        process.kill()
        process.wait(timeout=10)


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"EXAN_SECRET": ""}, "EXAN_SECRET"),
        ({"EXAN_SECRET": "short"}, "EXAN_SECRET"),
        ({"EXAN_HOST": "0.0.0.0"}, "loopback"),
        ({"EXAN_PORT": "70000"}, "EXAN_PORT"),
    ],
)
def test_invalid_environment_is_refused(tmp_path: Path, env: dict[str, str], message: str) -> None:
    process = launch(tmp_path, **env)
    _, stderr = process.communicate(timeout=60)
    assert process.returncode == 2
    assert message in stderr


def test_version_flag() -> None:
    result = subprocess.run(
        [*sidecar_command(), "--version"],
        cwd=SIDECAR_DIR,
        env={**os.environ, "PYTHONPATH": str(SIDECAR_DIR)},
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    assert result.stdout.strip() == __version__


def test_process_smoke_pdf_images_and_phone(tmp_path: Path) -> None:
    """Exercises the native pieces (pypdfium2, Pillow, segno, embedded server) in the real process."""
    import io

    from PIL import Image

    pdf = io.BytesIO()
    first = Image.new("RGB", (620, 877), "white")
    first.save(pdf, "PDF", save_all=True, append_images=[Image.new("RGB", (620, 877), "white")])
    png = io.BytesIO()
    Image.new("RGBA", (300, 200), (10, 20, 30, 128)).save(png, "PNG")

    process = launch(tmp_path)
    try:
        port = read_port(process)
        wait_healthy(port)
        auth = {"Authorization": "Bearer " + SECRET}
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}/api", headers=auth, trust_env=False, timeout=60
        ) as api:
            uploaded = api.post(
                "/key/pages",
                files=[
                    ("files", ("key.pdf", pdf.getvalue(), "application/pdf")),
                    ("files", ("page.png", png.getvalue(), "image/png")),
                ],
            )
            assert uploaded.status_code == 200, uploaded.text
            body = uploaded.json()
            assert body["errors"] == []
            pages = body["session"]["key"]["pages"]
            assert len(pages) == 3
            thumb = api.get(f"/images/{pages[0]['id']}", params={"size": "thumb"})
            assert thumb.status_code == 200 and thumb.headers["content-type"] == "image/jpeg"

            started = api.post("/phone/start", json={"target": "key"})
            assert started.status_code == 200, started.text
            phone = started.json()
            assert phone["active"] is True
            for entry in phone["urls"]:
                assert entry["qr"].startswith("<svg")
            if phone["urls"]:
                token_path = phone["urls"][0]["url"].split(f":{phone['port']}", 1)[1]
                page = httpx.get(f"http://127.0.0.1:{phone['port']}{token_path}", trust_env=False)
                assert page.status_code == 200 and "<html" in page.text
            assert api.post("/phone/stop").json()["active"] is False

            csv = api.get("/export.csv", params={"kind": "summary", "lang": "de"})
            assert csv.status_code == 200 and csv.content.startswith(b"\xef\xbb\xbf")
        assert process.stdin is not None
        process.stdin.write("shutdown\n")
        process.stdin.flush()
        assert process.wait(timeout=15) == 0
    finally:
        if process.poll() is None:
            process.kill()
