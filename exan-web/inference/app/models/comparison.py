from pydantic import BaseModel

from .exam import QuestionNumber


class StudentAnswer(BaseModel):
    question_number: QuestionNumber
    student_answer: str
    correct_answer: str
    is_correct: bool


class ComparisonResult(BaseModel):
    id: str
    exam_id: str
    student_name: str | None = None
    filename: str
    answers: list[StudentAnswer]
