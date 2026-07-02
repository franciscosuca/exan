from pydantic import BaseModel


class Question(BaseModel):
    number: int
    text: str
    type: str  # multiple_choice, open_ended, true_false, fill_in_blank
    options: list[str] | None = None
    points: float | None = None


class ExamStructure(BaseModel):
    id: str
    filename: str
    questions: list[Question]
    created_at: str


class Answer(BaseModel):
    question_number: int
    correct_answer: str
    points: float


class AnswerKey(BaseModel):
    id: str
    exam_id: str
    answers: list[Answer]
    created_at: str


class StudentAnswer(BaseModel):
    question_number: int
    student_answer: str
    correct_answer: str
    is_correct: bool
    points_earned: float
    points_possible: float


class GradingResult(BaseModel):
    id: str
    exam_id: str
    student_name: str | None = None
    filename: str
    total_score: float
    max_score: float
    percentage: float
    answers: list[StudentAnswer]


class ProviderConfig(BaseModel):
    provider: str
    available: bool
    requires_api_key: bool
    is_local: bool
