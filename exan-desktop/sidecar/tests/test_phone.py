from __future__ import annotations

import asyncio
import re
from pathlib import Path

import httpx
import pytest

from exan_sidecar.netutil import is_lan_client, lan_addresses
from exan_sidecar.phone import MAX_PHONE_FILES, PhoneBridge, _PhoneGate
from exan_sidecar.state import AppState

from .conftest import FakeEngine, jpeg_bytes, make_config

pytestmark = pytest.mark.anyio


def make_bridge(tmp_path: Path, idle_timeout: float = 600) -> tuple[AppState, PhoneBridge]:
    state = AppState(make_config(tmp_path), engine_factory=lambda *args: FakeEngine())
    bridge = PhoneBridge(
        state, bind_host="127.0.0.1", idle_timeout=idle_timeout, addresses=lambda: ["127.0.0.1"]
    )
    state.phone = bridge
    return state, bridge


def photo(name: str, width: int = 500) -> tuple[str, tuple[str, bytes, str]]:
    return ("files", (name, jpeg_bytes(width, 700), "image/jpeg"))


@pytest.mark.parametrize(
    ("host", "allowed"),
    [
        ("127.0.0.1", True),
        ("::1", True),
        ("192.168.1.20", True),
        ("10.0.0.7", True),
        ("172.20.1.1", True),
        ("100.100.1.1", True),
        ("169.254.10.10", True),
        ("fe80::1%en0", True),
        ("fd12:3456::1", True),
        ("::ffff:192.168.1.5", True),
        ("8.8.8.8", False),
        ("::ffff:8.8.8.8", False),
        ("2001:4860:4860::8888", False),
        ("0.0.0.0", False),
        ("testclient", False),
        ("", False),
    ],
)
def test_is_lan_client(host: str, allowed: bool) -> None:
    assert is_lan_client(host) is allowed


def test_lan_addresses_are_private_ipv4() -> None:
    for address in lan_addresses():
        assert is_lan_client(address)
        assert ":" not in address


async def test_phone_bridge_end_to_end(tmp_path: Path) -> None:
    state, bridge = make_bridge(tmp_path)
    view = await bridge.start("participants")
    try:
        assert view["active"] is True
        url = view["urls"][0]["url"]
        assert re.fullmatch(r"http://127\.0\.0\.1:\d+/m/[A-Za-z0-9_-]{24}", url)
        assert view["urls"][0]["qr"].startswith("<svg")
        token = url.rsplit("/", 1)[1]
        base = url.rsplit("/m/", 1)[0]

        async with httpx.AsyncClient(base_url=base, trust_env=False, timeout=10) as phone:
            page = await phone.get(f"/m/{token}")
            assert page.status_code == 200
            assert page.headers["cache-control"] == "no-store"
            assert page.headers["x-frame-options"] == "DENY"
            nonce = re.search(r"script-src 'nonce-([^']+)'", page.headers["content-security-policy"]).group(1)
            assert f'<script nonce="{nonce}">' in page.text
            assert '"target": "participants"' in page.text
            assert token not in page.text.split("exan-config")[0]  # token only in the config blob

            assert (await phone.get("/m/wrong-token")).status_code == 404
            assert (await phone.get("/")).status_code == 404
            assert (await phone.get(f"/m/{token}x")).status_code == 404

            info = (await phone.get(f"/m/{token}/info")).json()
            assert info == {"target": "participants", "lang": "de"}

            one = await phone.post(
                f"/m/{token}/upload",
                files=[photo("p1.jpg"), photo("p2.jpg", 501)],
                data={"target": "participants", "grouping": "single"},
            )
            assert one.status_code == 200, one.text
            assert one.json() == {"target": "participants", "pages": 2, "participants": 1, "errors": []}
            (participant,) = state.session.participants.values()
            assert participant.source == "phone" and len(participant.pages) == 2
            assert state.session.last_phone_upload["pages"] == 2

            each = await phone.post(
                f"/m/{token}/upload",
                files=[
                    photo("a.jpg"),
                    photo("b.jpg"),
                    ("files", ("x.heic", b"\x00\x00\x00\x18ftypheic" + b"\x00" * 40, "image/heic")),
                ],
                data={"target": "participants", "grouping": "file"},
            )
            body = each.json()
            assert body["participants"] == 2
            assert body["errors"][0]["file"] == "x.heic"
            assert len(state.session.participants) == 3

            await bridge.set_target("key")
            assert (await phone.get(f"/m/{token}/info")).json()["target"] == "key"
            key = await phone.post(f"/m/{token}/upload", files=[photo("key.jpg")], data={"target": "key"})
            assert key.json()["pages"] == 1
            assert len(state.session.key.pages) == 1
            assert state.session.key.pages[0].source == "phone"

            too_many = await phone.post(
                f"/m/{token}/upload", files=[photo(f"{i}.jpg", 300) for i in range(MAX_PHONE_FILES + 1)]
            )
            assert too_many.status_code == 400

            async def stream():
                yield b"--x\r\n"

            chunked = await phone.post(
                f"/m/{token}/upload",
                content=stream(),
                headers={"content-type": "multipart/form-data; boundary=x"},
            )
            assert chunked.status_code == 411

            empty = await phone.post(f"/m/{token}/upload", data={"target": "key"})
            assert empty.status_code in (400, 422)

        assert bridge.view()["uploads"] == 5
    finally:
        await bridge.stop()
    assert bridge.view()["active"] is False
    async with httpx.AsyncClient(trust_env=False, timeout=2) as late:
        with pytest.raises(httpx.HTTPError):
            await late.get(url)


async def test_restart_issues_a_new_token(tmp_path: Path) -> None:
    _, bridge = make_bridge(tmp_path)
    first = (await bridge.start("key"))["urls"][0]["url"]
    again = (await bridge.start("participants"))["urls"][0]["url"]
    assert first == again  # already running: same link, new target
    assert bridge.target == "participants"
    await bridge.stop()
    second = (await bridge.start("key"))["urls"][0]["url"]
    await bridge.stop()
    assert first.rsplit("/", 1)[1] != second.rsplit("/", 1)[1]


async def test_idle_timeout_stops_the_bridge(tmp_path: Path) -> None:
    state, bridge = make_bridge(tmp_path, idle_timeout=0.3)
    await bridge.start("participants")
    version = state.session.version
    for _ in range(100):
        if not bridge.active and state.session.version > version:
            break
        await asyncio.sleep(0.05)
    assert bridge.active is False
    assert state.session.version > version


async def test_public_clients_are_rejected(tmp_path: Path) -> None:
    _, bridge = make_bridge(tmp_path)
    bridge.token = "secret-token"
    reached: list[bool] = []

    async def app(scope, receive, send) -> None:
        reached.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def call(client: tuple[str, int], path: str) -> int:
        sent: list[dict] = []

        async def send(message: dict) -> None:
            sent.append(message)

        async def receive() -> dict:
            return {"type": "http.request", "body": b""}

        scope = {"type": "http", "method": "GET", "path": path, "headers": [], "client": client}
        await _PhoneGate(app, bridge)(scope, receive, send)
        return sent[0]["status"]

    assert await call(("8.8.8.8", 5000), "/m/secret-token") == 403
    assert await call(("192.168.1.5", 5000), "/m/other") == 404
    assert reached == []
    assert await call(("192.168.1.5", 5000), "/m/secret-token") == 200
    assert reached == [True]
