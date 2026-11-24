"""HTTP API used by the desktop UI. Only reachable on loopback and only with the per-launch secret."""

from __future__ import annotations

import hmac
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from . import __version__
from .engine.base import EngineError
from .engine.builtin_catalog import catalog as builtin_catalog
from .engine.builtin_catalog import get_model as get_builtin_model
from .engine.catalog import catalog_view
from .errors import ApiError
from .export import export_csv
from .grading import AnswerItem, KeyItem, index_answers, normalize_answer, question_key
from .parsing import parse_text
from .session import Participant
from .state import AppState
from .uploads import BodyLimitMiddleware, read_upload_form

MAX_REQUEST_BYTES = 300 * 1024 * 1024
MAX_FILES_PER_REQUEST = 100
MAX_FILE_BYTES = 60 * 1024 * 1024
MAX_LONG_POLL_SECONDS = 30.0
_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}$")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class KeyItemIn(BaseModel):
    question: str = Field(min_length=1, max_length=80)
    answer: str = Field("", max_length=2000)
    points: float = Field(1.0, ge=0, le=1000)


class KeyItemsIn(BaseModel):
    items: list[KeyItemIn] = Field(max_length=500)


class KeyTextIn(BaseModel):
    text: str = Field(max_length=200_000)
    mode: Literal["replace", "append"] = "replace"


class AnswerIn(BaseModel):
    question: str = Field(min_length=1, max_length=80)
    answer: str = Field("", max_length=2000)


class ParticipantPatch(BaseModel):
    name: str | None = Field(None, max_length=120)
    answers: list[AnswerIn] | None = Field(None, max_length=500)


class OverrideIn(BaseModel):
    question: str = Field(min_length=1, max_length=80)
    verdict: Literal["correct", "incorrect"] | None = None


class ExtractAllIn(BaseModel):
    scope: Literal["pending", "all"] = "pending"


class PhoneIn(BaseModel):
    target: Literal["key", "participants"] = "participants"


class PullIn(BaseModel):
    model: str = Field(min_length=1, max_length=200)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


def _host_name(header: str) -> str:
    header = header.strip().lower()
    if header.startswith("["):
        return header.split("]", 1)[0] + "]"
    return header.split(":", 1)[0]


class LocalGuard:
    """Rejects requests with a foreign Host header (DNS rebinding) or without the bearer secret."""

    allowed_hosts = frozenset({"127.0.0.1", "localhost", "[::1]"})

    def __init__(self, app: ASGIApp, secret: str) -> None:
        self.app = app
        self.secret = secret.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        host = _host_name(headers.get(b"host", b"").decode("latin-1"))
        if host not in self.allowed_hosts:
            await _reject(send, 400, "Invalid host header.", "invalid_host")
            return
        auth = headers.get(b"authorization", b"")
        scheme, _, token = auth.partition(b" ")
        if scheme.lower() != b"bearer" or not hmac.compare_digest(token.strip(), self.secret):
            await _reject(send, 401, "Missing or invalid credentials.", "unauthorized")
            return
        await self.app(scope, receive, send)


async def _reject(send: Send, status: int, detail: str, code: str) -> None:
    body = JSONResponse({"detail": detail, "code": code}).body
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    if status == 401:
        headers.append((b"www-authenticate", b"Bearer"))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _participant(state: AppState, participant_id: str) -> Participant:
    participant = state.session.participants.get(participant_id)
    if participant is None:
        raise ApiError(404, "participant_not_found", "This participant no longer exists.")
    return participant


def _updated(state: AppState, **extra: Any) -> dict[str, Any]:
    state.session.bump()
    return {"session": state.session_view(), **extra}


def _parse_grouping(value: str | None) -> Literal["file", "page", "single"]:
    if value in ("file", "page", "single"):
        return value  # type: ignore[return-value]
    return "file"


def create_app(state: AppState) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await state.startup()
        try:
            yield
        finally:
            await state.shutdown()

    app = FastAPI(title="Exan engine", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.exan = state

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse({"detail": exc.message, "code": exc.code}, status_code=exc.status)

    @app.exception_handler(EngineError)
    async def _engine_error(_: Request, exc: EngineError) -> JSONResponse:
        status = 502 if exc.code in ("unreachable", "timeout", "runtime_error") else 400
        return JSONResponse({"detail": exc.message, "code": exc.code}, status_code=status)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
        message = f"{location}: {first.get('msg', 'invalid value')}" if location else "Invalid request."
        return JSONResponse({"detail": message, "code": "invalid_request"}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exc.detail), "code": f"http_{exc.status_code}"},
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    api = APIRouter(prefix="/api")

    # -- basics ---------------------------------------------------------------------
    @api.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "version": __version__}

    @api.get("/settings")
    async def get_settings() -> dict[str, Any]:
        return state.settings.get().model_dump()

    @api.put("/settings")
    async def put_settings(patch: dict[str, Any]) -> dict[str, Any]:
        try:
            settings = state.settings.update(patch)
        except ValidationError as exc:
            first = exc.errors()[0]
            field = ".".join(str(p) for p in first.get("loc", ()))
            raise ApiError(422, "invalid_settings", f"{field}: {first.get('msg', 'invalid value')}") from exc
        except ValueError as exc:
            raise ApiError(422, "invalid_settings", str(exc)) from exc
        # Free the memory of a built-in model that is no longer used.
        loaded = state.llama.model_id
        if loaded and (settings.runtime != "builtin" or settings.model != loaded):
            await state.llama.stop()
        return settings.model_dump()

    # -- runtime --------------------------------------------------------------------
    @api.get("/runtime")
    async def runtime() -> dict[str, Any]:
        status = await state.engine().status()
        settings = state.settings.get()
        view = status.view()
        names = {m.name for m in status.models}
        view["model"] = settings.model
        view["model_installed"] = bool(settings.model) and (
            settings.model in names or f"{settings.model}:latest" in names
        )
        view["pull"] = state.pull.view()
        return view

    @api.get("/catalog")
    async def catalog() -> list[dict[str, Any]]:
        return catalog_view()

    @api.get("/models")
    async def builtin_models() -> list[dict[str, Any]]:
        """Models of the built-in runtime with their download state."""
        return [
            {
                **model.view(),
                "installed": state.models.is_installed(model),
                "downloaded_bytes": state.models.downloaded_bytes(model),
            }
            for model in builtin_catalog()
        ]

    @api.delete("/models/{model_id}")
    async def delete_builtin_model(model_id: str) -> list[dict[str, Any]]:
        model = get_builtin_model(model_id)
        if model is None:
            raise ApiError(404, "model_not_found", "This model is not one of Exan's built-in models.")
        if state.pull.running_model() == model.id:
            raise ApiError(409, "pull_running", "Cancel the download of this model first.")
        if state.llama.model_id == model.id:
            await state.llama.stop()
        state.models.delete(model)
        return await builtin_models()

    @api.post("/runtime/pull")
    async def start_pull(body: PullIn) -> dict[str, Any]:
        runtime = state.settings.get().runtime
        if runtime == "builtin":
            if get_builtin_model(body.model) is None:
                raise ApiError(422, "invalid_model", "This is not one of Exan's built-in models.")
        elif runtime != "ollama":
            raise ApiError(
                400, "unsupported", "Download models in the model server app (for example LM Studio)."
            )
        elif not _MODEL_NAME.match(body.model):
            raise ApiError(422, "invalid_model", "This is not a valid model name.")
        state.pull.start(body.model)
        return state.pull.view()

    @api.get("/runtime/pull")
    async def pull_status() -> dict[str, Any]:
        return state.pull.view()

    @api.delete("/runtime/pull")
    async def cancel_pull() -> dict[str, Any]:
        state.pull.cancel()
        return state.pull.view()

    # -- session --------------------------------------------------------------------
    @api.get("/session")
    async def get_session(
        since: Annotated[int | None, Query(ge=0)] = None,
        wait: Annotated[float, Query(ge=0, le=MAX_LONG_POLL_SECONDS)] = 0,
    ) -> dict[str, Any]:
        if since is not None and wait > 0:
            await state.session.wait_for_change(since, wait)
        return state.session_view()

    @api.post("/session/reset")
    async def reset_session() -> dict[str, Any]:
        state.reset_session()
        return {"session": state.session_view()}

    @api.post("/jobs/cancel")
    async def cancel_jobs() -> dict[str, Any]:
        state.extractor.cancel_all()
        return _updated(state)

    # -- answer key -----------------------------------------------------------------
    @api.post("/key/pages")
    async def add_key_pages(request: Request) -> dict[str, Any]:
        files, _, errors = await read_upload_form(
            request, max_files=MAX_FILES_PER_REQUEST, max_file_bytes=MAX_FILE_BYTES
        )
        groups, ingest_errors = await state.ingest(files, source="computer")
        state.add_key_pages(groups)
        return _updated(state, errors=errors + ingest_errors)

    @api.delete("/key/pages/{page_id}")
    async def delete_key_page(page_id: str) -> dict[str, Any]:
        key = state.session.key
        before = len(key.pages)
        key.pages = [p for p in key.pages if p.id != page_id]
        if len(key.pages) == before:
            raise ApiError(404, "page_not_found", "This page no longer exists.")
        return _updated(state)

    @api.put("/key/items")
    async def put_key_items(body: KeyItemsIn) -> dict[str, Any]:
        key = state.session.key
        key.items = [
            KeyItem(item.question.strip(), item.answer.strip(), item.points)
            for item in body.items
            if item.question.strip()
        ]
        if key.status in ("idle", "error") and key.items:
            key.status, key.error = "done", None
        return _updated(state)

    @api.post("/key/text")
    async def put_key_text(body: KeyTextIn) -> dict[str, Any]:
        sheet = parse_text(body.text)
        if not sheet.answers:
            raise ApiError(
                422, "nothing_found", "No answers were found. Write one answer per line, for example '1. B'."
            )
        key = state.session.key
        points = {question_key(i.question): i.points for i in key.items}
        found = [KeyItem(q, a, points.get(question_key(q), 1.0)) for q, a in sheet.answers]
        if body.mode == "replace":
            key.items = found
        else:
            existing = {question_key(i.question): i for i in key.items}
            for item in found:
                current = existing.get(question_key(item.question))
                if current is None:
                    key.items.append(item)
                    existing[question_key(item.question)] = item
                else:
                    current.answer = item.answer
        if key.status != "processing":
            key.status, key.error = "done", None
        return _updated(state)

    @api.post("/key/extract")
    async def extract_key() -> dict[str, Any]:
        if not state.session.key.pages:
            raise ApiError(400, "no_pages", "Add a photo of the answer key first.")
        state.extractor.submit_key(None, replace=True)
        return _updated(state)

    # -- participants -------------------------------------------------------------
    @api.post("/participants")
    async def add_participants(request: Request) -> dict[str, Any]:
        files, fields, errors = await read_upload_form(
            request, max_files=MAX_FILES_PER_REQUEST, max_file_bytes=MAX_FILE_BYTES
        )
        groups, ingest_errors = await state.ingest(files, source="computer")
        created = state.add_participants(groups, _parse_grouping(fields.get("grouping")), source="computer")
        return _updated(state, errors=errors + ingest_errors, created=[p.id for p in created])

    @api.post("/participants/extract")
    async def extract_all(body: ExtractAllIn) -> dict[str, Any]:
        count = 0
        for participant in state.session.participants.values():
            if not participant.pages:
                continue
            if body.scope == "all" or participant.status in ("idle", "error"):
                state.extractor.submit_participant(participant.id)
                count += 1
        return _updated(state, queued=count)

    @api.patch("/participants/{participant_id}")
    async def patch_participant(participant_id: str, body: ParticipantPatch) -> dict[str, Any]:
        participant = _participant(state, participant_id)
        if body.name is not None:
            participant.name = body.name.strip()
            participant.name_edited = True
        if body.answers is not None:
            before = index_answers(participant.answers)
            participant.answers = [AnswerItem(a.question.strip(), a.answer.strip()) for a in body.answers]
            after = index_answers(participant.answers)
            for key in list(participant.overrides):
                old = normalize_answer(before[key].answer) if key in before else ""
                new = normalize_answer(after[key].answer) if key in after else ""
                if old != new:
                    del participant.overrides[key]
            if participant.status in ("idle", "error"):
                participant.status, participant.error = "done", None
        return _updated(state)

    @api.put("/participants/{participant_id}/override")
    async def put_override(participant_id: str, body: OverrideIn) -> dict[str, Any]:
        participant = _participant(state, participant_id)
        key = question_key(body.question)
        if body.verdict is None:
            participant.overrides.pop(key, None)
        else:
            participant.overrides[key] = body.verdict
        return _updated(state)

    @api.post("/participants/{participant_id}/pages")
    async def add_participant_pages(participant_id: str, request: Request) -> dict[str, Any]:
        participant = _participant(state, participant_id)
        files, _, errors = await read_upload_form(
            request, max_files=MAX_FILES_PER_REQUEST, max_file_bytes=MAX_FILE_BYTES
        )
        groups, ingest_errors = await state.ingest(files, source="computer")
        pages = [page for group in groups for page in group]
        if participant.id in state.session.participants and pages:
            participant.pages.extend(pages)
            state.extractor.submit_participant(participant.id)
        return _updated(state, errors=errors + ingest_errors)

    @api.delete("/participants/{participant_id}/pages/{page_id}")
    async def delete_participant_page(participant_id: str, page_id: str) -> dict[str, Any]:
        participant = _participant(state, participant_id)
        before = len(participant.pages)
        participant.pages = [p for p in participant.pages if p.id != page_id]
        if len(participant.pages) == before:
            raise ApiError(404, "page_not_found", "This page no longer exists.")
        return _updated(state)

    @api.delete("/participants/{participant_id}")
    async def delete_participant(participant_id: str) -> dict[str, Any]:
        _participant(state, participant_id)
        state.extractor.cancel_participant(participant_id)
        state.session.participants.pop(participant_id, None)
        return _updated(state)

    @api.post("/participants/{participant_id}/extract")
    async def extract_participant(participant_id: str) -> dict[str, Any]:
        participant = _participant(state, participant_id)
        if not participant.pages:
            raise ApiError(400, "no_pages", "This participant has no pages.")
        state.extractor.submit_participant(participant.id)
        return _updated(state)

    # -- images & export ------------------------------------------------------------
    @api.get("/images/{page_id}")
    async def image(page_id: str, size: Literal["thumb", "full"] = "thumb") -> Response:
        page = state.session.find_page(page_id)
        if page is None:
            raise ApiError(404, "page_not_found", "This page no longer exists.")
        return Response(
            page.thumb if size == "thumb" else page.jpeg,
            media_type="image/jpeg",
            headers={"cache-control": "private, max-age=86400, immutable"},
        )

    @api.get("/export.csv")
    async def export(
        kind: Literal["summary", "detail"] = "summary", lang: Literal["de", "en"] = "de"
    ) -> Response:
        content = export_csv(state.session, kind, lang)
        return Response(
            content.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"cache-control": "no-store"},
        )

    # -- phone bridge ---------------------------------------------------------------
    @api.get("/phone")
    async def phone_status() -> dict[str, Any]:
        return state.phone.view()

    @api.post("/phone/start")
    async def phone_start(body: PhoneIn) -> dict[str, Any]:
        try:
            view = await state.phone.start(body.target)
        except OSError as exc:
            raise ApiError(500, "phone_failed", f"The phone connection could not be started: {exc}") from exc
        state.session.bump()
        return view

    @api.post("/phone/target")
    async def phone_target(body: PhoneIn) -> dict[str, Any]:
        return await state.phone.set_target(body.target)

    @api.post("/phone/stop")
    async def phone_stop() -> dict[str, Any]:
        await state.phone.stop()
        state.session.bump()
        return state.phone.view()

    app.include_router(api)

    app.add_middleware(BodyLimitMiddleware, max_bytes=MAX_REQUEST_BYTES)
    app.add_middleware(LocalGuard, secret=state.config.secret)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(state.config.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )
    return app
