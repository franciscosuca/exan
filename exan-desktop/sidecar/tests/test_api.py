from __future__ import annotations

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from exan_sidecar.api import create_app
from exan_sidecar.engine.base import EngineError
from exan_sidecar.state import AppState

from .conftest import AUTH, SECRET, FakeEngine, jpeg_bytes, wait_for

KEY_SIZE = (600, 800)
ANA_SIZE = (601, 800)
BEN_SIZE = (602, 800)

KEY_JSON = json.dumps(
    {
        "name": "",
        "answers": [
            {"question": "1", "answer": "B"},
            {"question": "2", "answer": "Paris"},
            {"question": "3", "answer": "true"},
        ],
    }
)
ANA_JSON = json.dumps(
    {
        "name": "Ana",
        "answers": [
            {"question": "1", "answer": "b"},
            {"question": "2", "answer": "Paris"},
            {"question": "3", "answer": "wahr"},
        ],
    }
)
BEN_JSON = json.dumps(
    {
        "name": "Ben",
        "answers": [
            {"question": "1", "answer": "C"},
            {"question": "2", "answer": "Pariss"},
            {"question": "3", "answer": ""},
        ],
    }
)


def files(*sizes: tuple[int, int]) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", (f"sheet-{w}.jpg", jpeg_bytes(w, h), "image/jpeg")) for w, h in sizes]


def key_done(session: dict) -> bool:
    return session["key"]["status"] in ("done", "error")


def all_participants_done(session: dict) -> bool:
    return bool(session["participants"]) and all(
        p["status"] in ("done", "error") for p in session["participants"]
    )


@pytest.fixture
def engine() -> FakeEngine:
    return FakeEngine({KEY_SIZE: KEY_JSON, ANA_SIZE: ANA_JSON, BEN_SIZE: BEN_JSON})


# -- security -----------------------------------------------------------------------


def test_requests_need_the_secret(state: AppState) -> None:
    with TestClient(create_app(state), base_url="http://127.0.0.1") as anonymous:
        assert anonymous.get("/api/health").status_code == 401
        wrong = anonymous.get("/api/health", headers={"Authorization": "Bearer " + "not-the-secret"})
        assert wrong.status_code == 401 and wrong.json()["code"] == "unauthorized"
        assert wrong.headers["www-authenticate"] == "Bearer"
        ok = anonymous.get("/api/health", headers=AUTH)
        assert ok.status_code == 200 and ok.json()["status"] == "ok"


def test_foreign_host_header_is_rejected(state: AppState) -> None:
    with TestClient(create_app(state), base_url="http://evil.example", headers=AUTH) as rebinding:
        response = rebinding.get("/api/health")
    assert response.status_code == 400 and response.json()["code"] == "invalid_host"


def test_cors_preflight_and_headers(client: TestClient) -> None:
    preflight = client.options(
        "/api/session",
        headers={
            "Origin": "tauri://localhost",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "tauri://localhost"
    denied = client.options(
        "/api/session", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in denied.headers
    simple = client.get("/api/health", headers={"Origin": "http://tauri.localhost"})
    assert simple.headers["access-control-allow-origin"] == "http://tauri.localhost"


def test_body_requires_content_length(client: TestClient) -> None:
    def chunks():
        yield b'{"language": "en"}'

    response = client.put("/api/settings", content=chunks(), headers={"content-type": "application/json"})
    assert response.status_code == 411


@pytest.mark.anyio
async def test_body_limit_middleware() -> None:
    from exan_sidecar.uploads import BodyLimitMiddleware

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def call(headers: list[tuple[bytes, bytes]], method: str = "POST") -> int:
        sent: list[dict] = []

        async def send(message: dict) -> None:
            sent.append(message)

        async def receive() -> dict:
            return {"type": "http.request", "body": b"", "more_body": False}

        scope = {"type": "http", "method": method, "headers": headers}
        await BodyLimitMiddleware(app, max_bytes=1000)(scope, receive, send)
        return sent[0]["status"]

    assert await call([(b"content-length", b"10")]) == 204
    assert await call([(b"content-length", b"1001")]) == 413
    assert await call([(b"content-length", b"abc")]) == 411
    assert await call([(b"transfer-encoding", b"chunked")]) == 411
    assert await call([]) == 411
    assert await call([], method="GET") == 204


# -- settings & runtime ------------------------------------------------------------------


def test_settings_roundtrip_and_validation(client: TestClient, state: AppState) -> None:
    settings = client.get("/api/settings").json()
    assert settings["runtime"] == "ollama" and settings["model"] == "qwen2.5vl:3b"
    updated = client.put("/api/settings", json={"language": "en", "ollama_url": "http://localhost:11434/"})
    assert updated.status_code == 200
    assert updated.json()["ollama_url"] == "http://localhost:11434"
    assert json.loads((state.config.data_dir / "settings.json").read_text())["language"] == "en"
    for bad in (
        {"ollama_url": "file:///etc/passwd"},
        {"max_image_side": 10},
        {"unknown": 1},
        {"runtime": "cloud"},
    ):
        response = client.put("/api/settings", json=bad)
        assert response.status_code == 422, bad
        assert response.json()["code"] == "invalid_settings"


def test_runtime_status_and_catalog(client: TestClient) -> None:
    runtime = client.get("/api/runtime").json()
    assert runtime["reachable"] is True
    assert runtime["model_installed"] is True
    assert runtime["models"][0]["vision"] is True
    catalog = client.get("/api/catalog").json()
    assert any(entry["recommended"] for entry in catalog)


def test_model_pull(client: TestClient) -> None:
    assert client.post("/api/runtime/pull", json={"model": "bad name; rm -rf"}).status_code == 422
    started = client.post("/api/runtime/pull", json={"model": "qwen2.5vl:3b"})
    assert started.status_code == 200 and started.json()["state"] == "running"
    for _ in range(200):
        status = client.get("/api/runtime/pull").json()
        if status["state"] != "running":
            break
    assert status["state"] == "done"
    client.put("/api/settings", json={"runtime": "openai"})
    assert client.post("/api/runtime/pull", json={"model": "x"}).json()["code"] == "unsupported"


# -- full correction workflow ---------------------------------------------------------------


def test_full_workflow(client: TestClient, engine: FakeEngine) -> None:
    response = client.post("/api/key/pages", files=files(KEY_SIZE))
    assert response.status_code == 200 and response.json()["errors"] == []
    session = wait_for(client, key_done)
    assert session["key"]["status"] == "done"
    assert [(i["question"], i["answer"]) for i in session["key"]["items"]] == [
        ("1", "B"),
        ("2", "Paris"),
        ("3", "true"),
    ]
    assert session["key"]["max_score"] == 3

    upload = client.post(
        "/api/participants",
        files=[*files(ANA_SIZE, BEN_SIZE), ("files", ("notes.txt", b"hello", "text/plain"))],
        data={"grouping": "file"},
    )
    body = upload.json()
    assert len(body["created"]) == 2
    assert body["errors"][0]["file"] == "notes.txt" and body["errors"][0]["code"] == "unsupported"
    session = wait_for(client, all_participants_done)
    by_name = {p["name"]: p for p in session["participants"]}
    assert by_name["Ana"]["result"]["score"] == 3
    assert by_name["Ben"]["result"]["counts"] == {"correct": 0, "incorrect": 1, "review": 1, "missing": 1}
    assert session["stats"]["graded"] == 2
    assert session["stats"]["pending_review"] == 1

    # The participant prompt lists the questions of the answer key.
    participant_call = next(c for c in engine.calls if c["size"] == ANA_SIZE)
    assert "1, 2, 3" in participant_call["prompt"]

    # Teacher accepts Ben's spelling.
    ben = by_name["Ben"]
    overridden = client.put(
        f"/api/participants/{ben['id']}/override", json={"question": "2", "verdict": "correct"}
    )
    ben_view = next(p for p in overridden.json()["session"]["participants"] if p["id"] == ben["id"])
    assert ben_view["result"]["score"] == 1
    assert ben_view["result"]["questions"][1]["override"] == "correct"

    # Editing an answer drops the override for that question, renaming keeps the name.
    patched = client.patch(
        f"/api/participants/{ben['id']}",
        json={
            "name": "Benjamin",
            "answers": [
                {"question": "1", "answer": "B"},
                {"question": "2", "answer": "Pariis"},
                {"question": "3", "answer": "true"},
            ],
        },
    ).json()["session"]
    ben_view = next(p for p in patched["participants"] if p["id"] == ben["id"])
    assert ben_view["name"] == "Benjamin"
    assert ben_view["result"]["questions"][1]["override"] is None
    assert ben_view["result"]["score"] == 2

    # CSV exports
    summary = client.get("/api/export.csv", params={"kind": "summary", "lang": "de"})
    assert summary.headers["content-type"].startswith("text/csv")
    text = summary.content.decode("utf-8")
    assert text.startswith("\ufeff")
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff")), delimiter=";"))
    assert rows[0][:5] == ["Teilnehmende Person", "Name", "Punkte", "Max. Punkte", "Prozent"]
    assert rows[1][1:5] == ["Ana", "3", "3", "100"]
    assert rows[2][1:5] == ["Benjamin", "2", "3", "66,7"]
    detail = client.get("/api/export.csv", params={"kind": "detail", "lang": "en"}).content.decode("utf-8")
    detail_rows = list(csv.reader(io.StringIO(detail.lstrip("\ufeff"))))
    assert detail_rows[0][0] == "Participant" and len(detail_rows) == 1 + 2 * 3

    # Images are served from memory.
    page_id = session["participants"][0]["pages"][0]["id"]
    thumb = client.get(f"/api/images/{page_id}", params={"size": "thumb"})
    assert thumb.status_code == 200 and thumb.headers["content-type"] == "image/jpeg"
    assert client.get("/api/images/unknown").status_code == 404

    # Delete and reset
    deleted = client.delete(f"/api/participants/{ben['id']}").json()["session"]
    assert len(deleted["participants"]) == 1
    reset = client.post("/api/session/reset").json()["session"]
    assert reset["participants"] == [] and reset["key"]["items"] == []
    assert reset["id"] != session["id"]


def test_grouping_single_and_page(client: TestClient) -> None:
    single = client.post(
        "/api/participants", files=files(ANA_SIZE, BEN_SIZE), data={"grouping": "single"}
    ).json()
    assert len(single["created"]) == 1
    session = wait_for(client, all_participants_done)
    assert len(session["participants"][0]["pages"]) == 2
    # Both pages are merged: the first non-empty answer per question wins.
    assert session["participants"][0]["name"] == "Ana"


def test_typed_answer_key(client: TestClient) -> None:
    response = client.post("/api/key/text", json={"text": "1. B\n2. Paris\n3) true", "mode": "replace"})
    key = response.json()["session"]["key"]
    assert [(i["question"], i["answer"]) for i in key["items"]] == [("1", "B"), ("2", "Paris"), ("3", "true")]
    assert key["status"] == "done"
    append = client.post("/api/key/text", json={"text": "4. C\n2. London", "mode": "append"}).json()[
        "session"
    ]["key"]
    assert {i["question"]: i["answer"] for i in append["items"]} == {
        "1": "B",
        "2": "London",
        "3": "true",
        "4": "C",
    }
    bad = client.post("/api/key/text", json={"text": "no answers here"})
    assert bad.status_code == 422 and bad.json()["code"] == "nothing_found"


def test_edit_key_items_with_points(client: TestClient) -> None:
    response = client.put(
        "/api/key/items",
        json={
            "items": [
                {"question": "1", "answer": "A", "points": 2},
                {"question": "2", "answer": "B", "points": 0.5},
            ]
        },
    )
    assert response.json()["session"]["key"]["max_score"] == 2.5
    invalid = client.put("/api/key/items", json={"items": [{"question": "", "answer": "A"}]})
    assert invalid.status_code == 422 and invalid.json()["code"] == "invalid_request"


def test_extraction_errors_are_reported(client: TestClient, engine: FakeEngine) -> None:
    engine.default = EngineError("unreachable", "Ollama is not reachable at http://127.0.0.1:11434.")
    client.post("/api/participants", files=files((700, 900)))
    session = wait_for(client, all_participants_done)
    participant = session["participants"][0]
    assert participant["status"] == "error"
    assert participant["error"]["code"] == "unreachable"
    assert session["stats"]["graded"] == 0

    engine.default = "I cannot read this."
    client.post(f"/api/participants/{participant['id']}/extract")
    session = wait_for(
        client,
        lambda s: (
            s["participants"][0]["status"] in ("done", "error")
            and s["participants"][0]["error"]
            and s["participants"][0]["error"]["code"] == "nothing_found"
        ),
    )
    assert session["participants"][0]["error"]["code"] == "nothing_found"


def test_missing_model_is_reported(client: TestClient) -> None:
    client.put("/api/settings", json={"model": ""})
    client.post("/api/key/pages", files=files(KEY_SIZE))
    session = wait_for(client, key_done)
    assert session["key"]["error"]["code"] == "no_model"


def test_text_fallback_when_json_is_empty(client: TestClient, engine: FakeEngine) -> None:
    engine.responses[(710, 900)] = lambda prompt, schema: '{"answers": []}' if schema else "1. A\n2. B"
    client.post("/api/key/pages", files=files((710, 900)))
    session = wait_for(client, key_done)
    assert [(i["question"], i["answer"]) for i in session["key"]["items"]] == [("1", "A"), ("2", "B")]
    assert [call["schema"] is not None for call in engine.calls] == [True, False]


def test_ocr_mode_uses_ocr_prompt(client: TestClient, engine: FakeEngine) -> None:
    client.put("/api/settings", json={"model": "deepseek-ocr:3b"})
    engine.responses[(720, 900)] = "<|ref|>1. B<|/ref|><|det|>[[1,2,3,4]]<|/det|>"
    client.post("/api/key/pages", files=files((720, 900)))
    session = wait_for(client, key_done)
    assert session["key"]["items"][0]["answer"] == "B"
    assert engine.calls[-1]["prompt"] == "Free OCR." and engine.calls[-1]["schema"] is None


def test_long_poll_returns_on_change(client: TestClient) -> None:
    version = client.get("/api/session").json()["version"]
    unchanged = client.get("/api/session", params={"since": version + 100, "wait": 0.2}).json()
    assert unchanged["version"] == version
    client.post("/api/key/text", json={"text": "1. A"})
    changed = client.get("/api/session", params={"since": version, "wait": 5}).json()
    assert changed["version"] > version


def test_cancel_jobs(client: TestClient, engine: FakeEngine) -> None:
    engine.delay = 0.5
    client.post("/api/participants", files=files((730, 900), (731, 900), (732, 900)))
    client.post("/api/jobs/cancel")
    session = wait_for(
        client, lambda s: all(p["status"] in ("idle", "done", "error") for p in s["participants"])
    )
    assert session["jobs"]["queued"] == 0
    assert any(p["status"] == "idle" for p in session["participants"])
    retry = client.post("/api/participants/extract", json={"scope": "pending"}).json()
    assert retry["queued"] >= 1


def test_participant_not_found(client: TestClient) -> None:
    response = client.patch("/api/participants/p_missing", json={"name": "x"})
    assert response.status_code == 404 and response.json()["code"] == "participant_not_found"


def test_secret_is_not_in_responses(client: TestClient) -> None:
    client.post("/api/key/text", json={"text": "1. A"})
    assert SECRET not in client.get("/api/session").text
    assert SECRET not in client.get("/api/settings").text
