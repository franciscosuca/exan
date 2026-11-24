from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from exan_sidecar import cli
from exan_sidecar.downloads import DownloadError, download_file, part_path
from exan_sidecar.engine import model_store as model_store_module
from exan_sidecar.engine.base import EngineError
from exan_sidecar.engine.builtin_catalog import (
    CatalogError,
    ModelFile,
    catalog,
    get_model,
    parse_catalog,
    recommended_model,
)
from exan_sidecar.engine.llamacpp import BuiltinEngine, LlamaServer
from exan_sidecar.engine.model_store import ModelStore
from exan_sidecar.state import AppState

from .conftest import FakeEngine, jpeg_bytes, wait_for

pytestmark = pytest.mark.anyio

FAKE_SERVER = Path(__file__).with_name("fake_llama_server.py")
FIXTURES = Path(__file__).with_name("fixtures")


# -- catalog ------------------------------------------------------------------------------------


def test_catalog_lists_pinned_models_and_recommends_the_smallest() -> None:
    models = catalog()
    assert [m.id for m in models] == ["granite-docling-258m", "paddleocr-vl-1.6", "qwen2.5-vl-3b"]
    smallest = min(models, key=lambda m: m.download_bytes)
    assert recommended_model() is smallest and smallest.id == "granite-docling-258m"
    for model in models:
        assert {f.role for f in model.files} == {"model", "mmproj"}
        assert all(
            f.url.startswith("https://huggingface.co/") and f"/resolve/{f.revision}/" in f.url
            for f in model.files
        )
        assert model.notes.keys() >= {"en", "de"} and model.summary.keys() >= {"en", "de"}
        assert all(len(text) <= 70 for text in model.summary.values())  # one line on the installer page
        view = model.view()
        assert view["download_bytes"] == sum(f.size for f in model.files)
    assert get_model("qwen2.5-vl-3b").mode == "structured"
    assert get_model("paddleocr-vl-1.6").prompt == "OCR:"
    assert get_model("nope") is None


def test_catalog_rejects_bad_entries() -> None:
    raw = json.loads((Path(__file__).parents[1] / "exan_sidecar" / "engine" / "models.json").read_text())
    broken = json.loads(json.dumps(raw))
    broken["models"][0]["files"][0]["sha256"] = "abc"
    with pytest.raises(CatalogError, match="checksum"):
        parse_catalog(broken)
    twice = json.loads(json.dumps(raw))
    twice["models"][1]["recommended"] = True
    with pytest.raises(CatalogError, match="recommended"):
        parse_catalog(twice)


# -- downloads ----------------------------------------------------------------------------------

CONTENT = os.urandom(300_000)
DIGEST = hashlib.sha256(CONTENT).hexdigest()


def serving(
    content: bytes = CONTENT, *, honour_range: bool = True, status: int = 200, log: list | None = None
):
    def handler(request: httpx.Request) -> httpx.Response:
        if log is not None:
            log.append(request.headers.get("range"))
        if status != 200:
            return httpx.Response(status)
        requested = request.headers.get("range")
        if requested and honour_range:
            start = int(requested.split("=")[1].rstrip("-"))
            return httpx.Response(206, content=content[start:])
        return httpx.Response(200, content=content)

    return httpx.MockTransport(handler)


async def fetch(transport: httpx.MockTransport, target: Path, **kwargs) -> list[int]:
    seen: list[int] = []
    async with httpx.AsyncClient(transport=transport) as client:
        await download_file(
            client,
            "https://huggingface.co/x/y/resolve/r/f.gguf",
            target,
            size=kwargs.pop("size", len(CONTENT)),
            sha256=kwargs.pop("sha256", DIGEST),
            on_progress=seen.append,
        )
    return seen


async def test_download_verifies_and_renames(tmp_path: Path) -> None:
    target = tmp_path / "m" / "model.gguf"
    seen = await fetch(serving(), target)
    assert target.read_bytes() == CONTENT and not part_path(target).exists()
    assert seen[-1] == len(CONTENT) and seen == sorted(seen)
    # A complete file is not downloaded again.
    requests: list = []
    await fetch(serving(log=requests), target)
    assert requests == []


async def test_download_resumes_a_partial_file(tmp_path: Path) -> None:
    target = tmp_path / "model.gguf"
    part_path(target).write_bytes(CONTENT[:120_000])
    requests: list = []
    await fetch(serving(log=requests), target)
    assert requests == ["bytes=120000-"]
    assert target.read_bytes() == CONTENT


async def test_download_restarts_when_range_is_ignored(tmp_path: Path) -> None:
    target = tmp_path / "model.gguf"
    part_path(target).write_bytes(CONTENT[:50_000])
    await fetch(serving(honour_range=False), target)
    assert target.read_bytes() == CONTENT


async def test_download_rejects_damaged_or_wrong_files(tmp_path: Path) -> None:
    target = tmp_path / "model.gguf"
    with pytest.raises(DownloadError) as damaged:
        await fetch(serving(CONTENT[:-1] + b"x"), target)
    assert damaged.value.code == "download_corrupt"
    assert not target.exists() and not part_path(target).exists()
    with pytest.raises(DownloadError) as too_big:
        await fetch(serving(CONTENT + b"extra"), target)
    assert too_big.value.code == "download_corrupt"
    with pytest.raises(DownloadError) as http_error:
        await fetch(serving(status=503), target)
    assert http_error.value.code == "download_failed" and "503" in http_error.value.message


async def test_download_reports_network_errors(tmp_path: Path) -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(DownloadError) as error:
        await fetch(httpx.MockTransport(broken), tmp_path / "model.gguf")
    assert error.value.code == "download_failed"


# -- model store --------------------------------------------------------------------------------


def tiny_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The recommended model with its files replaced by small in-memory ones."""
    import dataclasses

    model = recommended_model()
    payloads = {"model": CONTENT[:200_000], "mmproj": CONTENT[200_000:]}
    files = tuple(
        dataclasses.replace(
            f, size=len(payloads[f.role]), sha256=hashlib.sha256(payloads[f.role]).hexdigest()
        )
        for f in model.files
    )
    small = dataclasses.replace(model, files=files)

    def handler(request: httpx.Request) -> httpx.Response:
        role = "mmproj" if "mmproj" in request.url.path else "model"
        return httpx.Response(200, content=payloads[role])

    monkeypatch.setattr(
        model_store_module,
        "new_client",
        lambda transport=None: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    return small


async def test_store_downloads_both_files_with_overall_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tiny_model(tmp_path, monkeypatch)
    store = ModelStore(tmp_path / "models")
    assert not store.is_installed(model) and store.downloaded_bytes(model) == 0
    events: list[tuple[str, int | None, int | None]] = []
    await store.download(model, lambda status, done, total: events.append((status, done, total)))
    assert store.is_installed(model)
    assert events[-1] == ("success", model.download_bytes, model.download_bytes)
    progress = [done for status, done, _ in events if status == "downloading"]
    assert progress == sorted(progress) and max(progress) == model.download_bytes
    assert sorted(p.name for p in store.model_dir(model).iterdir()) == sorted(f.path for f in model.files)
    store.delete(model)
    assert not store.model_dir(model).exists()


async def test_store_refuses_when_the_disk_is_full(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    model = tiny_model(tmp_path, monkeypatch)
    monkeypatch.setattr(shutil, "disk_usage", lambda _path: shutil._ntuple_diskusage(100, 100, 10))
    with pytest.raises(DownloadError) as error:
        await ModelStore(tmp_path / "models").download(model, lambda *_: None)
    assert error.value.code == "disk_full"


def install_sparse(store: ModelStore, model_id: str) -> None:
    """Pretend a model is installed: files with the expected sizes (sparse, so they take no space)."""
    model = get_model(model_id)
    for item in model.files:
        path = store.paths(model)[item.role]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            handle.truncate(item.size)


# -- llama-server process ------------------------------------------------------------------------


def fake_server(tmp_path: Path, **kwargs) -> LlamaServer:
    return LlamaServer(
        None, tmp_path / "logs", tmp_path / "data", command=[sys.executable, str(FAKE_SERVER)], **kwargs
    )


async def test_engine_starts_the_runtime_and_reads_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "requests.jsonl"
    monkeypatch.setenv("FAKE_LLAMA_LOG", str(log))
    store = ModelStore(tmp_path / "models")
    install_sparse(store, "granite-docling-258m")
    install_sparse(store, "paddleocr-vl-1.6")
    server = fake_server(tmp_path)
    engine = BuiltinEngine(store, server, timeout=30)
    try:
        status = await engine.status()
        assert status.reachable and {m.name for m in status.models} == {
            "granite-docling-258m",
            "paddleocr-vl-1.6",
        }
        assert status.view()["can_pull"] is True

        text = await engine.complete(model="granite-docling-258m", prompt="p", image_jpeg=b"jpg", schema=None)
        assert text == "1. B\n2. C"
        first_pid = server._process.pid
        assert server.model_id == "granite-docling-258m"
        assert json.loads(server.pid_file.read_text())["pid"] == server._process.pid
        assert "--api-key" not in server._process.args  # the key travels in LLAMA_API_KEY

        await engine.complete(model="paddleocr-vl-1.6", prompt="OCR:", image_jpeg=b"jpg", schema=None)
        assert server.model_id == "paddleocr-vl-1.6"
        assert (
            server._process.pid != first_pid
        )  # a new server process for the new model (the port may repeat)

        requests = [json.loads(line) for line in log.read_text().splitlines()]
        granite, paddle = requests
        assert granite["alias"] == "granite-docling-258m" and granite["dry_multiplier"] == 0.8
        assert granite["max_tokens"] == 2048 and granite["temperature"] == 0
        assert granite["messages"][0]["content"][0]["type"] == "image_url"
        assert paddle["model_path"].endswith("PaddleOCR-VL-1.6-GGUF.gguf") and "dry_multiplier" not in paddle
    finally:
        await engine.aclose()
    assert server.model_id is None and not server.pid_file.exists()


async def test_engine_explains_missing_models_and_runtime(tmp_path: Path) -> None:
    store = ModelStore(tmp_path / "models")
    engine = BuiltinEngine(store, LlamaServer(None, tmp_path, tmp_path), timeout=30)
    status = await engine.status()
    assert not status.reachable and status.error.code == "runtime_missing"
    with pytest.raises(EngineError) as missing:
        await engine.complete(model="granite-docling-258m", prompt="p", image_jpeg=b"", schema=None)
    assert missing.value.code == "model_missing"
    with pytest.raises(EngineError) as unknown:
        await engine.complete(model="llava:7b", prompt="p", image_jpeg=b"", schema=None)
    assert unknown.value.code == "model_missing"
    install_sparse(store, "granite-docling-258m")
    with pytest.raises(EngineError) as no_runtime:
        await engine.complete(model="granite-docling-258m", prompt="p", image_jpeg=b"", schema=None)
    assert no_runtime.value.code == "runtime_missing"


async def test_runtime_that_crashes_while_loading_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_LLAMA_MODE", "crash")
    store = ModelStore(tmp_path / "models")
    install_sparse(store, "granite-docling-258m")
    server = fake_server(tmp_path)
    with pytest.raises(EngineError) as error:
        await BuiltinEngine(store, server).complete(
            model="granite-docling-258m", prompt="p", image_jpeg=b"", schema=None
        )
    assert error.value.code == "runtime_failed"
    assert "out of memory" in error.value.message
    assert server.model_id is None


def test_stale_pid_file_never_stops_unrelated_processes(tmp_path: Path) -> None:
    server = fake_server(tmp_path)
    server.pid_file.parent.mkdir(parents=True)
    server.pid_file.write_text(json.dumps({"pid": os.getpid()}))  # the test runner is not a llama-server
    server.cleanup_stale()
    assert not server.pid_file.exists()  # forgotten, and we are still alive


def test_runtime_binary_and_version_come_from_the_runtime_folder(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    server = LlamaServer(runtime, tmp_path, tmp_path)
    assert not server.available and server.version is None
    (runtime / ("llama-server.exe" if sys.platform == "win32" else "llama-server")).write_bytes(b"")
    (runtime / "VERSION").write_text("b11376\n")
    assert server.available and server.version == "b11376"


# -- reading pages and the API -------------------------------------------------------------------


def test_builtin_models_use_their_own_prompt_mode_and_image_size(
    client: TestClient, state: AppState, engine: FakeEngine
) -> None:
    client.put("/api/settings", json={"runtime": "builtin", "model": "granite-docling-258m"})
    engine.default = (FIXTURES / "ocr-granite-anna.txt").read_text(encoding="utf-8")
    client.post("/api/participants", files=[("files", ("a.jpg", jpeg_bytes(2400, 3200), "image/jpeg"))])
    session = wait_for(client, lambda s: s["participants"] and s["participants"][0]["status"] == "done")
    call = engine.calls[-1]
    assert call["prompt"] == "Convert this page to docling." and call["schema"] is None
    assert max(call["size"]) == 2048
    participant = session["participants"][0]
    assert participant["name"] == "Anna Schmiadt"
    assert [a["answer"] for a in participant["answers"]] == [
        "B",
        "C, A",
        "richtig",
        "0.7",
        "Fotosynthese",
        "Paris",
    ]

    client.put("/api/settings", json={"model": "qwen2.5-vl-3b"})
    engine.default = '{"name": "Kim", "answers": [{"question": "1", "answer": "B"}]}'
    client.post(f"/api/participants/{participant['id']}/extract")
    wait_for(client, lambda s: s["participants"][0]["name"] == "Kim")
    assert engine.calls[-1]["schema"] is not None and max(engine.calls[-1]["size"]) == 1600

    client.put("/api/settings", json={"model": "llava:7b"})
    client.post(f"/api/participants/{participant['id']}/extract")
    failed = wait_for(client, lambda s: s["participants"][0]["status"] == "error")
    assert failed["participants"][0]["error"]["code"] == "model_missing"


def test_models_endpoint_download_and_delete(client: TestClient, state: AppState) -> None:
    client.put("/api/settings", json={"runtime": "builtin", "model": ""})
    models = client.get("/api/models").json()
    assert [m["id"] for m in models] == [m.id for m in catalog()]
    assert [m["recommended"] for m in models] == [True, False, False]
    assert not any(m["installed"] for m in models)
    assert models[2]["license"].startswith("Qwen Research License")

    assert client.post("/api/runtime/pull", json={"model": "llava:7b"}).json()["code"] == "invalid_model"
    started = client.post("/api/runtime/pull", json={"model": "granite-docling-258m"})
    assert started.status_code == 200 and started.json()["model"] == "granite-docling-258m"

    install_sparse(state.models, "granite-docling-258m")
    for _ in range(100):
        if not state.pull.running:
            break
        time.sleep(0.02)
    assert client.get("/api/models").json()[0]["installed"] is True
    after = client.delete("/api/models/granite-docling-258m").json()
    assert (
        after[0]["installed"] is False
        and not state.models.model_dir(get_model("granite-docling-258m")).exists()
    )
    assert client.delete("/api/models/llava").status_code == 404


def test_settings_default_to_the_builtin_runtime(tmp_path: Path) -> None:
    from .conftest import make_config

    state = AppState(make_config(tmp_path))
    assert state.settings.get().runtime == "builtin"
    assert state.config.model_root == tmp_path / "data" / "models"
    assert isinstance(state.engine(), BuiltinEngine)


# -- command line (used by the Windows installer) -----------------------------------------------


def test_cli_lists_models(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from exan_sidecar.__main__ import main

    assert main(["models", "list", "--json", "--models-dir", str(tmp_path)]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["id"] == "granite-docling-258m" and rows[0]["installed"] is False
    assert main(["models", "list", "--models-dir", str(tmp_path)]) == 0
    assert "(recommended)" in capsys.readouterr().out


def test_cli_downloads_and_selects_a_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from exan_sidecar.__main__ import main

    small = tiny_model(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "get_model", lambda model_id: small if model_id == small.id else None)
    code = main(
        [
            "models",
            "download",
            small.id,
            "--models-dir",
            str(tmp_path / "models"),
            "--select",
            "--data-dir",
            str(tmp_path / "data"),
            "--lang",
            "de",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "wird von huggingface.co heruntergeladen" in out and "100 %" in out and "ist bereit" in out
    settings = json.loads((tmp_path / "data" / "settings.json").read_text())
    assert settings["runtime"] == "builtin" and settings["model"] == small.id

    assert main(["models", "download", "nope", "--models-dir", str(tmp_path)]) == 2
    assert "granite-docling-258m" in capsys.readouterr().err


def test_cli_reports_failed_downloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from exan_sidecar.__main__ import main

    def offline(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(
        model_store_module,
        "new_client",
        lambda transport=None: httpx.AsyncClient(transport=httpx.MockTransport(offline)),
    )
    data = tmp_path / "data"
    args = [
        "models",
        "download",
        "granite-docling-258m",
        "--models-dir",
        str(tmp_path),
        "--select",
        "--data-dir",
        str(data),
    ]
    assert main(args) == 1
    assert "failed" in capsys.readouterr().err
    # The choice is kept, so the app offers exactly this model again.
    assert json.loads((data / "settings.json").read_text())["model"] == "granite-docling-258m"


def test_model_file_url_is_pinned() -> None:
    item = ModelFile("model", "org/repo", "a" * 40, "m.gguf", 1, "b" * 64)
    assert item.url == f"https://huggingface.co/org/repo/resolve/{'a' * 40}/m.gguf"
