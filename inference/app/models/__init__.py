from pydantic import BaseModel, Field, model_validator

QuestionNumber = int | str


class Question(BaseModel):
    number: QuestionNumber
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
    question_number: QuestionNumber
    correct_answer: str
    points: float


class AnswerKey(BaseModel):
    id: str
    exam_id: str
    answers: list[Answer]
    created_at: str


class StudentAnswer(BaseModel):
    question_number: QuestionNumber
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


# --- Batch Evaluation Models ---


class GrammarIssue(BaseModel):
    """A single finding, with an unambiguous before/after representation.

    ``issue`` and ``correction`` are accepted when reading older provider
    responses, but are deliberately not part of the new response shape.
    """

    original_text: str
    corrected_text: str

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_fields(cls, value: object) -> object:
        if isinstance(value, dict):
            value = dict(value)
            value.setdefault("original_text", value.get("issue"))
            value.setdefault("corrected_text", value.get("correction"))
        return value


class GrammarFeedback(BaseModel):
    issues: list[GrammarIssue] = Field(default_factory=list)
    summary: str = ""


class FileEvaluationResult(BaseModel):
    id: str
    filename: str
    summary: str
    grammar: GrammarFeedback | None = None


class BatchEvaluationResponse(BaseModel):
    id: str
    results: list[FileEvaluationResult]
    created_at: str
