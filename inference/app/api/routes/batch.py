"""Batch evaluation HTTP routes."""

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ...models import BatchEvaluationResponse
from ...services import UploadedDocument
from ...services.batch_evaluation import (
    BatchEvaluationError,
    BatchEvaluationService,
    UploadProcessingError,
)
from ..dependencies import get_batch_evaluation_service

router = APIRouter(prefix="/api/batch")


@router.post("/evaluate", response_model=BatchEvaluationResponse)
async def batch_evaluate(
    files: list[UploadFile] = File(...),
    provider: str = Form("gemini"),
    language: str = Form("en"),
    include_grammar: str = Form("true"),
    custom_criteria: str = Form("[]"),
    service: BatchEvaluationService = Depends(get_batch_evaluation_service),
) -> BatchEvaluationResponse:
    """Evaluate a batch of documents against grammar and/or custom criteria."""
    include_grammar_bool = include_grammar.lower() in ("true", "1", "yes")

    try:
        criteria_list = json.loads(custom_criteria)
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid custom_criteria JSON") from exc

    if not include_grammar_bool and not criteria_list:
        raise HTTPException(
            status_code=400,
            detail="At least one evaluation criteria must be selected",
        )

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
            documents,
            provider,
            language,
            include_grammar_bool,
            criteria_list,
        )
    except UploadProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BatchEvaluationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
