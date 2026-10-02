"""Ollama client (https://github.com/ollama/ollama/blob/main/docs/api.md)."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import httpx

from .base import EngineError, ModelInfo, ProgressCallback, RuntimeStatus, check_response, guess_vision, send

LABEL = "Ollama"


class OllamaEngine:
    kind = "ollama"

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 300,
        transport: httpx.AsyncBaseTransport | None = None,
        num_ctx: int = 8192,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.num_ctx = num_ctx
        # trust_env=False: never route local runtime traffic through system HTTP proxies.
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=5.0),
            transport=transport,
            trust_env=False,
        )
        self._capabilities: dict[tuple[str, str], bool | None] = {}

    async def aclose(self) -> None:
        await self._client.aclose()

    async def version(self) -> str:
        response = await send(LABEL, self.base_url, lambda: self._client.get("/api/version", timeout=5.0))
        data = response.json()
        return str(data.get("version", "")) if isinstance(data, dict) else ""

    async def list_models(self) -> list[ModelInfo]:
        response = await send(LABEL, self.base_url, lambda: self._client.get("/api/tags", timeout=10.0))
        payload = response.json()
        models: list[ModelInfo] = []
        digests: dict[str, str] = {}
        for raw in payload.get("models", []) if isinstance(payload, dict) else []:
            name = raw.get("name") or raw.get("model")
            if not name:
                continue
            details = raw.get("details") or {}
            models.append(
                ModelInfo(
                    name=name,
                    size=raw.get("size"),
                    family=details.get("family") or "",
                    parameters=details.get("parameter_size") or "",
                    quantization=details.get("quantization_level") or "",
                    families=list(details.get("families") or []),
                )
            )
            digests[name] = raw.get("digest") or ""
        semaphore = asyncio.Semaphore(4)

        async def fill(model: ModelInfo) -> None:
            async with semaphore:
                model.vision = await self._has_vision(model, digests.get(model.name, ""))

        await asyncio.gather(*(fill(m) for m in models))
        models.sort(key=lambda m: (m.vision is False, m.name))
        return models

    async def _has_vision(self, model: ModelInfo, digest: str) -> bool | None:
        cache_key = (model.name, digest)
        if cache_key in self._capabilities:
            return self._capabilities[cache_key]
        result: bool | None
        try:
            response = await send(
                LABEL,
                self.base_url,
                lambda: self._client.post(
                    "/api/show", json={"model": model.name, "name": model.name}, timeout=10.0
                ),
            )
            data = response.json()
            capabilities = data.get("capabilities") if isinstance(data, dict) else None
            if isinstance(capabilities, list):
                result = "vision" in capabilities
            elif isinstance(data, dict) and data.get("projector_info"):
                result = True
            else:
                result = None
        except EngineError:
            result = None
        if result is None:
            families = {f.lower() for f in model.families}
            if families & {"clip", "mllama"} or guess_vision(model.name):
                result = True
        self._capabilities[cache_key] = result
        return result

    async def status(self) -> RuntimeStatus:
        status = RuntimeStatus(kind=self.kind, url=self.base_url, reachable=False)
        try:
            status.version = await self.version()
            status.reachable = True
            status.models = await self.list_models()
        except EngineError as exc:
            status.error = exc
        return status

    async def complete(self, *, model: str, prompt: str, image_jpeg: bytes, schema: dict | None) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [base64.b64encode(image_jpeg).decode("ascii")],
                }
            ],
            "options": {"temperature": 0, "num_ctx": self.num_ctx},
            "keep_alive": "10m",
        }
        if schema is not None:
            payload["format"] = schema
        response = await send(LABEL, self.base_url, lambda: self._client.post("/api/chat", json=payload))
        try:
            data = response.json()
        except ValueError as exc:
            raise EngineError("bad_response", "Ollama returned an invalid response.") from exc
        message = data.get("message") if isinstance(data, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise EngineError("bad_response", "Ollama returned no text.")
        return content

    async def pull(self, model: str, progress: ProgressCallback) -> None:
        body = {"model": model, "name": model, "stream": True}
        try:
            async with self._client.stream(
                "POST", "/api/pull", json=body, timeout=httpx.Timeout(None, connect=5.0)
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    check_response(LABEL, response)
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get("error"):
                        raise EngineError("runtime_error", str(event["error"]))
                    progress(str(event.get("status", "")), event.get("completed"), event.get("total"))
        except httpx.TimeoutException as exc:
            raise EngineError("timeout", "Ollama did not answer in time.") from exc
        except httpx.ConnectError as exc:
            raise EngineError("unreachable", f"Ollama is not reachable at {self.base_url}.") from exc
        except httpx.HTTPError as exc:
            raise EngineError("unreachable", f"Ollama connection failed: {exc}") from exc
