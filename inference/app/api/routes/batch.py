"""Batch evaluation HTTP routes."""

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
    service: BatchEvaluationService = Depends(get_batch_evaluation_service),
) -> BatchEvaluationResponse:
    """Evaluate every uploaded document for grammar."""

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
        )
    except UploadProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BatchEvaluationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
