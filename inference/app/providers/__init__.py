"""AI provider abstraction layer.

Each provider implements the same interface for:
1. Analyzing exam structure from images/PDFs
2. Extracting answers from filled exams
3. Comparing student answers against answer keys
4. Evaluating text against criteria (batch evaluation)
"""

from abc import ABC, abstractmethod
from typing import Any


class ProviderResponse(dict):
    """Parsed provider output with non-invasive per-call metadata."""

    def __init__(self, data: dict, *, usage: Any = None):
        super().__init__(data)
        self.usage = usage


class BaseProvider(ABC):
    """Base class for all AI providers."""

    name: str

    @staticmethod
    def _with_metadata(result: dict, response: Any) -> ProviderResponse:
        """Keep the parsed dict contract while retaining response token usage."""
        if isinstance(response, dict):
            usage = response.get("usage")
        else:
            usage = getattr(response, "usage", None) or getattr(response, "usage_metadata", None)
        if usage is not None and hasattr(usage, "model_dump"):
            usage = usage.model_dump()
        elif usage is not None and not isinstance(usage, (dict, list, str, int, float, bool)):
            usage = vars(usage)
        if usage is None and isinstance(response, dict):
            usage = {
                key: response[key]
                for key in ("prompt_eval_count", "eval_count")
                if key in response
            } or None
        return ProviderResponse(result, usage=usage)

    @abstractmethod
    async def analyze_exam_structure(self, image_data: list[bytes], mime_types: list[str]) -> dict:
        """Analyze an exam image/PDF and return its structure.

        Returns dict with 'questions' list, each having:
        - number, text, type, options (if applicable), points
        """

    @abstractmethod
    async def extract_answers(self, image_data: list[bytes], mime_types: list[str]) -> dict:
        """Extract filled-in answers from an exam image/PDF.

        Returns dict with 'answers' list, each having:
        - question_number, answer, points
        """

    @abstractmethod
    async def grade_exam(
        self,
        student_images: list[bytes],
        student_mime_types: list[str],
        exam_structure: dict,
        answer_key: dict,
    ) -> dict:
        """Grade a student's exam against the answer key.

        Returns dict with:
        - student_name (if detectable), answers list with correctness
        """

    @abstractmethod
    async def evaluate_text(self, text: str, prompt: str) -> dict:
        """Evaluate text using a given prompt.

        Returns dict with:
        - score (0-100), feedback (string)
        """
