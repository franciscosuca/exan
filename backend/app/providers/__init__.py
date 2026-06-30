"""AI provider abstraction layer.

Each provider implements the same interface for:
1. Analyzing exam structure from images/PDFs
2. Extracting answers from filled exams
3. Comparing student answers against answer keys
"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Base class for all AI providers."""

    name: str

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
