"""Exan Backend - AI-powered exam scanning and grading API."""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .file_processing import get_mime_type, process_upload
from .models import AnswerKey, ExamStructure, GradingResult, StudentAnswer
from .providers.registry import get_available_providers, get_provider

app = FastAPI(title="Exan API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for this MVP
_exams: dict[str, dict] = {}
_answer_keys: dict[str, dict] = {}


@app.get("/api/providers")
async def list_providers():
    """List available AI providers and their status."""
    return get_available_providers()


@app.post("/api/exam/template", response_model=ExamStructure)
async def upload_exam_template(
    file: UploadFile = File(...),
    provider: str = Form("gemini"),
):
    """Upload an empty exam template for structure analysis."""
    content = await file.read()
    mime = get_mime_type(file.filename or "unknown", file.content_type)

    try:
        images = process_upload(content, mime)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    image_data = [img for img, _ in images]
    mime_types = [mt for _, mt in images]

    try:
        ai = get_provider(provider)
        result = await ai.analyze_exam_structure(image_data, mime_types)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")

    exam_id = str(uuid.uuid4())
    exam = ExamStructure(
        id=exam_id,
        filename=file.filename or "unknown",
        questions=result.get("questions", []),
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    _exams[exam_id] = {
        "structure": exam.model_dump(),
        "raw_result": result,
    }

    return exam


@app.post("/api/exam/answer-key", response_model=AnswerKey)
async def upload_answer_key(
    file: UploadFile = File(...),
    exam_id: str = Form(...),
    provider: str = Form("gemini"),
):
    """Upload an exam with correct answers filled in."""
    if exam_id not in _exams:
        raise HTTPException(status_code=404, detail="Exam not found")

    content = await file.read()
    mime = get_mime_type(file.filename or "unknown", file.content_type)

    try:
        images = process_upload(content, mime)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    image_data = [img for img, _ in images]
    mime_types = [mt for _, mt in images]

    try:
        ai = get_provider(provider)
        result = await ai.extract_answers(image_data, mime_types)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")

    key_id = str(uuid.uuid4())
    raw_answers = result.get("answers", [])
    # Normalize: AI returns "answer" field, model expects "correct_answer"
    normalized = [
        {
            "question_number": a.get("question_number"),
            "correct_answer": a.get("correct_answer") or a.get("answer", ""),
            "points": a.get("points", 1),
        }
        for a in raw_answers
    ]
    answer_key = AnswerKey(
        id=key_id,
        exam_id=exam_id,
        answers=normalized,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    _answer_keys[exam_id] = {
        "key": answer_key.model_dump(),
        "raw_result": result,
    }

    return answer_key


@app.post("/api/exam/grade", response_model=list[GradingResult])
async def grade_student_exams(
    files: list[UploadFile] = File(...),
    exam_id: str = Form(...),
    provider: str = Form("gemini"),
):
    """Upload and grade one or more student exams."""
    if exam_id not in _exams:
        raise HTTPException(status_code=404, detail="Exam not found")
    if exam_id not in _answer_keys:
        raise HTTPException(status_code=400, detail="Answer key not uploaded yet")

    exam_data = _exams[exam_id]
    answer_key_data = _answer_keys[exam_id]

    ai = get_provider(provider)
    results = []

    for file in files:
        content = await file.read()
        mime = get_mime_type(file.filename or "unknown", file.content_type)

        try:
            images = process_upload(content, mime)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"File {file.filename}: {e}")

        image_data = [img for img, _ in images]
        mime_types = [mt for _, mt in images]

        try:
            grading = await ai.grade_exam(
                image_data,
                mime_types,
                exam_data["raw_result"],
                answer_key_data["raw_result"],
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Grading failed for {file.filename}: {e}"
            )

        answers = [StudentAnswer(**a) for a in grading.get("answers", [])]
        total = sum(a.points_earned for a in answers)
        max_score = sum(a.points_possible for a in answers)

        result = GradingResult(
            id=str(uuid.uuid4()),
            exam_id=exam_id,
            student_name=grading.get("student_name"),
            filename=file.filename or "unknown",
            total_score=total,
            max_score=max_score,
            percentage=(total / max_score * 100) if max_score > 0 else 0,
            answers=answers,
        )
        results.append(result)

    return results
