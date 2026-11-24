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


_FENCE = re.compile(r"```[a-zA-Z]*\s*(.*?)```", re.S)
# DeepSeek-OCR grounding tags such as <|ref|>text<|/ref|><|det|>[[...]]<|/det|>
_GROUNDING_TAG = re.compile(r"<\|/?ref\|>|<\|/?grounding\|>")


def _remove_blocks(text: str, start: str, end: str) -> str:
    """Remove every ``start ... end`` block (case-insensitive) in linear time; unclosed starts are kept."""
    lower = text.lower()
    parts: list[str] = []
    position = 0
    while (begin := lower.find(start, position)) != -1:
        finish = lower.find(end, begin + len(start))
        if finish == -1:
            break
        parts.append(text[position:begin])
        position = finish + len(end)
    parts.append(text[position:])
    return "".join(parts)


def strip_reasoning(text: str) -> str:
    text = _remove_blocks(text or "", "<think>", "</think>")
    if "</think>" in text.lower():
        text = text[text.lower().rindex("</think>") + len("</think>") :]
    text = _remove_blocks(text, "<|det|>", "<|/det|>")
    return _GROUNDING_TAG.sub("", text).strip()


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
    text = str(label).strip()
    return len(text) <= 40 and bool(_QUESTION_LABEL.match(text))


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
# A marker starts a list item such as "2-C" in "1-B, 2-C"; the 7 in a decimal like "0,7)" is not one.
_INLINE_MARKER = re.compile(rf"(?:(?<=^)|(?<=[\s,;|]))(?<!\d,)({_Q})\s*[.):=\-](?!\d)", re.I)
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
_DOCTAG_BOX = re.compile(r"<loc_(\d+)><loc_(\d+)><loc_(\d+)><loc_(\d+)>")
_DOCTAG_OPEN = re.compile(r"<([a-z_0-9]+)>\s*$")
_UNFINISHED_TAG = re.compile(r"<[^<>]*$")
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


def _same_line(top: int, bottom: int, other_top: int, other_bottom: int) -> bool:
    heights = sorted((max(1, bottom - top), max(1, other_bottom - other_top)))
    overlap = min(bottom, other_bottom) - max(top, other_top)
    # Only text of similar height forms a line; a tall table or paragraph never swallows a word.
    return overlap > heights[0] / 2 and heights[1] <= 3 * heights[0]


def doctags_to_text(text: str) -> str:
    """Rebuild reading lines from DocTags element boxes.

    granite-docling emits every element with its box (``<loc_x0><loc_y0><loc_x1><loc_y1>``) and often lists
    handwritten words after all printed text. Each element joins an earlier line it shares (keeping the
    model's reading order), which puts "Antwort:" and the handwriting next to it back together.
    """
    boxes = list(_DOCTAG_BOX.finditer(text))
    if not boxes:
        return text
    text = _UNFINISHED_TAG.sub("", text)  # output cut off by the token limit
    rows: list[list[tuple[int, int, int, str]]] = []
    for index, box in enumerate(boxes):
        end = boxes[index + 1].start() if index + 1 < len(boxes) else len(text)
        body = _strip_markup(text[box.end() : end])
        lines = [" ".join(line.split()) for line in body.splitlines()]
        body = "\n".join(line for line in lines if line)
        if not body:
            continue
        opener = _DOCTAG_OPEN.search(text[max(0, box.start() - 40) : box.start()])
        if opener and opener.group(1) == "checkbox_selected":
            body = "☑ " + body
        elif opener and opener.group(1) == "checkbox_unselected":
            body = "☐ " + body
        x0, y0, _x1, y1 = (int(value) for value in box.groups())
        element = (x0, y0, y1, body)
        target = None
        if "\n" not in body:  # tables and multi-line blocks stay on their own
            for row in rows:
                if "\n" in row[0][3]:
                    continue
                if _same_line(min(e[1] for e in row), max(e[2] for e in row), y0, y1):
                    target = row
                    break
        if target is None:
            rows.append([element])
        elif all(e[3] != body for e in target):  # small models sometimes repeat the same word many times
            target.append(element)
    # A generation loop ("A C B D E F ...") shows up as many one- or two-letter fragments on a line;
    # they are noise, while a real single-letter answer such as "B" stands alone next to its label.
    cleaned_rows: list[list[tuple[int, int, int, str]]] = []
    for row in rows:
        if sum(len(e[3]) <= 2 for e in row) >= 4:
            row = [e for e in row if len(e[3]) > 2]
        if row:
            cleaned_rows.append(row)
    return "\n".join(" ".join(e[3] for e in sorted(row, key=lambda e: e[0])) for row in cleaned_rows)


# LaTeX that OCR models (PaddleOCR-VL, ...) put around underlined or mathematical answers.
_LATEX_COMMAND = re.compile(
    r"\\(?:underline|uline|text|textbf|textit|textrm|textsf|mathrm|mathbf|mathit|mathsf|overline|"
    r"boxed|emph|operatorname|mbox|hbox)\s*\{([^{}]*)\}"
)
_LATEX_FRACTION = re.compile(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_LATEX_MATH = re.compile(r"\\\((.*?)\\\)|\\\[(.*?)\\\]|\$\$(.+?)\$\$|\$([^$\n]+?)\$", re.S)
_LATEX_SYMBOLS = {
    r"\times": "×",
    r"\cdot": "·",
    r"\checkmark": "✓",
    r"\quad": " ",
    r"\qquad": " ",
    r"\_": "_",
    r"\%": "%",
    r"\&": "&",
    r"\#": "#",
    r"\,": " ",
    r"\;": " ",
    r"\:": " ",
    r"\ ": " ",
}


def _strip_latex(text: str) -> str:
    if "\\" not in text and "$" not in text:
        return text
    text = _LATEX_MATH.sub(lambda m: next(g for g in m.groups() if g is not None), text)
    previous = None
    while previous != text:
        previous = text
        text = _LATEX_FRACTION.sub(r"\1/\2", _LATEX_COMMAND.sub(r"\1", text))
    for command, replacement in _LATEX_SYMBOLS.items():
        text = text.replace(command, replacement)
    return text


# Lines of underscores, dots or dashes are empty answer lines, not answers.
_FILLER = re.compile(r"[\s_.\-–—…·]*")


def _is_filler(text: str) -> bool:
    return bool(_FILLER.fullmatch(text))


def _resolve_checkboxes(answer: str) -> str:
    checked = _CHECKED.findall(answer)
    if checked:
        return ", ".join(dict.fromkeys(letter.upper() for letter in checked))
    return answer


def _clean_answer(answer: str) -> str:
    answer = _ANSWER_PREFIX.sub("", answer.strip().lstrip("|").strip())
    answer = answer.strip().strip("*_").strip()
    answer = _resolve_checkboxes(answer)
    answer = answer.rstrip(",;|").strip()
    return "" if _is_filler(answer) else answer


def _clean_name(name: str) -> str:
    name = name.strip().strip("*_").strip()
    return "" if _is_filler(name) else name


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


_INLINE_LABEL = re.compile(
    r"(?:^|(?<=\s))(?:answer|antwort|respuesta|réponse|reponse|lösung|loesung|solution)\s*[:\-–]\s*", re.I
)


def _labelled_answer(rest: str, lines: list[str], index: int) -> tuple[str | None, int]:
    """Answer marked with a label ("Antwort: B") on the question line or below it, before the next question.

    OCR models transcribe the printed question as well, so the text after the label is the answer.
    Returns (answer or None, index of the first line not consumed).
    """
    inline = list(_INLINE_LABEL.finditer(rest))
    if inline:
        return _clean_answer(rest[inline[-1].end() :]), index
    look = index
    while look < len(lines):
        candidate = lines[look].strip()
        if candidate and _is_structural(candidate):
            break
        label = _ANSWER_PREFIX.match(candidate)
        if label:
            answer, consumed = candidate[label.end() :].strip(), look + 1
            if not answer:
                following = look + 1
                while following < len(lines) and not lines[following].strip():
                    following += 1
                if following < len(lines):
                    nxt = lines[following].strip()
                    if not _is_structural(nxt) and not _ANSWER_PREFIX.match(nxt):
                        answer, consumed = nxt, following + 1
            return _clean_answer(answer), consumed
        look += 1
    return None, index


def _without_repeats(lines: list[str]) -> list[str]:
    """Drop a line that repeats the previous non-empty line (small models sometimes loop)."""
    result: list[str] = []
    previous = None
    for line in lines:
        stripped = line.strip()
        if stripped and stripped == previous:
            continue
        if stripped:
            previous = stripped
        result.append(line)
    return result


def parse_text(text: str) -> ParsedSheet:
    """Parse free text such as "1. B", "2) Paris", markdown/HTML tables or "1-B, 2-C"."""
    sheet = ParsedSheet()
    source = strip_reasoning(text)
    if "<loc_" in source:
        source = doctags_to_text(source)
    cleaned = _strip_latex(_strip_markup(_html_tables_to_rows(source)))
    lines = _without_repeats([line.rstrip() for line in cleaned.splitlines()])
    pairs: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line:
            continue
        if not sheet.name and (name_match := _NAME_LINE.match(line)):
            sheet.name = _clean_name(name_match.group("name"))
            continue
        if row := _table_row(line):
            pairs.append(row)
            continue
        match = _LINE.match(line)
        if match:
            # An explicit answer label wins over every other reading of a question line.
            labelled, after = _labelled_answer(match.group("a") or "", lines, index)
            if labelled is not None:
                pairs.append((match.group("q"), labelled))
                index = after
                continue
        if inline := _inline_pairs(line):
            pairs.extend(inline)
            continue
        if not match:
            continue
        question = match.group("q")
        answer = _clean_answer(match.group("a") or "")
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
