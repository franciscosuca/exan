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
                "grammar": {
                    "issues": [
                        {"original_text": "teh", "corrected_text": "the"},
                        {"original_text": "their going", "corrected_text": "they're going"},
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
            {"original_text": "teh", "corrected_text": "the"},
            {"original_text": "their going", "corrected_text": "they're going"},
        ],
        summary="The text has two small errors.",
    )
    assert result.summary == "The text has two small errors."
    assert "scores" not in result.model_dump()
    assert "overall_score" not in result.model_dump()
    assert len(provider.prompts) == 1
    assert '"grammar": {' in provider.prompts[0]
    assert '"original_text":' in provider.prompts[0]
    assert '"corrected_text":' in provider.prompts[0]
    assert "Issue found | Correction" not in provider.prompts[0]
    assert '"score"' not in provider.prompts[0]


@pytest.mark.asyncio
async def test_uses_correction_and_summary_languages_separately():
    provider = FakeProvider([{"grammar": {"issues": [], "summary": "Résumé."}}])

    with patch("app.services.batch_evaluation.write_run_log"):
        await _service(provider).evaluate(
            [_document()], "fake", "German", summary_language="French"
        )

    assert "in German" in provider.prompts[0]
    assert "Write the summary\nin French" in provider.prompts[0]


@pytest.mark.asyncio
async def test_evaluates_each_document_once_with_grammar():
    provider = FakeProvider(
        [
            {
                "grammar": {"issues": [], "summary": "First document."},
            },
            {
                "grammar": {"issues": [], "summary": "Second document."},
            },
        ]
    )

    with patch("app.services.batch_evaluation.write_run_log"):
        response = await _service(provider).evaluate(
            [_document("first.pdf"), _document("second.pdf")], "fake", "English"
        )

    assert [result.filename for result in response.results] == ["first.pdf", "second.pdf"]
    assert [result.summary for result in response.results] == [
        "First document.",
        "Second document.",
    ]
    assert all("scores" not in result.model_dump() for result in response.results)
    assert len(provider.prompts) == 2


@pytest.mark.asyncio
async def test_maps_empty_grammar_issue_list():
    provider = FakeProvider(
        [
            {
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
