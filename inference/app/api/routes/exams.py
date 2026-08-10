"""Exam comparison HTTP routes."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ...models import AnswerKey, AnswerKeyUpdate, ComparisonResult, ExamStructure
from ...services import UploadedDocument
from ...services.exam_comparison import (
    AnswerKeyNotFoundError,
    ComparisonError,
    ExamComparisonService,
    ExamNotFoundError,
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
    model: str = Form(...),
    criteria: str | None = Form(None),
    service: ExamComparisonService = Depends(get_exam_comparison_service),
) -> ExamStructure:
    """Upload an empty exam template for structure analysis."""
    document = _document(await file.read(), file)
    try:
        return await service.upload_exam_template(document, provider, model, criteria)
    except UploadProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderAnalysisError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/answer-key", response_model=AnswerKey)
async def upload_answer_key(
    file: UploadFile = File(...),
    exam_id: str = Form(...),
    provider: str = Form("gemini"),
    model: str = Form(...),
    service: ExamComparisonService = Depends(get_exam_comparison_service),
) -> AnswerKey:
    """Upload an exam with correct answers filled in."""
    document = _document(await file.read(), file)
    try:
        return await service.upload_answer_key(document, exam_id, provider, model)
    except ExamNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UploadProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderAnalysisError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/answer-key/{exam_id}", response_model=AnswerKey)
async def update_answer_key(
    exam_id: str,
    payload: AnswerKeyUpdate,
    service: ExamComparisonService = Depends(get_exam_comparison_service),
) -> AnswerKey:
    """Persist corrections to an answer key extracted for an existing exam."""
    try:
        return await service.update_answer_key(exam_id, payload.answers)
    except (ExamNotFoundError, AnswerKeyNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/compare", response_model=list[ComparisonResult])
async def compare_student_exams(
    files: list[UploadFile] = File(...),
    exam_id: str = Form(...),
    provider: str = Form("gemini"),
    model: str = Form(...),
    service: ExamComparisonService = Depends(get_exam_comparison_service),
) -> list[ComparisonResult]:
    """Upload and compare one or more student exams."""
    documents = [_document(await file.read(), file) for file in files]
    try:
        return await service.compare_student_exams(documents, exam_id, provider, model)
    except ExamNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AnswerKeyNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UploadProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ComparisonError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
