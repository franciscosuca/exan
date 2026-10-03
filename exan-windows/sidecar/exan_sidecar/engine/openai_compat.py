"""Client for OpenAI-compatible local servers (LM Studio, llama.cpp server, MLX, vLLM, ...)."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from .base import EngineError, ModelInfo, ProgressCallback, RuntimeStatus, guess_vision, send

LABEL = "The local model server"


class OpenAICompatEngine:
    kind = "openai"

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 300,
        transport: httpx.AsyncBaseTransport | None = None,
        max_tokens: int = 4096,
        api_key: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.options = dict(options or {})
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=5.0),
            transport=transport,
            trust_env=False,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else None,
        )
        self._schema_unsupported: set[str] = set()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_models(self) -> list[ModelInfo]:
        response = await send(LABEL, self.base_url, lambda: self._client.get("/models", timeout=10.0))
        try:
            payload = response.json()
        except ValueError as exc:
            raise EngineError("bad_response", "The server did not return a model list.") from exc
        entries = payload.get("data", []) if isinstance(payload, dict) else []
        models = [
            ModelInfo(name=str(entry["id"]), vision=True if guess_vision(str(entry["id"])) else None)
            for entry in entries
            if isinstance(entry, dict) and entry.get("id")
        ]
        models.sort(key=lambda m: (m.vision is not True, m.name))
        return models

    async def status(self) -> RuntimeStatus:
        status = RuntimeStatus(kind=self.kind, url=self.base_url, reachable=False)
        try:
            status.models = await self.list_models()
            status.reachable = True
        except EngineError as exc:
            status.error = exc
        return status

    async def complete(self, *, model: str, prompt: str, image_jpeg: bytes, schema: dict | None) -> str:
        image_url = "data:image/jpeg;base64," + base64.b64encode(image_jpeg).decode("ascii")
        payload: dict[str, Any] = {
            **self.options,
            "model": model,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    # Image first: OCR models are trained on "<image> prompt" and read worse otherwise.
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        if schema is not None and model not in self._schema_unsupported:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "exam_answers", "schema": schema},
            }
            try:
                return await self._chat(payload)
            except EngineError as exc:
                if exc.status not in (400, 422, 500, 501):
                    raise
                # Some servers reject structured output; retry with the plain prompt.
                self._schema_unsupported.add(model)
                payload.pop("response_format", None)
        return await self._chat(payload)

    async def _chat(self, payload: dict[str, Any]) -> str:
        response = await send(
            LABEL, self.base_url, lambda: self._client.post("/chat/completions", json=payload)
        )
        try:
            data = response.json()
            message = data["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise EngineError("bad_response", "The server returned an invalid response.") from exc
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str):
            raise EngineError("bad_response", "The server returned no text.")
        return content

    async def pull(self, model: str, progress: ProgressCallback) -> None:
        raise EngineError("unsupported", "Download models in the model server app (for example LM Studio).")
