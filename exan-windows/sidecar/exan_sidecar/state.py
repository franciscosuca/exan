"""Application state shared by the desktop API and the phone bridge."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable, Sequence
from typing import Any, Literal

from .config import RuntimeConfig, SettingsStore
from .engine.base import EngineError, VisionEngine, create_engine
from .engine.llamacpp import BuiltinEngine, LlamaServer
from .engine.model_store import ModelStore
from .errors import ApiError
from .extraction import Extractor
from .images import ImageError, prepare_upload
from .session import MAX_PAGES_PER_SESSION, MAX_PARTICIPANTS, Page, Participant, Session, new_id

log = logging.getLogger(__name__)

Grouping = Literal["file", "page", "single"]
EngineFactory = Callable[[str, str, float], VisionEngine]


class PullManager:
    """Downloads one model at a time (built-in model or Ollama pull) and exposes its progress."""

    def __init__(self, state: AppState) -> None:
        self.state = state
        self._task: asyncio.Task[None] | None = None
        self._status: dict[str, Any] = {"state": "idle", "model": None}

    def view(self) -> dict[str, Any]:
        return dict(self._status)

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self, model: str) -> None:
        if self.running:
            raise ApiError(409, "pull_running", "A model download is already running.")
        self._status = {
            "state": "running",
            "model": model,
            "status": "starting",
            "completed": None,
            "total": None,
        }
        self._task = asyncio.create_task(self._run(model), name="exan-pull")

    def running_model(self) -> str | None:
        return self._status.get("model") if self.running else None

    async def _run(self, model: str) -> None:
        engine = self.state.engine()

        def progress(status: str, completed: int | None, total: int | None) -> None:
            self._status.update(status=status, completed=completed, total=total)

        try:
            await engine.pull(model, progress)
        except asyncio.CancelledError:
            self._status.update(state="cancelled")
            raise
        except EngineError as exc:
            self._status.update(state="error", error=exc.view())
        except Exception:
            log.exception("Model download failed")
            self._status.update(state="error", error={"code": "internal", "message": "The download failed."})
        else:
            self._status.update(state="done", status="success")

    def cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()

    async def stop(self) -> None:
        self.cancel()
        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task


class AppState:
    def __init__(self, config: RuntimeConfig, *, engine_factory: EngineFactory | None = None) -> None:
        from .phone import PhoneBridge

        self.config = config
        self.settings = SettingsStore(config.data_dir / "settings.json")
        self.session = Session()
        self.models = ModelStore(config.model_root)
        self.llama = LlamaServer(config.runtime_dir, config.log_dir, config.data_dir)
        self.extractor = Extractor(self)
        self.pull = PullManager(self)
        self.phone = PhoneBridge(self)
        self._engine_factory: EngineFactory = engine_factory or self._default_engine
        self._engine: VisionEngine | None = None
        self._engine_key: tuple[str, str, int] | None = None
        self._retired: list[VisionEngine] = []

    # -- engine ---------------------------------------------------------------
    def _default_engine(self, kind: str, url: str, timeout: float) -> VisionEngine:
        if kind == "builtin":
            return BuiltinEngine(self.models, self.llama, timeout=timeout)
        return create_engine(kind, url, timeout)

    def engine(self) -> VisionEngine:
        settings = self.settings.get()
        key = (settings.runtime, settings.runtime_url(), settings.request_timeout)
        if self._engine is None or self._engine_key != key:
            if self._engine is not None:
                self._retired.append(self._engine)
            self._engine = self._engine_factory(
                settings.runtime, settings.runtime_url(), settings.request_timeout
            )
            self._engine_key = key
        return self._engine

    # -- lifecycle --------------------------------------------------------------
    async def startup(self) -> None:
        self.extractor.start()

    async def shutdown(self) -> None:
        await self.phone.stop()
        await self.pull.stop()
        await self.extractor.stop()
        for engine in [*self._retired, self._engine]:
            if engine is not None:
                with contextlib.suppress(Exception):
                    await engine.aclose()
        self._retired.clear()
        self._engine = None
        await self.llama.stop()

    # -- views ------------------------------------------------------------------
    def session_view(self) -> dict[str, Any]:
        view = self.session.view(jobs=self.extractor.view())
        view["phone"] = {
            "active": self.phone.active,
            "target": self.phone.target,
            "uploads": self.phone.uploads,
        }
        return view

    # -- uploads ------------------------------------------------------------------
    async def ingest(
        self, files: Sequence[tuple[str, bytes]], source: str
    ) -> tuple[list[list[Page]], list[dict]]:
        """Decode uploaded files into pages, grouped per file. Errors are reported per file."""
        groups: list[list[Page]] = []
        errors: list[dict[str, str]] = []
        budget = MAX_PAGES_PER_SESSION - self.session.page_count()
        for name, data in files:
            try:
                prepared = await asyncio.to_thread(prepare_upload, data, name)
            except ImageError as exc:
                errors.append({"file": name, "code": exc.code, "message": exc.message})
                continue
            if len(prepared) > budget:
                errors.append(
                    {"file": name, "code": "session_full", "message": "This session holds too many pages."}
                )
                continue
            budget -= len(prepared)
            groups.append(
                [
                    Page(
                        id=new_id("pg"),
                        name=item.name,
                        width=item.width,
                        height=item.height,
                        jpeg=item.jpeg,
                        thumb=item.thumb,
                        source=source,
                    )
                    for item in prepared
                ]
            )
        return groups, errors

    def add_key_pages(self, groups: Sequence[Sequence[Page]]) -> list[Page]:
        pages = [page for group in groups for page in group]
        if pages:
            self.session.key.pages.extend(pages)
            self.extractor.submit_key([p.id for p in pages], replace=False)
            self.session.bump()
        return pages

    def add_participants(
        self, groups: Sequence[Sequence[Page]], grouping: Grouping, source: str
    ) -> list[Participant]:
        if grouping == "single":
            sets = [[page for group in groups for page in group]]
        elif grouping == "page":
            sets = [[page] for group in groups for page in group]
        else:
            sets = [list(group) for group in groups]
        sets = [s for s in sets if s]
        room = MAX_PARTICIPANTS - len(self.session.participants)
        if len(sets) > room:
            raise ApiError(
                409, "too_many_participants", f"A session can hold at most {MAX_PARTICIPANTS} participants."
            )
        created = [self.session.add_participant(pages, source=source) for pages in sets]
        for participant in created:
            self.extractor.submit_participant(participant.id)
        if created:
            self.session.bump()
        return created

    def reset_session(self) -> None:
        self.extractor.cancel_all()
        self.session.reset()
