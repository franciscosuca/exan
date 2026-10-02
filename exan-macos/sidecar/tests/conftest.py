from __future__ import annotations

import asyncio
import io
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from exan_sidecar.api import create_app
from exan_sidecar.config import DEFAULT_CORS_ORIGINS, RuntimeConfig
from exan_sidecar.engine.base import ModelInfo, RuntimeStatus
from exan_sidecar.state import AppState

SECRET = "test-secret-0123456789abcdef"
AUTH = {"Authorization": "Bearer " + SECRET}


def jpeg_bytes(
    width: int = 640, height: int = 800, color: tuple[int, int, int] = (250, 250, 250), **save: Any
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG", **save)
    return buffer.getvalue()


def image_size(jpeg: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(jpeg)) as image:
        return image.size


class FakeEngine:
    """Vision engine double: answers are looked up by the size of the image it receives."""

    kind = "ollama"
    base_url = "http://fake-runtime"

    def __init__(
        self, responses: dict[tuple[int, int], Any] | None = None, default: Any = "{}", delay: float = 0.0
    ):
        self.responses = responses or {}
        self.default = default
        self.delay = delay
        self.calls: list[dict[str, Any]] = []
        self.closed = False
        self.models = [ModelInfo(name="qwen2.5vl:3b", vision=True), ModelInfo(name="llama3:8b", vision=False)]

    async def status(self) -> RuntimeStatus:
        return RuntimeStatus(
            kind=self.kind, url=self.base_url, reachable=True, version="0.12.9", models=self.models
        )

    async def complete(self, *, model: str, prompt: str, image_jpeg: bytes, schema: dict | None) -> str:
        size = image_size(image_jpeg)
        self.calls.append({"model": model, "prompt": prompt, "size": size, "schema": schema})
        if self.delay:
            await asyncio.sleep(self.delay)
        response = self.responses.get(size, self.default)
        if callable(response):
            response = response(prompt, schema)
        if isinstance(response, Exception):
            raise response
        return response

    async def pull(self, model: str, progress: Callable[[str, int | None, int | None], None]) -> None:
        for done in range(3):
            progress("downloading", done, 2)
            await asyncio.sleep(0.01)

    async def aclose(self) -> None:
        self.closed = True


def make_config(tmp_path: Path) -> RuntimeConfig:
    return RuntimeConfig(
        secret=SECRET,
        host="127.0.0.1",
        port=0,
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        cors_origins=DEFAULT_CORS_ORIGINS,
        watch_stdin=False,
    )


@pytest.fixture
def engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def state(tmp_path: Path, engine: FakeEngine) -> AppState:
    app_state = AppState(make_config(tmp_path), engine_factory=lambda kind, url, timeout: engine)
    app_state.settings.update({"model": "qwen2.5vl:3b"})
    return app_state


@pytest.fixture
def client(state: AppState) -> Iterator[TestClient]:
    with TestClient(create_app(state), base_url="http://127.0.0.1", headers=AUTH) as test_client:
        yield test_client


def wait_for(client: TestClient, predicate: Callable[[dict], bool], timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    session: dict = {}
    while time.monotonic() < deadline:
        session = client.get("/api/session").json()
        if predicate(session):
            return session
        time.sleep(0.02)
    raise AssertionError(f"condition not reached; last session: {session}")
