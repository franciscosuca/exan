"""In-memory persistence for exam comparison workflow state."""

from typing import Any, TypedDict


class ExamRecord(TypedDict):
    """Stored exam structure and the provider's original response."""

    structure: dict[str, Any]
    raw_result: dict[str, Any]


class AnswerKeyRecord(TypedDict):
    """Stored normalized answer key and the provider's original response."""

    key: dict[str, Any]
    raw_result: dict[str, Any]


class ExamRepository:
    """Process-local storage for the MVP exam comparison workflow."""

    def __init__(self) -> None:
        self._exams: dict[str, ExamRecord] = {}
        self._answer_keys: dict[str, AnswerKeyRecord] = {}

    def save_exam(
        self,
        exam_id: str,
        structure: dict[str, Any],
        raw_result: dict[str, Any],
    ) -> None:
        """Store an analyzed exam and its raw provider result."""
        self._exams[exam_id] = {"structure": structure, "raw_result": raw_result}

    def get_exam(self, exam_id: str) -> ExamRecord | None:
        """Return an exam record, or ``None`` when it is not stored."""
        return self._exams.get(exam_id)

    def save_answer_key(
        self,
        exam_id: str,
        key: dict[str, Any],
        raw_result: dict[str, Any],
    ) -> None:
        """Store an answer key and its raw provider result for an exam."""
        self._answer_keys[exam_id] = {"key": key, "raw_result": raw_result}

    def get_answer_key(self, exam_id: str) -> AnswerKeyRecord | None:
        """Return an answer-key record, or ``None`` when it is not stored."""
        return self._answer_keys.get(exam_id)
