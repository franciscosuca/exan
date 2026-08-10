from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_exam_comparison_service
from app.main import app
from app.models import Answer, Question, StudentAnswer
from app.repositories.exam_repository import ExamRepository
from app.services import UploadedDocument, exam_comparison
from app.services.exam_comparison import ExamComparisonService


class AnswerKeyProvider:
    name = "stub"

    async def extract_answers(self, image_data: list[bytes], mime_types: list[str]) -> dict:
        return {
            "answers": [
                {"question_number": "B3a", "correct_answer": "A"},
            ]
        }


class ComparisonProvider:
    name = "stub"

    async def compare_exam(
        self,
        student_images: list[bytes],
        student_mime_types: list[str],
        exam_structure: dict,
        answer_key: dict,
    ) -> dict:
        return {
            "answers": [
                {
                    "question_number": "B3a",
                    "student_answer": "A",
                    "correct_answer": "A",
                    "is_correct": True,
                }
            ]
        }


def test_question_identifiers_preserve_numeric_values_and_accept_labels() -> None:
    assert Question(number=3, text="x", type="open_ended").number == 3
    assert isinstance(Answer(question_number=3, correct_answer="x").question_number, int)
    assert (
        StudentAnswer(
            question_number=3,
            student_answer="x",
            correct_answer="x",
            is_correct=True,
        ).question_number
        == 3
    )
    assert Question(number="B3a", text="x", type="open_ended").number == "B3a"


async def test_answer_key_endpoint_accepts_alphanumeric_question_numbers(monkeypatch) -> None:
    repository = ExamRepository()
    repository.save_exam("exam-1", {"id": "exam-1"}, {})
    service = ExamComparisonService(repository, lambda *_: AnswerKeyProvider())

    monkeypatch.setattr(
        ExamComparisonService,
        "_images",
        staticmethod(lambda document: ([b"image"], ["image/png"])),
    )
    app.dependency_overrides[get_exam_comparison_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/exam/answer-key",
                files={"file": ("answer-key.png", b"content", "image/png")},
                data={"exam_id": "exam-1", "provider": "stub", "model": "test-model"},
            )
    finally:
        app.dependency_overrides.pop(get_exam_comparison_service, None)

    assert response.status_code == 200
    assert response.json()["answers"][0]["question_number"] == "B3a"


async def test_comparison_accepts_alphanumeric_question_numbers(monkeypatch) -> None:
    repository = ExamRepository()
    repository.save_exam("exam-1", {"id": "exam-1"}, {})
    repository.save_answer_key("exam-1", {"answers": []}, {})
    service = ExamComparisonService(repository, lambda *_: ComparisonProvider())
    monkeypatch.setattr(
        exam_comparison,
        "process_upload",
        lambda content, mime: [(b"image", "image/png")],
    )

    results = await service.compare_student_exams(
        [UploadedDocument(b"content", "student.png", "image/png")],
        "exam-1",
        "stub",
        "test-model",
    )

    assert results[0].answers[0].question_number == "B3a"
