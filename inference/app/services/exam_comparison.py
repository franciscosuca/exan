"""Exam template, answer-key, and grading workflow orchestration."""

import uuid
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Any

from ..models import AnswerKey, ExamStructure, GradingResult, StudentAnswer
from ..providers import BaseProvider
from ..repositories.exam_repository import ExamRepository
from ..utils.file_processing import get_mime_type, process_upload
from ..utils.run_logging import elapsed_ms, start_timer, write_run_log
from . import UploadedDocument


class UploadProcessingError(ValueError):
    """Raised when an exam-comparison upload is unsupported or invalid."""


class ExamNotFoundError(LookupError):
    """Raised when an exam comparison operation references an unknown exam."""


class AnswerKeyNotFoundError(LookupError):
    """Raised when grading is requested before an answer key is stored."""


class ProviderAnalysisError(RuntimeError):
    """Raised when a provider cannot analyze a template or answer key."""


class GradingError(RuntimeError):
    """Raised when a provider cannot grade a student exam."""


class ExamComparisonService:
    """Orchestrate exam comparison without depending on HTTP routing."""

    def __init__(
        self,
        repository: ExamRepository,
        provider_factory: Callable[[str], BaseProvider],
    ) -> None:
        self.repository = repository
        self.provider_factory = provider_factory

    @staticmethod
    def _images(document: UploadedDocument) -> tuple[list[bytes], list[str]]:
        mime = get_mime_type(document.filename, document.content_type)
        try:
            images = process_upload(document.content, mime)
        except ValueError as exc:
            raise UploadProcessingError(str(exc)) from exc
        return [image for image, _ in images], [image_mime for _, image_mime in images]

    async def upload_exam_template(
        self,
        document: UploadedDocument,
        provider_name: str,
    ) -> ExamStructure:
        """Analyze and store an empty exam template."""
        image_data, mime_types = self._images(document)
        try:
            provider = self.provider_factory(provider_name)
            result = await provider.analyze_exam_structure(image_data, mime_types)
        except Exception as exc:
            raise ProviderAnalysisError(f"AI analysis failed: {exc}") from exc

        exam = ExamStructure(
            id=str(uuid.uuid4()),
            filename=document.filename,
            questions=result.get("questions", []),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.repository.save_exam(exam.id, exam.model_dump(), result)
        return exam

    async def upload_answer_key(
        self,
        document: UploadedDocument,
        exam_id: str,
        provider_name: str,
    ) -> AnswerKey:
        """Analyze and store an answer key for an existing exam."""
        if self.repository.get_exam(exam_id) is None:
            raise ExamNotFoundError("Exam not found")

        image_data, mime_types = self._images(document)
        try:
            provider = self.provider_factory(provider_name)
            result = await provider.extract_answers(image_data, mime_types)
        except Exception as exc:
            raise ProviderAnalysisError(f"AI analysis failed: {exc}") from exc

        normalized = [
            {
                "question_number": answer.get("question_number"),
                "correct_answer": answer.get("correct_answer") or answer.get("answer", ""),
                "points": answer.get("points", 1),
            }
            for answer in result.get("answers", [])
        ]
        answer_key = AnswerKey(
            id=str(uuid.uuid4()),
            exam_id=exam_id,
            answers=normalized,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.repository.save_answer_key(exam_id, answer_key.model_dump(), result)
        return answer_key

    async def grade_student_exams(
        self,
        documents: Sequence[UploadedDocument],
        exam_id: str,
        provider_name: str,
    ) -> list[GradingResult]:
        """Grade student documents against the stored exam and answer key."""
        exam_data = self.repository.get_exam(exam_id)
        if exam_data is None:
            raise ExamNotFoundError("Exam not found")
        answer_key_data = self.repository.get_answer_key(exam_id)
        if answer_key_data is None:
            raise AnswerKeyNotFoundError("Answer key not uploaded yet")

        try:
            provider = self.provider_factory(provider_name)
        except Exception as exc:
            raise GradingError(f"Grading failed: {exc}") from exc

        results: list[GradingResult] = []
        run_started = start_timer()
        outputs: list[dict[str, Any]] = []
        input_files = []

        for document in documents:
            mime = get_mime_type(document.filename, document.content_type)
            input_files.append(
                {
                    "filename": document.filename,
                    "mime_type": mime,
                    "bytes": len(document.content),
                }
            )
            try:
                images = process_upload(document.content, mime)
            except ValueError as exc:
                raise UploadProcessingError(f"File {document.filename}: {exc}") from exc

            image_data = [image for image, _ in images]
            mime_types = [image_mime for _, image_mime in images]
            try:
                call_started = start_timer()
                grading = await provider.grade_exam(
                    image_data,
                    mime_types,
                    exam_data["raw_result"],
                    answer_key_data["raw_result"],
                )
                outputs.append(
                    {
                        "operation": "grade_exam",
                        "filename": document.filename,
                        "elapsed_ms": elapsed_ms(call_started),
                        "output": grading,
                    }
                )
            except Exception as exc:
                raise GradingError(f"Grading failed for {document.filename}: {exc}") from exc

            answers = [StudentAnswer(**answer) for answer in grading.get("answers", [])]
            total = sum(answer.points_earned for answer in answers)
            max_score = sum(answer.points_possible for answer in answers)
            results.append(
                GradingResult(
                    id=str(uuid.uuid4()),
                    exam_id=exam_id,
                    student_name=grading.get("student_name"),
                    filename=document.filename,
                    total_score=total,
                    max_score=max_score,
                    percentage=(total / max_score * 100) if max_score > 0 else 0,
                    answers=answers,
                )
            )

        write_run_log(
            "exam-comparison",
            input_snapshot={
                "exam_id": exam_id,
                "files": input_files,
                "exam_structure": exam_data["raw_result"],
                "answer_key": answer_key_data["raw_result"],
            },
            outputs=outputs,
            elapsed=elapsed_ms(run_started),
            provider=provider,
        )
        return results
