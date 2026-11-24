"""Shared types for runtime clients."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

ProgressCallback = Callable[[str, int | None, int | None], None]

# Name fragments of models that are known to accept images.
_VISION_HINTS = (
    "vl",
    "vision",
    "llava",
    "bakllava",
    "moondream",
    "minicpm-v",
    "gemma3",
    "gemma4",
    "ocr",
    "docling",
    "pixtral",
    "mistral-small3",
    "llama4",
    "internvl",
    "smolvlm",
    "phi4-multimodal",
    "phi-4-multimodal",
)


def guess_vision(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _VISION_HINTS)


class EngineError(Exception):
    """A user-facing runtime problem. `code` is stable and translated by the UI."""

    def __init__(self, code: str, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status

    def view(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


@dataclass
class ModelInfo:
    name: str
    size: int | None = None
    vision: bool | None = None
    family: str = ""
    parameters: str = ""
    quantization: str = ""
    families: list[str] = field(default_factory=list)

    def view(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "size": self.size,
            "vision": self.vision,
            "family": self.family,
            "parameters": self.parameters,
            "quantization": self.quantization,
        }


@dataclass
class RuntimeStatus:
    kind: str
    url: str
    reachable: bool
    version: str | None = None
    models: list[ModelInfo] = field(default_factory=list)
    error: EngineError | None = None

    def view(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "url": self.url,
            "reachable": self.reachable,
            "version": self.version,
            "models": [m.view() for m in self.models],
            "error": self.error.view() if self.error else None,
            "can_pull": self.kind in ("ollama", "builtin"),
        }


class VisionEngine(Protocol):
    kind: str
    base_url: str

    async def status(self) -> RuntimeStatus: ...

    async def complete(self, *, model: str, prompt: str, image_jpeg: bytes, schema: dict | None) -> str: ...

    async def pull(self, model: str, progress: ProgressCallback) -> None: ...

    async def aclose(self) -> None: ...


def error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        text = response.text.strip()
        return text[:300] or f"HTTP {response.status_code}"
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)[:300]
        if error:
            return str(error)[:300]
        if payload.get("detail"):
            return str(payload["detail"])[:300]
    return f"HTTP {response.status_code}"


async def send(label: str, base_url: str, call: Callable[[], Awaitable[httpx.Response]]) -> httpx.Response:
    """Run an HTTP call and translate transport problems into EngineError."""
    try:
        response = await call()
    except httpx.TimeoutException as exc:
        raise EngineError("timeout", f"{label} did not answer in time.") from exc
    except httpx.ConnectError as exc:
        raise EngineError("unreachable", f"{label} is not reachable at {base_url}.") from exc
    except httpx.HTTPError as exc:
        raise EngineError("unreachable", f"{label} connection failed: {exc}") from exc
    return check_response(label, response)


def check_response(label: str, response: httpx.Response) -> httpx.Response:
    """Raise EngineError for HTTP error responses (the body must already be read)."""
    if response.status_code < 400:
        return response
    message = error_message(response)
    if response.status_code == 404 and "model" in message.lower():
        raise EngineError("model_missing", message, response.status_code)
    if response.status_code == 404:
        raise EngineError("runtime_error", f"{label}: {message} (check the server address)", 404)
    raise EngineError("runtime_error", message, response.status_code)


def create_engine(
    kind: str, base_url: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None
):
    from .ollama import OllamaEngine
    from .openai_compat import OpenAICompatEngine

    if kind == "openai":
        return OpenAICompatEngine(base_url, timeout=timeout, transport=transport)
    return OllamaEngine(base_url, timeout=timeout, transport=transport)
