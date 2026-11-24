"""Exam template, answer-key, and comparison workflow orchestration."""

import uuid
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Any

from ..models import AnswerKey, AnswerKeyUpdateItem, ComparisonResult, ExamStructure, StudentAnswer
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
    """Raised when comparison is requested before an answer key is stored."""


class ProviderAnalysisError(RuntimeError):
    """Raised when a provider cannot analyze a template or answer key."""


class ComparisonError(RuntimeError):
    """Raised when a provider cannot compare a student exam."""


class ExamComparisonService:
    """Orchestrate exam comparison without depending on HTTP routing."""

    def __init__(
        self,
        repository: ExamRepository,
        provider_factory: Callable[[str, str], BaseProvider],
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

    @staticmethod
    def _normalize_criteria(criteria: str | None) -> str | None:
        normalized = criteria.strip() if criteria else ""
        return normalized or None

    @staticmethod
    def _with_criteria(result: dict[str, Any], criteria: str | None) -> dict[str, Any]:
        scoped_result = dict(result)
        scoped_result["criteria"] = criteria
        return scoped_result

    async def upload_exam_template(
        self,
        document: UploadedDocument,
        provider_name: str,
        model: str,
        criteria: str | None = None,
    ) -> ExamStructure:
        """Analyze and store an empty exam template."""
        image_data, mime_types = self._images(document)
        normalized_criteria = self._normalize_criteria(criteria)
        try:
            provider = self.provider_factory(provider_name, model)
            if normalized_criteria is None:
                result = await provider.analyze_exam_structure(image_data, mime_types)
            else:
                result = await provider.analyze_exam_structure(
                    image_data,
                    mime_types,
                    normalized_criteria,
                )
        except Exception as exc:
            raise ProviderAnalysisError(f"AI analysis failed: {exc}") from exc

        raw_result = self._with_criteria(result, normalized_criteria)
        exam = ExamStructure(
            id=str(uuid.uuid4()),
            filename=document.filename,
            questions=result.get("questions", []),
            created_at=datetime.now(timezone.utc).isoformat(),
            criteria=normalized_criteria,
        )
        self.repository.save_exam(exam.id, exam.model_dump(), raw_result)
        return exam

    async def upload_answer_key(
        self,
        document: UploadedDocument,
        exam_id: str,
        provider_name: str,
        model: str,
    ) -> AnswerKey:
        """Analyze and store an answer key for an existing exam."""
        exam_data = self.repository.get_exam(exam_id)
        if exam_data is None:
            raise ExamNotFoundError("Exam not found")

        criteria = self._normalize_criteria(
            exam_data["structure"].get("criteria") or exam_data["raw_result"].get("criteria")
        )
        image_data, mime_types = self._images(document)
        try:
            provider = self.provider_factory(provider_name, model)
            if criteria is None:
                result = await provider.extract_answers(image_data, mime_types)
            else:
                result = await provider.extract_answers(image_data, mime_types, criteria)
        except Exception as exc:
            raise ProviderAnalysisError(f"AI analysis failed: {exc}") from exc

        raw_result = self._with_criteria(result, criteria)
        normalized = [
            {
                "question_number": answer.get("question_number"),
                "correct_answer": answer.get("correct_answer") or answer.get("answer", ""),
            }
            for answer in result.get("answers", [])
        ]
        answer_key = AnswerKey(
            id=str(uuid.uuid4()),
            exam_id=exam_id,
            answers=normalized,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.repository.save_answer_key(exam_id, answer_key.model_dump(), raw_result)
        return answer_key

    async def update_answer_key(
        self,
        exam_id: str,
        answers: Sequence[AnswerKeyUpdateItem],
    ) -> AnswerKey:
        """Persist user corrections for an already extracted answer key."""
        if self.repository.get_exam(exam_id) is None:
            raise ExamNotFoundError("Exam not found")
        if self.repository.get_answer_key(exam_id) is None:
            raise AnswerKeyNotFoundError("Answer key not uploaded yet")

        normalized_answers = [answer.model_dump() for answer in answers]
        raw_answers = [
            {
                "question_number": answer.question_number,
                "correct_answer": answer.correct_answer,
            }
            for answer in answers
        ]
        updated_record = self.repository.update_answer_key(
            exam_id,
            normalized_answers,
            raw_answers,
        )
        if updated_record is None:
            raise AnswerKeyNotFoundError("Answer key not uploaded yet")
        return AnswerKey(**updated_record["key"])

    async def compare_student_exams(
        self,
        documents: Sequence[UploadedDocument],
        exam_id: str,
        provider_name: str,
        model: str,
    ) -> list[ComparisonResult]:
        """Compare student documents against the stored exam and answer key."""
        exam_data = self.repository.get_exam(exam_id)
        if exam_data is None:
            raise ExamNotFoundError("Exam not found")
        answer_key_data = self.repository.get_answer_key(exam_id)
        if answer_key_data is None:
            raise AnswerKeyNotFoundError("Answer key not uploaded yet")

        criteria = self._normalize_criteria(
            exam_data["structure"].get("criteria") or exam_data["raw_result"].get("criteria")
        )
        raw_exam_result = self._with_criteria(exam_data["raw_result"], criteria)
        raw_answer_key_result = self._with_criteria(answer_key_data["raw_result"], criteria)

        try:
            provider = self.provider_factory(provider_name, model)
        except Exception as exc:
            raise ComparisonError(f"Comparison failed: {exc}") from exc

        results: list[ComparisonResult] = []
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
                comparison = await provider.compare_exam(
                    image_data,
                    mime_types,
                    raw_exam_result,
                    raw_answer_key_result,
                )
                outputs.append(
                    {
                        "operation": "compare_exam",
                        "filename": document.filename,
                        "elapsed_ms": elapsed_ms(call_started),
                        "output": comparison,
                    }
                )
            except Exception as exc:
                raise ComparisonError(f"Comparison failed for {document.filename}: {exc}") from exc

            answers = [StudentAnswer(**answer) for answer in comparison.get("answers", [])]
            results.append(
                ComparisonResult(
                    id=str(uuid.uuid4()),
                    exam_id=exam_id,
                    student_name=comparison.get("student_name"),
                    filename=document.filename,
                    answers=answers,
                )
            )

        write_run_log(
            "exam-comparison",
            input_snapshot={
                "exam_id": exam_id,
                "files": input_files,
                "exam_structure": raw_exam_result,
                "answer_key": raw_answer_key_result,
            },
            outputs=outputs,
            elapsed=elapsed_ms(run_started),
            provider=provider,
        )
        return results
