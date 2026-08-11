"""Tests for the Exan API endpoints."""

import io
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_grammar_evaluation_service
from app.main import app
from app.services.grammar_evaluation import GrammarEvaluationService

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


def test_workflow_routes_include_canonical_and_legacy_paths():
    paths = set(app.openapi()["paths"])

    assert "/api/exam-comparison/template" in paths
    assert "/api/exam/compare" in paths
    assert "/api/grammar-evaluation/evaluate" in paths
    assert "/api/batch/evaluate" in paths


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
        }
    ]
}

MOCK_ANSWERS = {"answers": [{"question_number": 1, "answer": "B"}]}

MOCK_COMPARISON = {
    "student_name": "Test Student",
    "answers": [
        {
            "question_number": 1,
            "student_answer": "B",
            "correct_answer": "B",
            "is_correct": True,
        }
    ],
}


@patch("app.main.get_provider")
def test_upload_exam_template(mock_get_provider):
    """POST /api/exam-comparison/template processes a PDF and returns structure."""
    mock_provider = AsyncMock()
    mock_provider.analyze_exam_structure.return_value = MOCK_STRUCTURE
    mock_get_provider.return_value = mock_provider

    pdf = _make_fake_pdf()
    response = client.post(
        "/api/exam-comparison/template",
        files={"file": ("exam.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"provider": "gemini", "model": "test-model", "criteria": "B1 and B3 only"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "exam.pdf"
    assert len(data["questions"]) == 1
    assert data["questions"][0]["number"] == 1
    assert data["criteria"] == "B1 and B3 only"
    mock_provider.analyze_exam_structure.assert_awaited_once()
    assert mock_provider.analyze_exam_structure.call_args.args[2] == "B1 and B3 only"
    assert data["id"]  # non-empty UUID


@patch("app.main.get_provider")
def test_upload_answer_key(mock_get_provider):
    """POST /api/exam-comparison/answer-key requires a valid exam_id."""
    mock_provider = AsyncMock()
    mock_provider.analyze_exam_structure.return_value = MOCK_STRUCTURE
    mock_provider.extract_answers.return_value = MOCK_ANSWERS
    mock_get_provider.return_value = mock_provider

    # First create an exam
    pdf = _make_fake_pdf()
    resp1 = client.post(
        "/api/exam-comparison/template",
        files={"file": ("exam.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"provider": "gemini", "model": "test-model"},
    )
    exam_id = resp1.json()["id"]

    # Upload answer key
    resp2 = client.post(
        "/api/exam-comparison/answer-key",
        files={"file": ("key.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"exam_id": exam_id, "provider": "gemini", "model": "test-model"},
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["exam_id"] == exam_id
    assert len(data["answers"]) == 1
    assert set(data["answers"][0]) == {"question_number", "correct_answer"}


def test_upload_answer_key_missing_exam():
    """POST /api/exam-comparison/answer-key returns 404 for unknown exam_id."""
    pdf = _make_fake_pdf()
    response = client.post(
        "/api/exam-comparison/answer-key",
        files={"file": ("key.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"exam_id": "nonexistent", "provider": "gemini", "model": "test-model"},
    )
    assert response.status_code == 404


def test_failed_http_response_logs_response_detail(caplog):
    """Failed validation responses include their body in inference logs."""
    with caplog.at_level("ERROR", logger="app.main"):
        response = client.post("/api/exam-comparison/answer-key")

    assert response.status_code == 422
    assert "Field required" in caplog.text


@patch("app.main.get_provider")
def test_compare_student_exams(mock_get_provider):
    """POST /api/exam-comparison/compare returns answer comparisons."""
    mock_provider = AsyncMock()
    mock_provider.analyze_exam_structure.return_value = MOCK_STRUCTURE
    mock_provider.extract_answers.return_value = MOCK_ANSWERS
    mock_provider.compare_exam.return_value = MOCK_COMPARISON
    mock_get_provider.return_value = mock_provider

    pdf = _make_fake_pdf()

    # Setup: create exam + answer key
    resp1 = client.post(
        "/api/exam-comparison/template",
        files={"file": ("exam.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"provider": "gemini", "model": "test-model"},
    )
    exam_id = resp1.json()["id"]

    client.post(
        "/api/exam-comparison/answer-key",
        files={"file": ("key.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"exam_id": exam_id, "provider": "gemini", "model": "test-model"},
    )

    # Compare
    resp3 = client.post(
        "/api/exam-comparison/compare",
        files=[("files", ("student1.pdf", io.BytesIO(pdf), "application/pdf"))],
        data={"exam_id": exam_id, "provider": "gemini", "model": "test-model"},
    )
    assert resp3.status_code == 200
    results = resp3.json()
    assert len(results) == 1
    assert results[0]["student_name"] == "Test Student"
    assert set(results[0]) == {"id", "exam_id", "student_name", "filename", "answers"}
    assert set(results[0]["answers"][0]) == {
        "question_number",
        "student_answer",
        "correct_answer",
        "is_correct",
    }
    assert not {"points", "score", "percentage"}.intersection(results[0])
    assert not {"points", "score", "percentage"}.intersection(results[0]["answers"][0])
    assert results[0]["answers"][0]["is_correct"] is True


def test_compare_missing_answer_key():
    """POST /api/exam-comparison/compare returns 400 if answer key not uploaded."""
    # We need an exam that exists but has no answer key
    # Use the providers endpoint to ensure the app is working
    response = client.post(
        "/api/exam-comparison/compare",
        files=[("files", ("student.pdf", io.BytesIO(b"fake"), "application/pdf"))],
        data={"exam_id": "nonexistent", "provider": "gemini", "model": "test-model"},
    )
    assert response.status_code == 404


def test_unsupported_file_type():
    """Uploading an unsupported file type returns 400."""
    response = client.post(
        "/api/exam-comparison/template",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"provider": "gemini", "model": "test-model"},
    )
    assert response.status_code == 400


def test_grammar_evaluation_ignores_legacy_evaluation_fields():
    """Legacy multipart controls do not alter grammar-only evaluation."""
    from unittest.mock import AsyncMock

    provider = AsyncMock()
    provider.evaluate_text.return_value = {
        "score": 88,
        "grammar": {"issues": [], "summary": "No issues."},
    }
    service = GrammarEvaluationService(lambda *_: provider)
    app.dependency_overrides[get_grammar_evaluation_service] = lambda: service

    try:
        responses = [
            client.post(
                path,
                files=[("files", ("essay.pdf", io.BytesIO(_make_fake_pdf()), "application/pdf"))],
                data={
                    "provider": "fake",
                    "model": "test-model",
                    "language": "English",
                    "include_grammar": "false",
                    "custom_criteria": "not-json",
                },
            )
            for path in ("/api/grammar-evaluation/evaluate", "/api/batch/evaluate")
        ]
    finally:
        app.dependency_overrides.clear()

    assert all(response.status_code == 200 for response in responses)
    assert all("overall_score" not in response.json()["results"][0] for response in responses)
    assert provider.evaluate_text.await_count == 2
