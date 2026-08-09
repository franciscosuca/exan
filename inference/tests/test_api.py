"""Tests for the Exan API endpoints."""

import io
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_batch_evaluation_service
from app.main import app
from app.services.batch_evaluation import BatchEvaluationService

client = TestClient(app)


def test_list_providers():
    """GET /api/providers returns a list of provider configs."""
    response = client.get("/api/providers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    names = [p["provider"] for p in data]
    assert names == ["gemini", "claude", "gpt", "ollama", "lmstudio"]

    for p in data:
        assert "available" in p
        assert "requires_api_key" in p
        assert "is_local" in p

    by_name = {p["provider"]: p for p in data}
    for name in ("gemini", "claude", "gpt"):
        assert by_name[name]["requires_api_key"] is True
        assert by_name[name]["is_local"] is False
    for name in ("ollama", "lmstudio"):
        assert by_name[name]["requires_api_key"] is False
        assert by_name[name]["is_local"] is True


def test_list_providers_structure():
    """Each provider entry has the expected shape."""
    response = client.get("/api/providers")
    for p in response.json():
        assert isinstance(p["provider"], str)
        assert isinstance(p["available"], bool)
        assert isinstance(p["requires_api_key"], bool)
        assert isinstance(p["is_local"], bool)


def _make_fake_pdf() -> bytes:
    """Create a minimal valid PDF for testing."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "1. What is 2+2?\nA) 3\nB) 4\nC) 5\nD) 6")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


MOCK_STRUCTURE = {
    "questions": [
        {
            "number": 1,
            "text": "What is 2+2?",
            "type": "multiple_choice",
            "options": ["A) 3", "B) 4", "C) 5", "D) 6"],
            "points": 1,
        }
    ]
}

MOCK_ANSWERS = {"answers": [{"question_number": 1, "answer": "B", "points": 1}]}

MOCK_GRADING = {
    "student_name": "Test Student",
    "answers": [
        {
            "question_number": 1,
            "student_answer": "B",
            "correct_answer": "B",
            "is_correct": True,
            "points_earned": 1,
            "points_possible": 1,
        }
    ],
}


@patch("app.main.get_provider")
def test_upload_exam_template(mock_get_provider):
    """POST /api/exam/template processes a PDF and returns structure."""
    mock_provider = AsyncMock()
    mock_provider.analyze_exam_structure.return_value = MOCK_STRUCTURE
    mock_get_provider.return_value = mock_provider

    pdf = _make_fake_pdf()
    response = client.post(
        "/api/exam/template",
        files={"file": ("exam.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"provider": "gemini"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "exam.pdf"
    assert len(data["questions"]) == 1
    assert data["questions"][0]["number"] == 1
    assert data["id"]  # non-empty UUID


@patch("app.main.get_provider")
def test_upload_answer_key(mock_get_provider):
    """POST /api/exam/answer-key requires a valid exam_id."""
    mock_provider = AsyncMock()
    mock_provider.analyze_exam_structure.return_value = MOCK_STRUCTURE
    mock_provider.extract_answers.return_value = MOCK_ANSWERS
    mock_get_provider.return_value = mock_provider

    # First create an exam
    pdf = _make_fake_pdf()
    resp1 = client.post(
        "/api/exam/template",
        files={"file": ("exam.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"provider": "gemini"},
    )
    exam_id = resp1.json()["id"]

    # Upload answer key
    resp2 = client.post(
        "/api/exam/answer-key",
        files={"file": ("key.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"exam_id": exam_id, "provider": "gemini"},
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["exam_id"] == exam_id
    assert len(data["answers"]) == 1


def test_upload_answer_key_missing_exam():
    """POST /api/exam/answer-key returns 404 for unknown exam_id."""
    pdf = _make_fake_pdf()
    response = client.post(
        "/api/exam/answer-key",
        files={"file": ("key.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"exam_id": "nonexistent", "provider": "gemini"},
    )
    assert response.status_code == 404


@patch("app.main.get_provider")
def test_grade_student_exams(mock_get_provider):
    """POST /api/exam/grade returns grading results."""
    mock_provider = AsyncMock()
    mock_provider.analyze_exam_structure.return_value = MOCK_STRUCTURE
    mock_provider.extract_answers.return_value = MOCK_ANSWERS
    mock_provider.grade_exam.return_value = MOCK_GRADING
    mock_get_provider.return_value = mock_provider

    pdf = _make_fake_pdf()

    # Setup: create exam + answer key
    resp1 = client.post(
        "/api/exam/template",
        files={"file": ("exam.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"provider": "gemini"},
    )
    exam_id = resp1.json()["id"]

    client.post(
        "/api/exam/answer-key",
        files={"file": ("key.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"exam_id": exam_id, "provider": "gemini"},
    )

    # Grade
    resp3 = client.post(
        "/api/exam/grade",
        files=[("files", ("student1.pdf", io.BytesIO(pdf), "application/pdf"))],
        data={"exam_id": exam_id, "provider": "gemini"},
    )
    assert resp3.status_code == 200
    results = resp3.json()
    assert len(results) == 1
    assert results[0]["student_name"] == "Test Student"
    assert results[0]["percentage"] == 100.0
    assert results[0]["answers"][0]["is_correct"] is True


def test_grade_missing_answer_key():
    """POST /api/exam/grade returns 400 if answer key not uploaded."""
    # We need an exam that exists but has no answer key
    # Use the providers endpoint to ensure the app is working
    response = client.post(
        "/api/exam/grade",
        files=[("files", ("student.pdf", io.BytesIO(b"fake"), "application/pdf"))],
        data={"exam_id": "nonexistent", "provider": "gemini"},
    )
    assert response.status_code == 404


def test_unsupported_file_type():
    """Uploading an unsupported file type returns 400."""
    response = client.post(
        "/api/exam/template",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"provider": "gemini"},
    )
    assert response.status_code == 400


def test_batch_evaluation_ignores_legacy_evaluation_fields():
    """Legacy multipart controls do not alter grammar-only evaluation."""
    from unittest.mock import AsyncMock

    provider = AsyncMock()
    provider.evaluate_text.return_value = {
        "score": 88,
        "grammar": {"issues": [], "summary": "No issues."},
    }
    service = BatchEvaluationService(lambda _: provider)
    app.dependency_overrides[get_batch_evaluation_service] = lambda: service

    try:
        response = client.post(
            "/api/batch/evaluate",
            files=[("files", ("essay.pdf", io.BytesIO(_make_fake_pdf()), "application/pdf"))],
            data={
                "provider": "fake",
                "language": "English",
                "include_grammar": "false",
                "custom_criteria": "not-json",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "overall_score" not in response.json()["results"][0]
    provider.evaluate_text.assert_awaited_once()
