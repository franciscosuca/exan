"""Background worker that reads pages with the configured vision model, one page at a time."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from .engine.base import EngineError, VisionEngine
from .engine.builtin_catalog import get_model as get_builtin_model
from .engine.catalog import OCR, resolve_mode
from .engine.prompts import ANSWER_SCHEMA, key_prompt, ocr_prompt, participant_prompt
from .grading import AnswerItem, KeyItem, question_key
from .images import model_image
from .parsing import ParsedSheet, parse_model_output
from .session import Page, Progress

if TYPE_CHECKING:
    from .state import AppState

log = logging.getLogger(__name__)


@dataclass
class Job:
    kind: Literal["key", "participant"]
    target: str | None = None
    page_ids: list[str] | None = None
    replace: bool = False


class Extractor:
    def __init__(self, state: AppState) -> None:
        self.state = state
        self._queue: deque[Job] = deque()
        self._wakeup = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._current: Job | None = None
        self._current_task: asyncio.Task[None] | None = None

    # -- lifecycle ----------------------------------------------------------
    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="exan-extractor")

    async def stop(self) -> None:
        for task in (self._current_task, self._task):
            if task is not None:
                task.cancel()
        for task in (self._current_task, self._task):
            if task is not None:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        self._task = None

    # -- queue ----------------------------------------------------------------
    def view(self) -> dict[str, Any]:
        current = self._current
        return {
            "queued": len(self._queue),
            "running": current is not None,
            "current": {"kind": current.kind, "target": current.target} if current else None,
        }

    def submit_key(self, page_ids: list[str] | None = None, replace: bool = False) -> None:
        key = self.state.session.key
        key.status = "queued"
        key.error = None
        self._queue.append(Job("key", page_ids=page_ids, replace=replace))
        self._wakeup.set()

    def submit_participant(self, participant_id: str) -> None:
        participant = self.state.session.participants.get(participant_id)
        if participant is None:
            return
        if any(j.kind == "participant" and j.target == participant_id for j in self._queue):
            return
        participant.status = "queued"
        participant.error = None
        self._queue.append(Job("participant", target=participant_id))
        self._wakeup.set()

    def cancel_participant(self, participant_id: str) -> None:
        self._queue = deque(j for j in self._queue if j.target != participant_id)
        if self._current and self._current.target == participant_id and self._current_task:
            self._current_task.cancel()

    def cancel_all(self) -> None:
        for job in self._queue:
            self._mark(job, "idle", None)
        self._queue.clear()
        if self._current_task is not None:
            self._current_task.cancel()

    def _mark(self, job: Job, status: str, error: dict[str, str] | None) -> None:
        session = self.state.session
        if job.kind == "key":
            session.key.status = status  # type: ignore[assignment]
            session.key.error = error
        elif job.target and (participant := session.participants.get(job.target)):
            participant.status = status  # type: ignore[assignment]
            participant.error = error

    # -- worker ---------------------------------------------------------------
    async def _run(self) -> None:
        while True:
            while not self._queue:
                self._wakeup.clear()
                await self._wakeup.wait()
            job = self._queue.popleft()
            self._current = job
            task = asyncio.create_task(self._execute(job))
            self._current_task = task
            try:
                await asyncio.wait({task})
            finally:
                self._current = None
                self._current_task = None
            if task.cancelled():
                self._mark(job, "idle", None)
            elif (exc := task.exception()) is not None:
                if isinstance(exc, EngineError):
                    error = exc.view()
                    log.warning("Reading failed: %s (%s)", exc.code, exc.message)
                else:
                    log.error("Unexpected error while reading pages", exc_info=exc)
                    error = {"code": "internal", "message": "Unexpected error while reading the pages."}
                self._mark(job, "error", error)
            self.state.session.bump()

    async def _execute(self, job: Job) -> None:
        settings = self.state.settings.get()
        if not settings.model:
            raise EngineError("no_model", "Choose a model in the settings first.")
        engine = self.state.engine()
        if settings.runtime == "builtin":
            builtin = get_builtin_model(settings.model)
            if builtin is None:
                raise EngineError("model_missing", "Choose one of the built-in models in the settings.")
            # Built-in models use the reading mode and image size they were tested with.
            reader = _PageReader(engine, builtin.id, builtin.mode, builtin.image_side, allow_fallback=True)
        else:
            mode = resolve_mode(settings.extraction_mode, settings.model)
            reader = _PageReader(
                engine, settings.model, mode, settings.max_image_side, settings.extraction_mode == "auto"
            )
        if job.kind == "key":
            await self._read_key(job, reader)
        else:
            await self._read_participant(job, reader)

    async def _read_pages(
        self, reader: _PageReader, pages: list[Page], prompt: str, progress: Progress
    ) -> ParsedSheet:
        session = self.state.session
        sheet = ParsedSheet()
        progress.done, progress.total = 0, len(pages)
        session.bump()
        for page in pages:
            sheet.merge(await reader.read(page, prompt))
            progress.done += 1
            session.bump()
        return sheet

    async def _read_key(self, job: Job, reader: _PageReader) -> None:
        session = self.state.session
        key = session.key
        pages = [p for p in key.pages if job.page_ids is None or p.id in job.page_ids]
        if not pages:
            key.status = "done" if key.items else "idle"
            return
        key.status = "processing"
        key.error = None
        sheet = await self._read_pages(reader, pages, key_prompt(), key.progress)
        if session.key is not key:
            return
        points = {question_key(i.question): i.points for i in key.items}
        found = [KeyItem(q, a, points.get(question_key(q), 1.0)) for q, a in sheet.answers]
        if job.replace:
            key.items = found
        else:
            existing = {question_key(i.question): i for i in key.items}
            for item in found:
                current = existing.get(question_key(item.question))
                if current is None:
                    key.items.append(item)
                    existing[question_key(item.question)] = item
                elif not current.answer.strip():
                    current.answer = item.answer
        if found:
            key.status, key.error = "done", None
        else:
            key.status = "error"
            key.error = {"code": "nothing_found", "message": "No answers were recognised on the answer key."}

    async def _read_participant(self, job: Job, reader: _PageReader) -> None:
        session = self.state.session
        participant = session.participants.get(job.target or "")
        if participant is None:
            return
        if not participant.pages:
            participant.status = "done"
            return
        participant.status = "processing"
        participant.error = None
        hints = [item.question for item in session.key.items]
        sheet = await self._read_pages(
            reader, list(participant.pages), participant_prompt(hints), participant.progress
        )
        participant = session.participants.get(job.target or "")
        if participant is None:
            return
        participant.answers = [AnswerItem(q, a) for q, a in sheet.answers]
        participant.overrides = {}
        if sheet.name and not participant.name_edited:
            participant.name = sheet.name.strip()[:120]
        if sheet.answers:
            participant.status, participant.error = "done", None
        else:
            participant.status = "error"
            participant.error = {
                "code": "nothing_found",
                "message": "No answers were recognised on this sheet.",
            }


class _PageReader:
    def __init__(
        self, engine: VisionEngine, model: str, mode: str, max_side: int, allow_fallback: bool
    ) -> None:
        self.engine = engine
        self.model = model
        self.mode = mode
        self.max_side = max_side
        self.allow_fallback = allow_fallback

    async def read(self, page: Page, prompt: str) -> ParsedSheet:
        image = await asyncio.to_thread(model_image, page.jpeg, self.max_side)
        if self.mode == OCR:
            text = await self.engine.complete(
                model=self.model, prompt=ocr_prompt(self.model), image_jpeg=image, schema=None
            )
            return parse_model_output(text)
        text = await self.engine.complete(
            model=self.model, prompt=prompt, image_jpeg=image, schema=ANSWER_SCHEMA
        )
        sheet = parse_model_output(text)
        if not sheet.answers and self.allow_fallback:
            text = await self.engine.complete(model=self.model, prompt=prompt, image_jpeg=image, schema=None)
            sheet = parse_model_output(text)
        return sheet
