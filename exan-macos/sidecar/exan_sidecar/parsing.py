"""Turn raw model output (JSON or plain OCR text) into question/answer pairs."""

from __future__ import annotations

import html
import itertools
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .grading import is_blank, normalize_answer, question_key


@dataclass
class ParsedSheet:
    name: str = ""
    answers: list[tuple[str, str]] = field(default_factory=list)

    def merge(self, other: ParsedSheet) -> None:
        """Merge another page into this sheet (first non-empty answer per question wins)."""
        if not self.name and other.name:
            self.name = other.name
        index = {question_key(q): i for i, (q, _) in enumerate(self.answers)}
        for question, answer in other.answers:
            key = question_key(question)
            if key not in index:
                index[key] = len(self.answers)
                self.answers.append((question, answer))
            elif is_blank(normalize_answer(self.answers[index[key]][1])) and answer.strip():
                self.answers[index[key]] = (self.answers[index[key]][0], answer)


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.S | re.I)
_FENCE = re.compile(r"```[a-zA-Z]*\s*(.*?)```", re.S)
# DeepSeek-OCR grounding tags such as <|ref|>text<|/ref|><|det|>[[...]]<|/det|>
_GROUNDING = re.compile(r"<\|det\|>.*?<\|/det\|>|<\|/?ref\|>|<\|/?grounding\|>", re.S)


def strip_reasoning(text: str) -> str:
    text = _THINK_BLOCK.sub("", text or "")
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return _GROUNDING.sub("", text).strip()


def parse_model_output(text: str) -> ParsedSheet:
    """Parse a model response. JSON is preferred; free text is parsed line by line."""
    cleaned = strip_reasoning(text)
    data = _load_json(cleaned)
    if data is not None:
        sheet = sheet_from_json(data)
        if sheet.answers:
            return sheet
        text_sheet = parse_text(cleaned) if not cleaned.lstrip().startswith(("{", "[")) else ParsedSheet()
        if text_sheet.answers:
            text_sheet.name = text_sheet.name or sheet.name
            return text_sheet
        return sheet
    return parse_text(cleaned)


def _load_json(text: str) -> Any:
    candidates: list[str] = [text]
    candidates.extend(match.group(1) for match in _FENCE.finditer(text))
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if 0 <= start < end:
            candidates.append(text[start : end + 1])
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate[0] not in "{[":
            continue
        try:
            return json.loads(candidate)
        except ValueError:
            continue
    return None


_NAME_KEYS = (
    "name",
    "student_name",
    "participant_name",
    "student",
    "participant",
    "nombre",
    "schueler",
    "schüler",
    "teilnehmer",
)
_LIST_KEYS = ("answers", "responses", "items", "questions", "results", "respuestas", "antworten")
_QUESTION_KEYS = (
    "question",
    "question_number",
    "number",
    "id",
    "q",
    "nr",
    "no",
    "label",
    "pregunta",
    "frage",
)
_ANSWER_KEYS = (
    "answer",
    "ans",
    "a",
    "student_answer",
    "participant_answer",
    "correct_answer",
    "response",
    "value",
    "selected",
    "choice",
    "respuesta",
    "antwort",
)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (list, tuple)):
        return ", ".join(s for s in (_stringify(v) for v in value) if s)
    if isinstance(value, dict):
        for key in _ANSWER_KEYS:
            if key in value:
                return _stringify(value[key])
        return ""
    return str(value).strip()


def _lower_keys(obj: dict[str, Any]) -> dict[str, Any]:
    return {str(k).strip().lower(): v for k, v in obj.items()}


def _first(obj: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in obj:
            return obj[key]
    return None


_QUESTION_LABEL = re.compile(
    r"^(?:(?:q|question|frage|aufgabe|pregunta|nr|no)\s*[.:#]?\s*)?\d{1,3}(?:\.\d{1,2})?[a-z]?[.)]?$",
    re.I,
)


def looks_like_question(label: object) -> bool:
    return bool(_QUESTION_LABEL.match(str(label).strip()))


def sheet_from_json(data: Any) -> ParsedSheet:
    if isinstance(data, list):
        return ParsedSheet(answers=_answers_from_list(data))
    if not isinstance(data, dict):
        return ParsedSheet()
    obj = _lower_keys(data)
    name_value = _first(obj, _NAME_KEYS)
    name = _stringify(name_value) if isinstance(name_value, (str, int, float)) else ""
    for key in _LIST_KEYS:
        value = obj.get(key)
        if isinstance(value, list):
            return ParsedSheet(name=name, answers=_answers_from_list(value))
        if isinstance(value, dict):
            return ParsedSheet(name=name, answers=_answers_from_mapping(value))
    mapping = {k: v for k, v in data.items() if looks_like_question(k)}
    return ParsedSheet(name=name, answers=_answers_from_mapping(mapping))


def _answers_from_mapping(mapping: dict[Any, Any]) -> list[tuple[str, str]]:
    return _clean((str(k), _stringify(v)) for k, v in mapping.items())


def _answers_from_list(items: list[Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for position, item in enumerate(items, start=1):
        if isinstance(item, dict):
            obj = _lower_keys(item)
            question = _first(obj, _QUESTION_KEYS)
            answer = _first(obj, _ANSWER_KEYS)
            if question is None and answer is None and len(obj) == 1:
                ((question, answer),) = obj.items()
            if question is None:
                question = position
            pairs.append((_stringify(question), _stringify(answer)))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            pairs.append((_stringify(item[0]), _stringify(item[-1])))
        elif isinstance(item, str):
            parsed = parse_text(item).answers
            pairs.extend(parsed or [(str(position), item)])
        elif isinstance(item, (int, float, bool)):
            pairs.append((str(position), _stringify(item)))
    return _clean(pairs)


def _clean(pairs: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    sheet = ParsedSheet()
    for question, answer in pairs:
        question = question.strip().rstrip(".:)").strip() or question.strip()
        if not question:
            continue
        sheet.merge(ParsedSheet(answers=[(question, answer.strip())]))
    return sheet.answers


# ---------------------------------------------------------------------------
# Plain text (OCR output, pasted answer keys)
# ---------------------------------------------------------------------------

_Q = r"\d{1,3}(?:\.\d{1,2})?[a-z]?"
_PREFIX = r"(?:(?:question|frage|aufgabe|pregunta|ejercicio|exercise|task|nr\.?|no\.?|q)\s*)?"
_LINE = re.compile(
    rf"^\s*(?:[-*•>]\s*)?(?:\*\*|__)?{_PREFIX}(?P<q>{_Q})(?=[\s.):=*_\-–—]|$)(?:\*\*|__)?"
    r"\s*(?:[.):=]|-(?!\d)|–|—)?\s*(?:\*\*|__)?\s*(?P<a>.*?)\s*(?:\*\*|__)?\s*$",
    re.I,
)
_NAME_LINE = re.compile(
    r"^\s*(?:[-*•]\s*)?(?:\*\*)?(?:name|student(?:\s+name)?|participant|nombre|nom|vorname|nachname|"
    r"schüler(?:in)?|teilnehmer(?:in)?|alumno|alumna)(?:\*\*)?\s*[:\-–]\s*(?:\*\*)?\s*(?P<name>.+?)\s*$",
    re.I,
)
_INLINE_MARKER = re.compile(rf"(?:(?<=^)|(?<=[\s,;|]))({_Q})\s*[.):=\-](?!\d)", re.I)
_ANSWER_PREFIX = re.compile(
    r"^(?:answer|antwort|respuesta|réponse|reponse|lösung|loesung|solution)\s*[:\-]\s*", re.I
)
_CHECKED = re.compile(r"(?:\[[xX✓✔]\]|☒|☑|■|●|\([xX]\))\s*\(?([A-Ha-h])\b")
_TABLE_SEPARATOR = re.compile(r"^:?-{2,}:?$")
_HTML_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_HTML_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_HTML_TAG = re.compile(r"<[^>]+>")


def _html_tables_to_rows(text: str) -> str:
    if "<tr" not in text.lower():
        return text

    def row(match: re.Match[str]) -> str:
        cells = [html.unescape(_HTML_TAG.sub("", c)).strip() for c in _HTML_CELL.findall(match.group(1))]
        return "\n| " + " | ".join(cells) + " |\n"

    converted = _HTML_ROW.sub(row, text)
    return _HTML_TAG.sub("", converted)


# DocTags (granite-docling) and other markup that OCR models emit around the text.
_DOCTAG_LOCATION = re.compile(r"<loc_\d+>")
_OTSL_CELL = re.compile(r"<(?:fcel|ecel|ched|rhed|srow|lcel|ucel|xcel)>")
_BLOCK_END = re.compile(
    r"<br\s*/?>|</(?:p|div|li|text|list_item|title|caption|doctag|otsl|section_header(?:_level_\d)?)>", re.I
)
_GENERIC_TAG = re.compile(r"</?[a-zA-Z][\w-]*(?:\s[^<>]*)?/?>")


def _strip_markup(text: str) -> str:
    if "<" not in text:
        return text
    text = _DOCTAG_LOCATION.sub("", text)
    text = text.replace("<nl>", "|\n")
    text = _OTSL_CELL.sub("| ", text)
    text = _BLOCK_END.sub("\n", text)
    return html.unescape(_GENERIC_TAG.sub("", text))


def _resolve_checkboxes(answer: str) -> str:
    checked = _CHECKED.findall(answer)
    if checked:
        return ", ".join(dict.fromkeys(letter.upper() for letter in checked))
    return answer


def _clean_answer(answer: str) -> str:
    answer = _ANSWER_PREFIX.sub("", answer.strip().lstrip("|").strip())
    answer = answer.strip().strip("*_").strip()
    answer = _resolve_checkboxes(answer)
    return answer.rstrip(",;|").strip()


def _table_row(line: str) -> tuple[str, str] | None:
    if line.count("|") < 2:
        return None
    cells = [c.strip().strip("*_").strip() for c in line.strip().strip("|").split("|")]
    if not cells or all(_TABLE_SEPARATOR.match(c) or not c for c in cells):
        return None
    first = cells[0].rstrip(".:)").strip()
    if not looks_like_question(first):
        return None
    rest = cells[1:]
    if not rest:
        return None
    answer = rest[-1] if len(rest) >= 2 else rest[0]
    return first, _clean_answer(answer)


def _inline_pairs(line: str) -> list[tuple[str, str]] | None:
    markers = list(_INLINE_MARKER.finditer(line))
    if len(markers) < 2:
        return None
    numbers: list[float] = []
    for marker in markers:
        digits = re.match(r"\d+(?:\.\d+)?", marker.group(1))
        numbers.append(float(digits.group(0)) if digits else 0.0)
    if any(b <= a for a, b in itertools.pairwise(numbers)):
        return None
    pairs = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(line)
        pairs.append((marker.group(1), _clean_answer(line[marker.end() : end])))
    return pairs


def _is_structural(line: str) -> bool:
    return bool(_LINE.match(line) or _NAME_LINE.match(line) or _table_row(line))


def parse_text(text: str) -> ParsedSheet:
    """Parse free text such as "1. B", "2) Paris", markdown/HTML tables or "1-B, 2-C"."""
    sheet = ParsedSheet()
    lines = [
        line.rstrip() for line in _strip_markup(_html_tables_to_rows(strip_reasoning(text))).splitlines()
    ]
    pairs: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line:
            continue
        if not sheet.name and (name_match := _NAME_LINE.match(line)):
            sheet.name = name_match.group("name").strip().strip("*_").strip()
            continue
        if row := _table_row(line):
            pairs.append(row)
            continue
        if inline := _inline_pairs(line):
            pairs.extend(inline)
            continue
        match = _LINE.match(line)
        if not match:
            continue
        question, answer = match.group("q"), _clean_answer(match.group("a") or "")
        if not answer:
            compact = re.fullmatch(r"(\d{1,3})([a-h])", question, re.I)
            if compact and index < len(lines) and _LINE.match(lines[index].strip() or "x"):
                question, answer = compact.group(1), compact.group(2)
            else:
                look = index
                while look < len(lines) and not lines[look].strip():
                    look += 1
                if look < len(lines) and not _is_structural(lines[look].strip()):
                    answer = _clean_answer(lines[look])
                    index = look + 1
                elif compact:
                    question, answer = compact.group(1), compact.group(2)
        pairs.append((question, answer))
    sheet.answers = _clean(pairs)
    return sheet
