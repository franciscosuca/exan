from __future__ import annotations

import base64
import json

import httpx
import pytest

from exan_sidecar.engine.base import EngineError, create_engine
from exan_sidecar.engine.catalog import OCR, STRUCTURED, catalog_view, resolve_mode
from exan_sidecar.engine.ollama import OllamaEngine
from exan_sidecar.engine.openai_compat import OpenAICompatEngine
from exan_sidecar.engine.prompts import ANSWER_SCHEMA, ocr_prompt, participant_prompt

pytestmark = pytest.mark.anyio

IMAGE = b"\xff\xd8\xff fake jpeg"


def ollama_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/api/version":
        return httpx.Response(200, json={"version": "0.12.9"})
    if path == "/api/tags":
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "qwen2.5vl:3b",
                        "size": 3_200_000_000,
                        "digest": "a",
                        "details": {"family": "qwen25vl"},
                    },
                    {
                        "name": "llama3.2:3b",
                        "size": 2_000_000_000,
                        "digest": "b",
                        "details": {"family": "llama"},
                    },
                    {
                        "name": "old-llava:7b",
                        "size": 4_000_000_000,
                        "digest": "c",
                        "details": {"families": ["llama", "clip"]},
                    },
                ]
            },
        )
    if path == "/api/show":
        name = json.loads(request.content)["model"]
        if name == "qwen2.5vl:3b":
            return httpx.Response(200, json={"capabilities": ["completion", "vision"]})
        if name == "llama3.2:3b":
            return httpx.Response(200, json={"capabilities": ["completion", "tools"]})
        return httpx.Response(500, json={"error": "boom"})
    if path == "/api/chat":
        body = json.loads(request.content)
        assert body["stream"] is False
        assert body["options"]["temperature"] == 0
        assert base64.b64decode(body["messages"][0]["images"][0]) == IMAGE
        if body["model"] == "missing:1b":
            return httpx.Response(404, json={"error": "model 'missing:1b' not found, try pulling it first"})
        content = (
            json.dumps({"name": "", "answers": [{"question": "1", "answer": "B"}]})
            if "format" in body
            else "1. B"
        )
        return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})
    if path == "/api/pull":
        lines = [
            {"status": "pulling manifest"},
            {"status": "downloading", "completed": 50, "total": 100},
            {"status": "downloading", "completed": 100, "total": 100},
            {"status": "success"},
        ]
        return httpx.Response(200, content="\n".join(json.dumps(line) for line in lines).encode())
    return httpx.Response(404, text="404 page not found")


async def test_ollama_status_and_vision_detection() -> None:
    engine = OllamaEngine("http://ollama.test", transport=httpx.MockTransport(ollama_handler))
    status = await engine.status()
    await engine.aclose()
    assert status.reachable and status.version == "0.12.9"
    vision = {m.name: m.vision for m in status.models}
    assert vision == {"qwen2.5vl:3b": True, "llama3.2:3b": False, "old-llava:7b": True}
    assert status.view()["can_pull"] is True
    assert status.models[-1].name == "llama3.2:3b"  # non-vision models are listed last


async def test_ollama_complete_structured_and_plain() -> None:
    engine = OllamaEngine("http://ollama.test", transport=httpx.MockTransport(ollama_handler))
    structured = await engine.complete(
        model="qwen2.5vl:3b", prompt="p", image_jpeg=IMAGE, schema=ANSWER_SCHEMA
    )
    plain = await engine.complete(model="qwen2.5vl:3b", prompt="p", image_jpeg=IMAGE, schema=None)
    assert json.loads(structured)["answers"][0]["answer"] == "B"
    assert plain == "1. B"
    with pytest.raises(EngineError) as error:
        await engine.complete(model="missing:1b", prompt="p", image_jpeg=IMAGE, schema=None)
    assert error.value.code == "model_missing"
    await engine.aclose()


async def test_ollama_pull_reports_progress() -> None:
    engine = OllamaEngine("http://ollama.test", transport=httpx.MockTransport(ollama_handler))
    events: list[tuple[str, int | None, int | None]] = []
    await engine.pull("qwen2.5vl:3b", lambda *event: events.append(event))
    await engine.aclose()
    assert events[0] == ("pulling manifest", None, None)
    assert ("downloading", 100, 100) in events
    assert events[-1][0] == "success"


async def test_ollama_pull_error_line() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b'{"status":"pulling manifest"}\n{"error":"pull model manifest: file does not exist"}\n',
        )

    engine = OllamaEngine("http://ollama.test", transport=httpx.MockTransport(handler))
    with pytest.raises(EngineError) as error:
        await engine.pull("nope:1b", lambda *event: None)
    await engine.aclose()
    assert "does not exist" in error.value.message


async def test_unreachable_runtime_is_reported_not_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    engine = OllamaEngine("http://127.0.0.1:9", transport=httpx.MockTransport(handler))
    status = await engine.status()
    assert status.reachable is False
    assert status.error is not None and status.error.code == "unreachable"
    with pytest.raises(EngineError) as error:
        await engine.complete(model="x", prompt="p", image_jpeg=IMAGE, schema=None)
    assert error.value.code == "unreachable"
    await engine.aclose()


async def test_wrong_server_address_gives_helpful_error() -> None:
    engine = OllamaEngine("http://ollama.test/wrong", transport=httpx.MockTransport(ollama_handler))
    with pytest.raises(EngineError) as error:
        await engine.complete(model="qwen2.5vl:3b", prompt="p", image_jpeg=IMAGE, schema=None)
    assert error.value.code == "runtime_error"
    assert "server address" in error.value.message
    await engine.aclose()


async def test_openai_compatible_with_schema_fallback() -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(
                200, json={"data": [{"id": "qwen2.5-vl-3b-instruct"}, {"id": "text-embedding-nomic"}]}
            )
        body = json.loads(request.content)
        seen.append(body)
        image = body["messages"][0]["content"][0]["image_url"]["url"]
        assert image.startswith("data:image/jpeg;base64,")
        assert body["messages"][0]["content"][1] == {"type": "text", "text": "p"}
        if "response_format" in body:
            return httpx.Response(400, json={"error": {"message": "response_format is not supported"}})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": [{"type": "text", "text": "1. C"}]}}]}
        )

    engine = OpenAICompatEngine("http://lmstudio.test/v1", transport=httpx.MockTransport(handler))
    status = await engine.status()
    assert status.reachable and status.models[0].name == "qwen2.5-vl-3b-instruct" and status.models[0].vision
    assert status.view()["can_pull"] is False
    first = await engine.complete(
        model="qwen2.5-vl-3b-instruct", prompt="p", image_jpeg=IMAGE, schema=ANSWER_SCHEMA
    )
    second = await engine.complete(
        model="qwen2.5-vl-3b-instruct", prompt="p", image_jpeg=IMAGE, schema=ANSWER_SCHEMA
    )
    assert first == second == "1. C"
    assert ["response_format" in body for body in seen] == [True, False, False]
    with pytest.raises(EngineError) as error:
        await engine.pull("x", lambda *event: None)
    assert error.value.code == "unsupported"
    await engine.aclose()


def test_create_engine_kinds() -> None:
    assert isinstance(create_engine("ollama", "http://127.0.0.1:11434", 30), OllamaEngine)
    assert isinstance(create_engine("openai", "http://127.0.0.1:1234/v1", 30), OpenAICompatEngine)


def test_catalog_and_modes() -> None:
    names = [entry["name"] for entry in catalog_view()]
    assert names[0] == "qwen2.5vl:3b"
    assert sum(1 for entry in catalog_view() if entry["recommended"]) == 1
    assert resolve_mode("auto", "deepseek-ocr:3b") == OCR
    assert resolve_mode("auto", "qwen2.5vl:7b-q8_0") == STRUCTURED
    assert resolve_mode("auto", "ibm/granite-docling:258m") == OCR
    assert resolve_mode("auto", "some-new-vl:2b") == STRUCTURED
    assert resolve_mode("ocr", "qwen2.5vl:3b") == OCR


def test_prompts() -> None:
    assert ocr_prompt("deepseek-ocr:3b") == "Free OCR."
    assert "docling" in ocr_prompt("granite-docling:258m")
    assert "1, 2, 3a" in participant_prompt(["1", "2", "3a"])
    assert "These questions" not in participant_prompt([])
