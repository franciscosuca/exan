"""Exam comparison HTTP routes."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ...models import AnswerKey, ExamStructure, GradingResult
from ...services import UploadedDocument
from ...services.exam_comparison import (
    AnswerKeyNotFoundError,
    ExamComparisonService,
    ExamNotFoundError,
    GradingError,
    ProviderAnalysisError,
    UploadProcessingError,
)
from ..dependencies import get_exam_comparison_service

router = APIRouter(prefix="/api/exam")


def _document(content: bytes, file: UploadFile) -> UploadedDocument:
    return UploadedDocument(
        content=content,
        filename=file.filename or "unknown",
        content_type=file.content_type,
    )


@router.post("/template", response_model=ExamStructure)
async def upload_exam_template(
    file: UploadFile = File(...),
    provider: str = Form("gemini"),
    service: ExamComparisonService = Depends(get_exam_comparison_service),
) -> ExamStructure:
    """Upload an empty exam template for structure analysis."""
    document = _document(await file.read(), file)
    try:
        return await service.upload_exam_template(document, provider)
    except UploadProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderAnalysisError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/answer-key", response_model=AnswerKey)
async def upload_answer_key(
    file: UploadFile = File(...),
    exam_id: str = Form(...),
    provider: str = Form("gemini"),
    service: ExamComparisonService = Depends(get_exam_comparison_service),
) -> AnswerKey:
    """Upload an exam with correct answers filled in."""
    document = _document(await file.read(), file)
    try:
        return await service.upload_answer_key(document, exam_id, provider)
    except ExamNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UploadProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderAnalysisError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/grade", response_model=list[GradingResult])
async def grade_student_exams(
    files: list[UploadFile] = File(...),
    exam_id: str = Form(...),
    provider: str = Form("gemini"),
    service: ExamComparisonService = Depends(get_exam_comparison_service),
) -> list[GradingResult]:
    """Upload and grade one or more student exams."""
    documents = [_document(await file.read(), file) for file in files]
    try:
        return await service.grade_student_exams(documents, exam_id, provider)
    except ExamNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AnswerKeyNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UploadProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GradingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
