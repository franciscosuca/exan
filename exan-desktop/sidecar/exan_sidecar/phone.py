"""Phone upload bridge: an on-demand HTTP server on the local network that accepts photos from a phone.

It is only started when the user opens the phone dialog, listens on a random port, accepts clients from
private address ranges only and requires an unguessable token in every URL. It stops after inactivity.
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import io
import logging
import secrets
import socket
import time
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, Literal

import segno
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .errors import ApiError
from .netutil import is_lan_client, lan_addresses
from .phone_page import render_page
from .uploads import BodyLimitMiddleware, read_upload_form

if TYPE_CHECKING:
    from .state import AppState

log = logging.getLogger(__name__)

PhoneTarget = Literal["key", "participants"]
MAX_PHONE_FILES = 30
MAX_PHONE_FILE_BYTES = 25 * 1024 * 1024
MAX_PHONE_REQUEST_BYTES = 160 * 1024 * 1024
IDLE_TIMEOUT_SECONDS = 30 * 60
PHONE_MAX_SIDE = 2000

_SECURITY_HEADERS = [
    (b"cache-control", b"no-store"),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"cross-origin-resource-policy", b"same-origin"),
]


class _EmbeddedServer(uvicorn.Server):
    """A uvicorn server that runs inside the existing event loop and leaves signal handling alone."""

    @contextlib.contextmanager
    def capture_signals(self) -> Iterator[None]:
        yield


async def _plain(send: Send, status: int, text: str) -> None:
    body = text.encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
                *_SECURITY_HEADERS,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class _PhoneGate:
    """Allows only local-network clients that present the current token in the URL path."""

    def __init__(self, app: ASGIApp, bridge: PhoneBridge) -> None:
        self.app = app
        self.bridge = bridge

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        client = scope.get("client")
        if not client or not is_lan_client(str(client[0])):
            await _plain(send, 403, "Forbidden")
            return
        token = self.bridge.token
        parts = str(scope.get("path", "")).split("/")
        if (
            token is None
            or len(parts) < 3
            or parts[1] != "m"
            or not hmac.compare_digest(parts[2].encode(), token.encode())
        ):
            await _plain(send, 404, "Not found")
            return
        self.bridge.touch()

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), *_SECURITY_HEADERS]
            await send(message)

        await self.app(scope, receive, send_with_headers)


class PhoneBridge:
    def __init__(
        self,
        state: AppState,
        *,
        bind_host: str = "0.0.0.0",  # noqa: S104 - the phone must reach this server over the LAN
        idle_timeout: float = IDLE_TIMEOUT_SECONDS,
        addresses: Callable[[], list[str]] = lan_addresses,
    ) -> None:
        self.state = state
        self.bind_host = bind_host
        self.idle_timeout = idle_timeout
        self._addresses = addresses
        self.token: str | None = None
        self.target: PhoneTarget = "participants"
        self.port: int | None = None
        self.uploads = 0
        self.last_upload: float | None = None
        self._last_activity = 0.0
        self._server: _EmbeddedServer | None = None
        self._task: asyncio.Task[None] | None = None
        self._idle_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    @property
    def active(self) -> bool:
        return self._server is not None

    def touch(self) -> None:
        self._last_activity = time.monotonic()

    # -- lifecycle -----------------------------------------------------------------
    async def start(self, target: PhoneTarget) -> dict[str, Any]:
        async with self._lock:
            self.target = target
            self.touch()
            if self._server is not None:
                return self.view()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                sock.bind((self.bind_host, 0))
                sock.listen(64)
                sock.setblocking(False)
            except OSError:
                sock.close()
                raise
            config = uvicorn.Config(
                self._build_app(),
                log_config=None,
                access_log=False,
                lifespan="off",
                http="h11",
                loop="asyncio",
                ws="none",
                server_header=False,
                date_header=False,
                proxy_headers=False,
                timeout_graceful_shutdown=1,
                limit_concurrency=32,
            )
            server = _EmbeddedServer(config)
            task = asyncio.create_task(server.serve(sockets=[sock]), name="exan-phone-server")
            task.add_done_callback(_log_crash)
            for _ in range(100):
                if server.started or task.done():
                    break
                await asyncio.sleep(0.02)
            if not server.started:
                server.should_exit = True
                with contextlib.suppress(Exception, asyncio.CancelledError):
                    await asyncio.wait_for(task, 2)
                sock.close()
                raise OSError("The phone connection could not be started.")
            self.token = secrets.token_urlsafe(18)
            self.port = int(sock.getsockname()[1])
            self.uploads = 0
            self.last_upload = None
            self._server = server
            self._task = task
            self._idle_task = asyncio.create_task(self._idle_watch(), name="exan-phone-idle")
            log.info("Phone bridge started on port %s", self.port)
            return self.view()

    async def set_target(self, target: PhoneTarget) -> dict[str, Any]:
        self.target = target
        self.state.session.bump()
        return self.view()

    async def stop(self) -> None:
        async with self._lock:
            server, task, idle = self._server, self._task, self._idle_task
            self._server = self._task = self._idle_task = None
            self.token = None
            self.port = None
            if idle is not None and idle is not asyncio.current_task():
                idle.cancel()
            if server is None or task is None:
                return
            server.should_exit = True
            try:
                await asyncio.wait_for(task, 5)
            except (TimeoutError, asyncio.CancelledError):
                task.cancel()
            except Exception:
                log.exception("Phone bridge did not stop cleanly")
            log.info("Phone bridge stopped")

    async def _idle_watch(self) -> None:
        while True:
            await asyncio.sleep(min(30.0, max(0.05, self.idle_timeout / 4)))
            if time.monotonic() - self._last_activity >= self.idle_timeout:
                log.info("Phone bridge stopped after inactivity")
                await self.stop()
                self.state.session.bump()
                return

    # -- views ---------------------------------------------------------------------
    def urls(self) -> list[str]:
        if self.token is None or self.port is None:
            return []
        return [f"http://{address}:{self.port}/m/{self.token}" for address in self._addresses()]

    def view(self) -> dict[str, Any]:
        if not self.active:
            return {"active": False, "target": self.target, "urls": [], "uploads": 0}
        remaining = max(0.0, self.idle_timeout - (time.monotonic() - self._last_activity))
        return {
            "active": True,
            "target": self.target,
            "port": self.port,
            "urls": [{"url": url, "qr": qr_svg(url)} for url in self.urls()],
            "uploads": self.uploads,
            "seconds_since_upload": None if self.last_upload is None else time.monotonic() - self.last_upload,
            "expires_in": int(remaining),
        }

    # -- phone-facing app --------------------------------------------------------------
    def _build_app(self) -> ASGIApp:
        app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        bridge = self

        @app.get("/m/{token}")
        async def page(token: str) -> HTMLResponse:
            current = bridge.token
            if current is None or not hmac.compare_digest(token.encode(), current.encode()):
                return HTMLResponse("Not found", status_code=404)
            nonce = secrets.token_urlsafe(16)
            lang = bridge.state.settings.get().language
            config = {
                "base": f"/m/{current}",
                "target": bridge.target,
                "lang": lang,
                "maxFiles": MAX_PHONE_FILES,
                "maxSide": PHONE_MAX_SIDE,
            }
            csp = (
                f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
                "img-src blob: data:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'none'"
            )
            return HTMLResponse(
                render_page(nonce=nonce, config=config, lang=lang), headers={"content-security-policy": csp}
            )

        @app.get("/m/{token}/info")
        async def info(token: str) -> dict[str, Any]:
            return {"target": bridge.target, "lang": bridge.state.settings.get().language}

        @app.post("/m/{token}/upload")
        async def upload(token: str, request: Request) -> JSONResponse:
            files, fields, errors = await read_upload_form(
                request, max_files=MAX_PHONE_FILES, max_file_bytes=MAX_PHONE_FILE_BYTES
            )
            target = fields.get("target", bridge.target)
            if target not in ("key", "participants"):
                target = bridge.target
            grouping = "file" if fields.get("grouping") == "file" else "single"
            if not files and not errors:
                return JSONResponse(
                    {"detail": "No photos were received.", "code": "no_files"}, status_code=400
                )
            state = bridge.state
            groups, ingest_errors = await state.ingest(files, source="phone")
            errors.extend(ingest_errors)
            pages = sum(len(group) for group in groups)
            participants = 0
            try:
                if target == "key":
                    state.add_key_pages(groups)
                elif groups:
                    participants = len(state.add_participants(groups, grouping, source="phone"))
            except ApiError as exc:
                return JSONResponse({"detail": exc.message, "code": exc.code}, status_code=exc.status)
            if pages:
                bridge.uploads += pages
                bridge.last_upload = time.monotonic()
                state.session.last_phone_upload = {
                    "id": secrets.token_hex(4),
                    "target": target,
                    "pages": pages,
                    "participants": participants,
                }
                state.session.bump()
            return JSONResponse(
                {"target": target, "pages": pages, "participants": participants, "errors": errors}
            )

        gated = _PhoneGate(BodyLimitMiddleware(app, MAX_PHONE_REQUEST_BYTES), self)
        return gated


def _log_crash(task: asyncio.Task[None]) -> None:
    if not task.cancelled() and task.exception() is not None:
        log.error("Phone bridge server crashed", exc_info=task.exception())


def qr_svg(data: str) -> str:
    buffer = io.BytesIO()
    segno.make(data, error="m", micro=False).save(
        buffer, kind="svg", scale=4, border=2, xmldecl=False, dark="#000"
    )
    return buffer.getvalue().decode("utf-8")
