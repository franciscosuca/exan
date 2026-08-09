"""Tests for structured grammar batch evaluation results."""

from unittest.mock import patch

import fitz
import pytest

from app.models import GrammarFeedback
from app.services import UploadedDocument
from app.services.batch_evaluation import BatchEvaluationError, BatchEvaluationService


class FakeProvider:
    def __init__(self, results):
        self.results = iter(results)
        self.prompts = []

    async def evaluate_text(self, text, prompt):
        self.prompts.append(prompt)
        return next(self.results)


def _make_pdf(text: str = "A short document.") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def _document(filename: str = "document.pdf") -> UploadedDocument:
    return UploadedDocument(
        content=_make_pdf(),
        filename=filename,
        content_type="application/pdf",
    )


def _service(provider: FakeProvider) -> BatchEvaluationService:
    return BatchEvaluationService(lambda _: provider)


@pytest.mark.asyncio
async def test_maps_grammar_issues_and_summary():
    provider = FakeProvider(
        [
            {
                "score": 78,
                "grammar": {
                    "issues": [
                        {"issue": "teh", "correction": "the"},
                        {"issue": "their going", "correction": "they're going"},
                    ],
                    "summary": "The text has two small errors.",
                },
            }
        ]
    )

    with patch("app.services.batch_evaluation.write_run_log"):
        response = await _service(provider).evaluate([_document()], "fake", "English")

    result = response.results[0]
    assert result.grammar == GrammarFeedback(
        issues=[
            {"issue": "teh", "correction": "the"},
            {"issue": "their going", "correction": "they're going"},
        ],
        summary="The text has two small errors.",
    )
    assert result.scores[0].criteria_name == "Grammar"
    assert result.scores[0].score == 78
    assert result.scores[0].feedback == ""
    assert "overall_score" not in result.model_dump()
    assert len(provider.prompts) == 1
    assert '"grammar": {' in provider.prompts[0]
    assert "Issue found | Correction" not in provider.prompts[0]


@pytest.mark.asyncio
async def test_evaluates_each_document_once_with_grammar():
    provider = FakeProvider(
        [
            {
                "score": 78,
                "grammar": {"issues": [], "summary": "First document."},
            },
            {
                "score": 62,
                "grammar": {"issues": [], "summary": "Second document."},
            },
        ]
    )

    with patch("app.services.batch_evaluation.write_run_log"):
        response = await _service(provider).evaluate(
            [_document("first.pdf"), _document("second.pdf")], "fake", "English"
        )

    assert [result.filename for result in response.results] == ["first.pdf", "second.pdf"]
    assert [result.scores[0].score for result in response.results] == [78, 62]
    assert len(provider.prompts) == 2


@pytest.mark.asyncio
async def test_maps_empty_grammar_issue_list():
    provider = FakeProvider(
        [
            {
                "score": 100,
                "grammar": {"issues": [], "summary": "No grammar issues found."},
            }
        ]
    )

    with patch("app.services.batch_evaluation.write_run_log"):
        response = await _service(provider).evaluate(
            [_document("empty-issues.pdf")], "fake", "English"
        )

    grammar = response.results[0].grammar
    assert grammar is not None
    assert grammar.issues == []
    assert grammar.summary == "No grammar issues found."


@pytest.mark.asyncio
async def test_malformed_grammar_output_raises_batch_evaluation_error():
    provider = FakeProvider(
        [
            {
                "score": 85,
                "grammar": {
                    "issues": [{"issue": "missing correction"}],
                    "summary": "Incomplete issue.",
                },
            }
        ]
    )

    with pytest.raises(
        BatchEvaluationError,
        match="Grammar evaluation failed for malformed.pdf: Malformed grammar response",
    ):
        await _service(provider).evaluate([_document("malformed.pdf")], "fake", "English")
