"""Grammar evaluation HTTP routes."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ...models import GrammarEvaluationResponse
from ...services import UploadedDocument
from ...services.grammar_evaluation import (
    GrammarEvaluationError,
    GrammarEvaluationService,
    GrammarUploadProcessingError,
)
from ..dependencies import get_grammar_evaluation_service

router = APIRouter()


@router.post("/evaluate", response_model=GrammarEvaluationResponse)
async def grammar_evaluate(
    files: list[UploadFile] = File(...),
    provider: str = Form("gemini"),
    model: str = Form(...),
    language: str = Form("en"),
    correction_language: str | None = Form(None),
    summary_language: str | None = Form(None),
    service: GrammarEvaluationService = Depends(get_grammar_evaluation_service),
) -> GrammarEvaluationResponse:
    """Evaluate every uploaded document for grammar.

    ``language`` remains the legacy correction-language field.  New clients
    should use ``correction_language`` and ``summary_language``; omitted
    values fall back to ``language``.
    """

    documents = [
        UploadedDocument(
            content=await file.read(),
            filename=file.filename or "unknown",
            content_type=file.content_type,
        )
        for file in files
    ]
    try:
        return await service.evaluate(
            documents=documents,
            provider_name=provider,
            model=model,
            language=language,
            summary_language=summary_language,
            correction_language=correction_language,
        )
    except GrammarUploadProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GrammarEvaluationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
