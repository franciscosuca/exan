from pydantic import BaseModel, Field, field_validator, model_validator

QuestionNumber = int | str


class Question(BaseModel):
    number: QuestionNumber
    text: str
    type: str  # multiple_choice, open_ended, true_false, fill_in_blank
    options: list[str] | None = None


class ExamStructure(BaseModel):
    id: str
    filename: str
    questions: list[Question]
    created_at: str
    criteria: str | None = None


class Answer(BaseModel):
    question_number: QuestionNumber
    correct_answer: str


class AnswerKeyUpdateItem(BaseModel):
    question_number: QuestionNumber
    correct_answer: str = Field(min_length=1)

    @field_validator("question_number")
    @classmethod
    def question_number_must_not_be_empty(cls, value: QuestionNumber) -> QuestionNumber:
        if isinstance(value, str) and not value.strip():
            raise ValueError("question_number must not be empty")
        return value

    @field_validator("correct_answer")
    @classmethod
    def correct_answer_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("correct_answer must not be blank")
        return value


class AnswerKeyUpdate(BaseModel):
    answers: list[AnswerKeyUpdateItem] = Field(min_length=1)


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


class ComparisonResult(BaseModel):
    id: str
    exam_id: str
    student_name: str | None = None
    filename: str
    answers: list[StudentAnswer]


class ProviderConfig(BaseModel):
    provider: str
    available: bool
    requires_api_key: bool
    is_local: bool


class ProviderModel(BaseModel):
    id: str
    name: str
    display_name: str
    supported_actions: list[str]


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
