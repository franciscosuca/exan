"""CSV export of the current session (opened by Excel, Numbers and LibreOffice)."""

from __future__ import annotations

import csv
import io
from typing import Literal

from .grading import question_key
from .session import Session

ExportKind = Literal["summary", "detail"]

_LABELS = {
    "en": {
        "participant": "Participant",
        "name": "Name",
        "score": "Score",
        "max": "Max score",
        "percent": "Percent",
        "correct": "Correct",
        "incorrect": "Incorrect",
        "review": "To review",
        "missing": "Missing",
        "question": "Question",
        "expected": "Expected answer",
        "given": "Given answer",
        "verdict": "Verdict",
        "points": "Points",
        "earned": "Points earned",
        "override": "Changed by teacher",
        "yes": "yes",
    },
    "de": {
        "participant": "Teilnehmende Person",
        "name": "Name",
        "score": "Punkte",
        "max": "Max. Punkte",
        "percent": "Prozent",
        "correct": "Richtig",
        "incorrect": "Falsch",
        "review": "Zu prüfen",
        "missing": "Fehlt",
        "question": "Frage",
        "expected": "Erwartete Antwort",
        "given": "Gegebene Antwort",
        "verdict": "Bewertung",
        "points": "Punkte",
        "earned": "Erreichte Punkte",
        "override": "Von Lehrkraft geändert",
        "yes": "ja",
    },
}

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: str) -> str:
    """Neutralise spreadsheet formulas in text cells (CSV injection)."""
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value


def _number(value: float | None, lang: str) -> str:
    if value is None:
        return ""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    if text in ("", "-0"):
        text = "0"
    return text.replace(".", ",") if lang == "de" else text


def export_csv(session: Session, kind: ExportKind = "summary", lang: str = "de") -> str:
    lang = "de" if lang == "de" else "en"
    labels = _LABELS[lang]
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";" if lang == "de" else ",", lineterminator="\r\n")
    participants = sorted(session.participants.values(), key=lambda p: p.number)

    def display_name(number: int, name: str) -> str:
        return safe_cell(name.strip()) if name.strip() else f"{labels['participant']} {number}"

    if kind == "detail":
        writer.writerow(
            [
                labels["participant"],
                labels["question"],
                labels["expected"],
                labels["given"],
                labels["verdict"],
                labels["earned"],
                labels["points"],
                labels["override"],
            ]
        )
        for participant in participants:
            result = participant.grade(session.key)
            for question in result.questions:
                writer.writerow(
                    [
                        display_name(participant.number, participant.name),
                        safe_cell(question.question),
                        safe_cell(question.expected),
                        safe_cell(question.given),
                        labels[question.final],
                        _number(question.earned, lang),
                        _number(question.points, lang),
                        labels["yes"] if question.override else "",
                    ]
                )
        return "\ufeff" + buffer.getvalue()

    result_rows = [(p, p.grade(session.key)) for p in participants]
    questions: list[str] = []
    seen: set[str] = set()
    for item in session.key.items:
        key = question_key(item.question)
        if key not in seen:
            seen.add(key)
            questions.append(item.question)
    writer.writerow(
        [
            labels["participant"],
            labels["name"],
            labels["score"],
            labels["max"],
            labels["percent"],
            labels["correct"],
            labels["incorrect"],
            labels["review"],
            labels["missing"],
            *(safe_cell(f"{labels['question']} {q}") for q in questions),
        ]
    )
    for participant, result in result_rows:
        counts = result.counts()
        writer.writerow(
            [
                str(participant.number),
                display_name(participant.number, participant.name),
                _number(result.score, lang),
                _number(result.max_score, lang),
                _number(result.percent, lang),
                counts["correct"],
                counts["incorrect"],
                counts["review"],
                counts["missing"],
                *(_number(q.earned, lang) for q in result.questions),
            ]
        )
    return "\ufeff" + buffer.getvalue()
