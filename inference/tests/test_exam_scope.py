from unittest.mock import AsyncMock

import pytest

from app.providers.prompts import (
    analyze_exam_structure_prompt,
    compare_exam_prompt,
    extract_answers_prompt,
)
from app.repositories.exam_repository import ExamRepository
from app.services import UploadedDocument, exam_comparison
from app.services.exam_comparison import ExamComparisonService


@pytest.mark.asyncio
async def test_exam_criteria_is_carried_through_the_workflow(monkeypatch) -> None:
    provider = AsyncMock()
    provider.analyze_exam_structure.return_value = {
        "questions": [
            {"number": "B1", "text": "First exercise", "type": "open_ended"},
        ]
    }
    provider.extract_answers.return_value = {"answers": [{"question_number": "B1", "answer": "Ja"}]}
    provider.compare_exam.return_value = {
        "answers": [
            {
                "question_number": "B1",
                "student_answer": "Ja",
                "correct_answer": "Ja",
                "is_correct": True,
            }
        ]
    }
    repository = ExamRepository()
    service = ExamComparisonService(repository, lambda *_: provider)
    monkeypatch.setattr(
        exam_comparison,
        "process_upload",
        lambda content, mime: [(b"image", "image/png")],
    )
    monkeypatch.setattr(exam_comparison, "write_run_log", lambda *args, **kwargs: None)

    template = UploadedDocument(b"template", "exam.pdf", "application/pdf")
    exam = await service.upload_exam_template(
        template,
        "stub",
        "test-model",
        "  B1 and B3 only  ",
    )

    assert exam.criteria == "B1 and B3 only"
    assert provider.analyze_exam_structure.call_args.args[2] == "B1 and B3 only"
    stored_exam = repository.get_exam(exam.id)
    assert stored_exam is not None
    assert stored_exam["raw_result"]["criteria"] == "B1 and B3 only"

    await service.upload_answer_key(
        UploadedDocument(b"answer key", "key.pdf", "application/pdf"),
        exam.id,
        "stub",
        "test-model",
    )

    assert provider.extract_answers.call_args.args[2] == "B1 and B3 only"
    stored_answer_key = repository.get_answer_key(exam.id)
    assert stored_answer_key is not None
    assert stored_answer_key["raw_result"]["criteria"] == "B1 and B3 only"

    await service.compare_student_exams(
        [UploadedDocument(b"student", "student.pdf", "application/pdf")],
        exam.id,
        "stub",
        "test-model",
    )

    comparison_exam = provider.compare_exam.call_args.args[2]
    comparison_answer_key = provider.compare_exam.call_args.args[3]
    assert comparison_exam["criteria"] == "B1 and B3 only"
    assert comparison_answer_key["criteria"] == "B1 and B3 only"


def test_scoped_prompts_require_excluding_other_sections() -> None:
    criteria = "B1 and B3 only"

    for prompt in (
        analyze_exam_structure_prompt(criteria),
        extract_answers_prompt(criteria),
        compare_exam_prompt({"criteria": criteria}, {"criteria": criteria}),
    ):
        assert "MANDATORY EVALUATION SCOPE" in prompt
        assert criteria in prompt
        assert "Ignore all other visible content" in prompt
        assert "Do not include, extract, or compare any out-of-scope section" in prompt
