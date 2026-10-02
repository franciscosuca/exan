"""Prompts and output schema for reading exam pages with small vision models."""

from __future__ import annotations

from collections.abc import Sequence

ANSWER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["question", "answer"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["name", "answers"],
    "additionalProperties": False,
}

_FORMAT = (
    'Reply with JSON only, exactly in this form: {"name": "", "answers": [{"question": "1", "answer": "B"}]}'
)

_RULES = """Rules:
- Use the question numbers printed on the page ("1", "2", "3a", ...). One entry per question, in page order.
- Multiple choice: give only the letter(s) of the marked option(s), for example "B" or "A, C". An option counts as marked when it is circled, ticked, crossed, underlined or written next to the question.
- True/false: give "true" or "false".
- Numbers: copy the number with its unit, if any.
- Written answers: copy the words exactly as written. Do not correct spelling, translate, explain or summarise.
- Ignore the printed question text, instructions, page headers and footers.
- Never invent questions or answers."""


def key_prompt() -> str:
    return (
        "This photo shows an ANSWER KEY for an exam: the correct solutions written or marked by the teacher.\n"
        "List every question with its correct answer.\n"
        f"{_RULES}\n"
        'Leave "name" empty.\n'
        f"{_FORMAT}"
    )


def participant_prompt(questions: Sequence[str] = ()) -> str:
    hint = ""
    labels = [q for q in questions if q.strip()][:200]
    if labels:
        hint = (
            f"The exam has these questions: {', '.join(labels)}. Report every one of them that appears on "
            'this page; use "" as the answer when the participant left a question blank.\n'
        )
    return (
        "This photo shows an exam answer sheet completed by a participant.\n"
        'Write down the participant\'s name if it is written on the page (otherwise use ""), '
        "and what the participant answered for each question.\n"
        f"{hint}"
        f"{_RULES}\n"
        "- Report what the participant wrote, even if it is wrong.\n"
        f"{_FORMAT}"
    )


def ocr_prompt(model: str) -> str:
    """Prompt for OCR-specialised models that transcribe pages instead of following JSON instructions."""
    lowered = model.lower()
    if "deepseek-ocr" in lowered:
        return "Free OCR."
    if "granite-docling" in lowered or "docling" in lowered:
        return "Convert this page to docling."
    return (
        "Transcribe this exam page exactly as text, line by line. Keep every question number at the start of "
        'its line followed by the answer, for example "1. B". Include the participant\'s name line if present.'
    )
