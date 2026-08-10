"""AI provider abstraction layer.

Each provider implements the same interface for:
1. Analyzing exam structure from images/PDFs
2. Extracting answers from filled exams
3. Comparing student answers against answer keys
4. Evaluating text for grammar feedback (batch evaluation)
"""

import re
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
        """Keep the parsed dict contract while retaining response token usage.

        Evaluation feedback is returned directly to end users.  Providers
        occasionally put Markdown formatting in the JSON string, while the
        API presents that string as plain text.  Normalize it at the common
        provider boundary so every provider has the same output contract.
        """
        if isinstance(result.get("feedback"), str):
            result = dict(result)
            result["feedback"] = BaseProvider._normalize_feedback(result["feedback"])

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
                key: response[key] for key in ("prompt_eval_count", "eval_count") if key in response
            } or None
        return ProviderResponse(result, usage=usage)

    @staticmethod
    def _normalize_feedback(feedback: str) -> str:
        """Remove Markdown-only decoration while preserving readable text."""
        feedback = feedback.replace("\r\n", "\n").replace("\r", "\n")
        feedback = re.sub(r"```(?:[A-Za-z0-9_-]+)?\s*", "", feedback)
        feedback = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", feedback)
        feedback = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", feedback)
        feedback = feedback.replace("**", "").replace("__", "").replace("`", "")
        feedback = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", feedback)
        feedback = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", feedback)
        feedback = re.sub(r"(?m)^\s*[*+]\s+", "- ", feedback)
        feedback = re.sub(r"[ \t]+", " ", feedback)
        feedback = re.sub(r"\n[ \t]+", "\n", feedback)
        feedback = re.sub(r"\n{3,}", "\n\n", feedback)
        return feedback.strip()

    @abstractmethod
    async def analyze_exam_structure(
        self,
        image_data: list[bytes],
        mime_types: list[str],
        criteria: str | None = None,
    ) -> dict:
        """Analyze an exam image/PDF and return its structure.

        Returns dict with 'questions' list, each having:
        - number, text, type, options (if applicable)
        """

    @abstractmethod
    async def extract_answers(
        self,
        image_data: list[bytes],
        mime_types: list[str],
        criteria: str | None = None,
    ) -> dict:
        """Extract filled-in answers from an exam image/PDF.

        Returns dict with 'answers' list, each having:
        - question_number, answer
        """

    @abstractmethod
    async def compare_exam(
        self,
        student_images: list[bytes],
        student_mime_types: list[str],
        exam_structure: dict,
        answer_key: dict,
    ) -> dict:
        """Compare a student's exam against the answer key.

        Returns dict with:
        - student_name (if detectable), answers list with correctness
        """

    @abstractmethod
    async def evaluate_text(self, text: str, prompt: str) -> dict:
        """Evaluate text using a given prompt.

        Returns a parsed provider response for the requested evaluation.
        """
