"""Exan Backend - AI-powered exam scanning and comparison API."""

import json
import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import batch, exams, providers
from .providers.registry import get_provider  # noqa: F401

logger = logging.getLogger(__name__)

app = FastAPI(title="Exan API", version="0.1.0")


async def _replay_body(body: bytes):
    yield body


async def _read_response_body(response: Response) -> bytes:
    body = getattr(response, "body", None)
    if isinstance(body, bytes):
        return body

    body_iterator = getattr(response, "body_iterator", None)
    if body_iterator is None:
        return b""

    body = b"".join([chunk async for chunk in body_iterator])
    response.body_iterator = _replay_body(body)
    return body


def _response_error_detail(body: bytes) -> str:
    if not body:
        return "<response body unavailable>"

    raw_body = body.decode("utf-8", errors="replace")

    try:
        payload = json.loads(raw_body)
    except (TypeError, ValueError):
        return raw_body

    if isinstance(payload, dict):
        for key in ("detail", "error"):
            detail = payload.get(key)
            if isinstance(detail, str):
                return detail

    return raw_body


@app.middleware("http")
async def log_http_errors(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled inference exception for %s %s", request.method, request.url.path
        )
        raise

    if response.status_code >= 400:
        response_body = await _read_response_body(response)
        logger.error(
            "Inference HTTP error %s %s -> %s: %s",
            request.method,
            request.url.path,
            response.status_code,
            _response_error_detail(response_body),
        )

    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(providers.router)
app.include_router(exams.router)
app.include_router(batch.router)
