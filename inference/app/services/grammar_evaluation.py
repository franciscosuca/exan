"""Grammar evaluation workflow orchestration."""

import uuid
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Any, Mapping

from pydantic import ValidationError

from ..models import FileEvaluationResult, GrammarEvaluationResponse, GrammarFeedback
from ..providers import BaseProvider
from ..providers.prompts import grammar_evaluation_prompt
from ..utils.file_processing import extract_text, get_mime_type
from ..utils.run_logging import elapsed_ms, start_timer, write_run_log
from . import UploadedDocument


class GrammarUploadProcessingError(ValueError):
    """Raised when a grammar-evaluation document cannot be converted to text."""


class GrammarEvaluationError(RuntimeError):
    """Raised when a provider cannot complete a grammar evaluation."""


def _parse_grammar_result(result: Mapping[str, Any]) -> GrammarFeedback:
    """Validate a grammar provider response before mapping it to API models."""
    try:
        grammar = GrammarFeedback.model_validate(result["grammar"])
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise ValueError(f"Malformed grammar response: {exc}") from exc
    return grammar


class GrammarEvaluationService:
    """Orchestrate grammar evaluation without depending on HTTP routing."""

    def __init__(self, provider_factory: Callable[[str, str], BaseProvider]) -> None:
        self.provider_factory = provider_factory

    async def evaluate(
        self,
        documents: Sequence[UploadedDocument],
        provider_name: str,
        model: str,
        language: str = "en",
        summary_language: str | None = None,
        correction_language: str | None = None,
    ) -> GrammarEvaluationResponse:
        """Evaluate each document for grammar.

        ``language`` is retained for callers of the original API and means
        the language used for corrections and issues.  The explicit
        ``correction_language`` takes precedence when supplied.
        """
        correction_language = correction_language or language
        summary_language = summary_language or correction_language
        try:
            provider = self.provider_factory(provider_name, model)
        except Exception as exc:
            raise GrammarEvaluationError(f"Grammar evaluation failed: {exc}") from exc

        results: list[FileEvaluationResult] = []
        run_started = start_timer()
        outputs: list[dict[str, Any]] = []
        input_files = []

        for document in documents:
            mime = get_mime_type(document.filename, document.content_type)
            try:
                text = extract_text(document.content, mime)
            except ValueError as exc:
                raise GrammarUploadProcessingError(f"File {document.filename}: {exc}") from exc

            if not text.strip():
                raise GrammarUploadProcessingError(
                    f"File {document.filename}: No text content could be extracted"
                )
            input_files.append(
                {
                    "filename": document.filename,
                    "mime_type": mime,
                    "bytes": len(document.content),
                    "text_preview": text[:500],
                }
            )

            grammar_feedback: GrammarFeedback | None = None
            try:
                prompt = grammar_evaluation_prompt(correction_language, summary_language)
                call_started = start_timer()
                result = await provider.evaluate_text(text, prompt)
                outputs.append(
                    {
                        "operation": "grammar",
                        "filename": document.filename,
                        "elapsed_ms": elapsed_ms(call_started),
                        "output": result,
                    }
                )
                grammar_feedback = _parse_grammar_result(result)
            except Exception as exc:
                raise GrammarEvaluationError(
                    f"Grammar evaluation failed for {document.filename}: {exc}"
                ) from exc

            results.append(
                FileEvaluationResult(
                    id=str(uuid.uuid4()),
                    filename=document.filename,
                    summary=grammar_feedback.summary,
                    grammar=grammar_feedback,
                )
            )

        response = GrammarEvaluationResponse(
            id=str(uuid.uuid4()),
            results=results,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        write_run_log(
            "grammar-evaluation",
            input_snapshot={
                "language": correction_language,
                "correction_language": correction_language,
                "summary_language": summary_language,
                "files": input_files,
            },
            outputs=outputs,
            elapsed=elapsed_ms(run_started),
            provider=provider,
        )
        return response
