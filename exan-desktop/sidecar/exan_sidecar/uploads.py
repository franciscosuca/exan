"""Helpers shared by the desktop API and the phone bridge for receiving uploads safely."""

from __future__ import annotations

import json
import re
import unicodedata

from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartParser
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

# Keep uploaded photos in memory instead of spooling them to temporary files on disk.
MultiPartParser.spool_max_size = 64 * 1024 * 1024

_BODY_METHODS = {"POST", "PUT", "PATCH"}
_UNSAFE_NAME = re.compile(r"[\x00-\x1f\x7f<>:\"|?*]")


def sanitize_filename(name: str | None, fallback: str = "upload") -> str:
    """Display-only file name: no directories, control characters or excessive length."""
    if not name:
        return fallback
    name = unicodedata.normalize("NFC", name).replace("\\", "/").rsplit("/", 1)[-1]
    name = _UNSAFE_NAME.sub("_", name).strip(" .")
    if len(name) > 120:
        stem, dot, ext = name.rpartition(".")
        name = (stem[:110] + dot + ext[:8]) if dot and len(ext) <= 8 else name[:120]
    return name or fallback


async def _send_json(send: Send, status: int, detail: str, code: str) -> None:
    body = json.dumps({"detail": detail, "code": code}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})


class BodyLimitMiddleware:
    """Requires a Content-Length on requests with a body and rejects bodies above a fixed size."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in _BODY_METHODS:
            await self.app(scope, receive, send)
            return
        length: int | None = None
        chunked = False
        for key, value in scope.get("headers", []):
            if key == b"content-length":
                try:
                    length = int(value)
                except ValueError:
                    length = -1
            elif key == b"transfer-encoding":
                chunked = True
        if chunked or length is None or length < 0:
            await _send_json(send, 411, "A Content-Length header is required.", "length_required")
            return
        if length > self.max_bytes:
            limit = self.max_bytes // (1024 * 1024)
            await _send_json(send, 413, f"The upload is too large (limit {limit} MB).", "too_large")
            return
        await self.app(scope, receive, send)


async def read_upload_form(
    request: Request, *, max_files: int, max_file_bytes: int
) -> tuple[list[tuple[str, bytes]], dict[str, str], list[dict[str, str]]]:
    """Return ``(files, fields, errors)`` from a multipart request. Files are read fully into memory."""
    form = await request.form(max_files=max_files, max_fields=20, max_part_size=64 * 1024)
    files: list[tuple[str, bytes]] = []
    fields: dict[str, str] = {}
    errors: list[dict[str, str]] = []
    try:
        for key, value in form.multi_items():
            if isinstance(value, UploadFile):
                if key != "files":
                    continue
                name = sanitize_filename(value.filename)
                data = await value.read(max_file_bytes + 1)
                if len(data) > max_file_bytes:
                    limit = max_file_bytes // (1024 * 1024)
                    errors.append({"file": name, "code": "too_large", "message": f"Larger than {limit} MB."})
                    continue
                if not data:
                    errors.append({"file": name, "code": "empty", "message": "The file is empty."})
                    continue
                files.append((name, data))
            else:
                fields[key] = str(value)
    finally:
        await form.close()
    return files, fields, errors
