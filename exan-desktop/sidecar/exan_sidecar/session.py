"""In-memory session state. Nothing here is persisted: closing the app discards the session."""

from __future__ import annotations

import asyncio
import secrets
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

from .grading import AnswerItem, KeyItem, Override, SheetResult, grade_sheet, question_key, summarize

JobStatus = Literal["idle", "queued", "processing", "done", "error"]

MAX_PAGES_PER_SESSION = 600
MAX_PARTICIPANTS = 400


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


@dataclass
class Page:
    id: str
    name: str
    width: int
    height: int
    jpeg: bytes = field(repr=False)
    thumb: bytes = field(repr=False)
    source: str = "computer"

    def view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "source": self.source,
        }


@dataclass
class Progress:
    done: int = 0
    total: int = 0

    def view(self) -> dict[str, int]:
        return {"done": self.done, "total": self.total}


@dataclass
class AnswerKey:
    pages: list[Page] = field(default_factory=list)
    items: list[KeyItem] = field(default_factory=list)
    status: JobStatus = "idle"
    error: dict[str, str] | None = None
    progress: Progress = field(default_factory=Progress)

    def view(self) -> dict[str, Any]:
        keys = [question_key(i.question) for i in self.items]
        duplicates = sorted({k for k in keys if keys.count(k) > 1})
        return {
            "pages": [p.view() for p in self.pages],
            "items": [{"question": i.question, "answer": i.answer, "points": i.points} for i in self.items],
            "status": self.status,
            "error": self.error,
            "progress": self.progress.view(),
            "duplicates": duplicates,
            "max_score": round(sum(max(0.0, i.points) for i in self.items), 4),
        }


@dataclass
class Participant:
    id: str
    number: int
    name: str = ""
    pages: list[Page] = field(default_factory=list)
    answers: list[AnswerItem] = field(default_factory=list)
    overrides: dict[str, Override] = field(default_factory=dict)
    status: JobStatus = "idle"
    error: dict[str, str] | None = None
    progress: Progress = field(default_factory=Progress)
    source: str = "computer"
    name_edited: bool = False
    created: float = field(default_factory=time.time)

    @property
    def is_graded(self) -> bool:
        """Answers are available (read by the model or typed in by the user)."""
        return self.status == "done" or bool(self.answers)

    def grade(self, key: AnswerKey) -> SheetResult:
        return grade_sheet(key.items, self.answers, self.overrides)

    def view(self, key: AnswerKey, result: SheetResult | None = None) -> dict[str, Any]:
        result = result or self.grade(key)
        return {
            "id": self.id,
            "number": self.number,
            "name": self.name,
            "pages": [p.view() for p in self.pages],
            "answers": [{"question": a.question, "answer": a.answer} for a in self.answers],
            "status": self.status,
            "error": self.error,
            "progress": self.progress.view(),
            "source": self.source,
            "graded": self.is_graded,
            "result": result.view(),
        }


class Session:
    """The single correction session held by the engine."""

    def __init__(self) -> None:
        self.id = new_id("s")
        self.version = 0
        self.key = AnswerKey()
        self.participants: dict[str, Participant] = {}
        self._next_number = 1
        self._changed = asyncio.Event()
        self.last_phone_upload: dict[str, Any] | None = None

    # -- change notification -------------------------------------------------
    def bump(self) -> int:
        self.version += 1
        event, self._changed = self._changed, asyncio.Event()
        event.set()
        return self.version

    async def wait_for_change(self, since: int, timeout: float) -> None:
        if self.version != since or timeout <= 0:
            return
        event = self._changed
        try:
            await asyncio.wait_for(event.wait(), timeout)
        except TimeoutError:
            return

    # -- mutations ----------------------------------------------------------
    def reset(self) -> None:
        self.id = new_id("s")
        self.key = AnswerKey()
        self.participants = {}
        self._next_number = 1
        self.last_phone_upload = None
        self.bump()

    def page_count(self) -> int:
        return len(self.key.pages) + sum(len(p.pages) for p in self.participants.values())

    def add_participant(self, pages: Iterable[Page], source: str = "computer") -> Participant:
        participant = Participant(id=new_id("p"), number=self._next_number, pages=list(pages), source=source)
        self._next_number += 1
        self.participants[participant.id] = participant
        return participant

    def find_page(self, page_id: str) -> Page | None:
        for page in self.key.pages:
            if page.id == page_id:
                return page
        for participant in self.participants.values():
            for page in participant.pages:
                if page.id == page_id:
                    return page
        return None

    # -- views --------------------------------------------------------------
    def view(self, jobs: dict[str, Any] | None = None) -> dict[str, Any]:
        participants = list(self.participants.values())
        results = [p.grade(self.key) for p in participants]
        graded = [r for p, r in zip(participants, results, strict=True) if p.is_graded]
        return {
            "id": self.id,
            "version": self.version,
            "key": self.key.view(),
            "participants": [p.view(self.key, r) for p, r in zip(participants, results, strict=True)],
            "stats": summarize(self.key.items, graded),
            "jobs": jobs or {},
            "last_phone_upload": self.last_phone_upload,
        }
