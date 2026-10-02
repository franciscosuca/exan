"""Compare participant answers with the answer key.

Grading is deterministic and runs locally; the vision model is only used to *read* the sheets.
Uncertain matches (accents, spelling, word order, unreadable formats) are flagged for review
instead of being silently accepted or rejected.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from fractions import Fraction
from typing import Literal

Verdict = Literal["correct", "incorrect", "review", "missing"]
Override = Literal["correct", "incorrect"]

_QUESTION_PREFIX = re.compile(
    r"^(?:question|frage|aufgabe|teilaufgabe|pregunta|ejercicio|exercice|exercise|task|item|nr|no|n°|nº|q|#)"
    r"(?=\s*[.:#]?\s*\d)\s*[.:#]?\s*",
    re.IGNORECASE,
)


def question_key(label: object) -> str:
    """Canonical form of a question label so that "Q1", "1.", "Frage 1" and "1)" match."""
    raw = unicodedata.normalize("NFKC", "" if label is None else str(label)).strip()
    text = raw.casefold()
    text = _QUESTION_PREFIX.sub("", text, count=1)
    text = re.sub(r"\((\w{1,3})\)", r"\1", text)
    text = re.sub(r"[\s_]+", "", text)
    text = text.strip(".:)(-–—,;")
    text = re.sub(r"(?<=\d)[.\-](?=[a-z])", "", text)
    text = re.sub(r"(?<=\d)-(?=\d)", ".", text)
    text = re.sub(r"(?<![\d.])0+(?=\d)", "", text)
    return text or raw.casefold()


_TRANSLATE = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‚": "'",
        "`": "'",
        "´": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "«": '"',
        "»": '"',
        "–": "-",
        "—": "-",
        "−": "-",
    }
)
_WRAPPERS = {'"': '"', "'": "'", "(": ")", "[": "]", "{": "}"}


def normalize_answer(value: object) -> str:
    text = unicodedata.normalize("NFKC", "" if value is None else str(value))
    text = text.translate(_TRANSLATE).casefold()
    text = re.sub(r"\s+", " ", text).strip().rstrip(" .;,!。")
    while len(text) >= 2 and _WRAPPERS.get(text[0]) == text[-1]:
        inner = text[1:-1]
        if text[0] in inner or text[-1] in inner:
            break
        text = inner.strip()
    return text.rstrip(" .;,!。").strip()


_BLANK = {
    "",
    "-",
    "--",
    "---",
    "?",
    "??",
    "...",
    "…",
    "/",
    "n/a",
    "na",
    "none",
    "null",
    "nil",
    "blank",
    "empty",
    "leer",
    "keine",
    "keine antwort",
    "nicht beantwortet",
    "unbeantwortet",
    "no answer",
    "unanswered",
    "sin respuesta",
    "sans réponse",
}


def is_blank(normalized: str) -> bool:
    return normalized in _BLANK


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("ß", "ss")


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _loose(text: str) -> str:
    return re.sub(r"[\W_]+", "", strip_accents(text))


# ---------------------------------------------------------------------------
# Answer formats
# ---------------------------------------------------------------------------

_CHOICE_SINGLE = re.compile(r"^\(?([a-h])\)?\.?$")
_CHOICE_MULTI = re.compile(r"^\(?[a-h]\)?(?:\s*(?:,|;|&|\+|\band\b|\bund\b|\by\b|\bet\b|\s)\s*\(?[a-h]\)?)+$")
_CHOICE_WITH_TEXT = re.compile(r"^\(?([a-h])[).:]\s*(.+)$")


@dataclass(frozen=True)
class Choice:
    letters: frozenset[str]
    text: str = ""


def parse_choice(normalized: str) -> Choice | None:
    """Recognise multiple-choice answers such as "b", "(b)", "a, c" or "b) Paris"."""
    if match := _CHOICE_SINGLE.match(normalized):
        return Choice(frozenset(match.group(1)))
    if _CHOICE_MULTI.match(normalized):
        letters = frozenset(re.findall(r"(?<![a-z])[a-h](?![a-z])", normalized))
        if letters:
            return Choice(letters)
    if match := _CHOICE_WITH_TEXT.match(normalized):
        return Choice(frozenset(match.group(1)), match.group(2).strip())
    return None


_TRUE_WORDS = {
    "true",
    "wahr",
    "richtig",
    "ja",
    "yes",
    "si",
    "sí",
    "verdadero",
    "vrai",
    "vero",
    "correct",
    "korrekt",
    "stimmt",
}
_FALSE_WORDS = {
    "false",
    "falsch",
    "nein",
    "no",
    "falso",
    "faux",
    "incorrect",
    "inkorrekt",
    "stimmt nicht",
}
_TRUE_SHORT = {"t", "w", "r", "v", "y", "j", "✓", "✔", "☑"}
_FALSE_SHORT = {"f", "n", "✗", "✘", "☒"}


def parse_true_false(normalized: str, *, allow_choice_letters: bool = True) -> bool | None:
    if normalized in _TRUE_WORDS:
        return True
    if normalized in _FALSE_WORDS:
        return False
    if normalized in _TRUE_SHORT:
        return True
    if normalized in _FALSE_SHORT and (allow_choice_letters or normalized not in "abcdefgh"):
        return False
    return None


def _is_true_false_key(normalized: str) -> bool:
    if normalized in _TRUE_WORDS or normalized in _FALSE_WORDS:
        return True
    return normalized in (_TRUE_SHORT | _FALSE_SHORT) and normalized not in "abcdefgh"


_NUMBER = re.compile(r"^[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)$")
_FRACTION = re.compile(r"^([+-]?\d+)/(\d+)$")


def parse_number(normalized: str) -> Fraction | None:
    compact = _compact(normalized)
    if match := _FRACTION.match(compact):
        denominator = int(match.group(2))
        if denominator == 0:
            return None
        return Fraction(int(match.group(1)), denominator)
    if _NUMBER.match(compact):
        try:
            return Fraction(compact.replace(",", "."))
        except (ValueError, ZeroDivisionError):
            return None
    return None


def split_alternatives(normalized_key: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\s*\|\s*|\s+/\s+", normalized_key)]
    return [p for p in parts if p] or [normalized_key]


# ---------------------------------------------------------------------------
# Single answer check
# ---------------------------------------------------------------------------

_RANK = {"correct": 3, "review": 2, "incorrect": 1, "missing": 0}


@dataclass(frozen=True)
class Check:
    verdict: Verdict
    reason: str


def check_answer(expected: object, given: object) -> Check:
    """Compare one participant answer with the expected answer."""
    exp = normalize_answer(expected)
    got = normalize_answer(given)
    if is_blank(got):
        return Check("missing", "blank")
    if is_blank(exp):
        return Check("review", "no_key")

    best: Check | None = None
    for alternative in split_alternatives(exp):
        result = _check_single(alternative, got)
        if result.verdict == "correct":
            return result
        if best is None or _RANK[result.verdict] > _RANK[best.verdict]:
            best = result
    assert best is not None
    return best


def _check_single(exp: str, got: str) -> Check:
    if exp == got:
        return Check("correct", "exact")

    expected_choice = parse_choice(exp)
    if expected_choice is not None and not _is_true_false_key(exp):
        given_choice = parse_choice(got)
        if given_choice is not None:
            if given_choice.letters == expected_choice.letters:
                return Check("correct", "choice")
            return Check("incorrect", "choice")
        if expected_choice.text and _loose(expected_choice.text) == _loose(got):
            return Check("correct", "choice_text")
        return Check("review", "format")

    if _is_true_false_key(exp):
        expected_tf = parse_true_false(exp)
        given_tf = parse_true_false(got)
        if given_tf is None:
            return Check("review", "format")
        return Check("correct" if given_tf == expected_tf else "incorrect", "true_false")

    expected_number = parse_number(exp)
    if expected_number is not None:
        given_number = parse_number(got)
        if given_number is not None:
            return Check("correct" if given_number == expected_number else "incorrect", "number")
        if re.search(r"\d", got):
            return Check("review", "format")
        return Check("incorrect", "different")

    if _compact(exp) == _compact(got):
        if re.search(r"\d", exp):
            return Check("correct", "spacing")
        return Check("review", "spacing")

    exp_plain, got_plain = strip_accents(exp), strip_accents(got)
    if exp_plain == got_plain:
        return Check("review", "accent")
    if _loose(exp) and _loose(exp) == _loose(got):
        return Check("review", "punctuation")
    exp_tokens = re.findall(r"\w+", exp_plain)
    got_tokens = re.findall(r"\w+", got_plain)
    if len(exp_tokens) > 1 and sorted(exp_tokens) == sorted(got_tokens):
        return Check("review", "order")
    a, b = _compact(exp_plain), _compact(got_plain)
    if max(len(a), len(b)) >= 5 and SequenceMatcher(None, a, b).ratio() >= 0.85:
        return Check("review", "similar")
    return Check("incorrect", "different")


# ---------------------------------------------------------------------------
# Sheets
# ---------------------------------------------------------------------------


@dataclass
class KeyItem:
    question: str
    answer: str
    points: float = 1.0


@dataclass
class AnswerItem:
    question: str
    answer: str


@dataclass
class QuestionResult:
    question: str
    key: str
    expected: str
    given: str
    points: float
    auto: Verdict
    reason: str
    override: Override | None
    final: Verdict
    earned: float

    def view(self) -> dict[str, object]:
        return {
            "question": self.question,
            "key": self.key,
            "expected": self.expected,
            "given": self.given,
            "points": self.points,
            "auto": self.auto,
            "reason": self.reason,
            "override": self.override,
            "final": self.final,
            "earned": self.earned,
        }


@dataclass
class SheetResult:
    questions: list[QuestionResult] = field(default_factory=list)
    extra: list[AnswerItem] = field(default_factory=list)

    @property
    def score(self) -> float:
        return round(sum(q.earned for q in self.questions), 4)

    @property
    def max_score(self) -> float:
        return round(sum(q.points for q in self.questions), 4)

    @property
    def percent(self) -> float | None:
        if self.max_score <= 0:
            return None
        return round(self.score / self.max_score * 100, 1)

    def counts(self) -> dict[str, int]:
        counts = {"correct": 0, "incorrect": 0, "review": 0, "missing": 0}
        for q in self.questions:
            counts[q.final] += 1
        return counts

    def view(self) -> dict[str, object]:
        return {
            "score": self.score,
            "max_score": self.max_score,
            "percent": self.percent,
            "counts": self.counts(),
            "questions": [q.view() for q in self.questions],
            "extra": [{"question": a.question, "answer": a.answer} for a in self.extra],
        }


def index_answers(answers: Iterable[AnswerItem]) -> dict[str, AnswerItem]:
    indexed: dict[str, AnswerItem] = {}
    for item in answers:
        key = question_key(item.question)
        current = indexed.get(key)
        if current is None or (is_blank(normalize_answer(current.answer)) and item.answer.strip()):
            indexed[key] = item
    return indexed


def grade_sheet(
    key_items: Sequence[KeyItem],
    answers: Iterable[AnswerItem],
    overrides: Mapping[str, Override] | None = None,
) -> SheetResult:
    overrides = overrides or {}
    by_key = index_answers(answers)
    result = SheetResult()
    seen: set[str] = set()
    for item in key_items:
        key = question_key(item.question)
        if key in seen:
            continue
        seen.add(key)
        given_item = by_key.get(key)
        given = given_item.answer if given_item else ""
        check = check_answer(item.answer, given)
        override = overrides.get(key)
        final: Verdict = override if override in ("correct", "incorrect") else check.verdict
        points = max(0.0, float(item.points))
        result.questions.append(
            QuestionResult(
                question=item.question,
                key=key,
                expected=item.answer,
                given=given,
                points=points,
                auto=check.verdict,
                reason=check.reason,
                override=override if override in ("correct", "incorrect") else None,
                final=final,
                earned=points if final == "correct" else 0.0,
            )
        )
    result.extra = [item for key, item in by_key.items() if key not in seen and item.answer.strip()]
    return result


def summarize(key_items: Sequence[KeyItem], results: Sequence[SheetResult]) -> dict[str, object]:
    """Class-level statistics across all graded participants."""
    graded = [r for r in results if r.questions]
    percents = [r.percent for r in graded if r.percent is not None]
    questions = []
    seen: set[str] = set()
    for item in key_items:
        key = question_key(item.question)
        if key in seen:
            continue
        seen.add(key)
        rows = [q for r in graded for q in r.questions if q.key == key]
        correct = sum(1 for q in rows if q.final == "correct")
        review = sum(1 for q in rows if q.final == "review")
        missing = sum(1 for q in rows if q.final == "missing")
        questions.append(
            {
                "question": item.question,
                "key": key,
                "correct": correct,
                "review": review,
                "missing": missing,
                "total": len(rows),
                "rate": round(correct / len(rows) * 100, 1) if rows else None,
            }
        )
    return {
        "graded": len(graded),
        "average": round(sum(percents) / len(percents), 1) if percents else None,
        "best": max(percents) if percents else None,
        "worst": min(percents) if percents else None,
        "pending_review": sum(r.counts()["review"] for r in graded),
        "questions": questions,
    }
