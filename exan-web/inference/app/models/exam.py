from pydantic import BaseModel, Field, field_validator

QuestionNumber = int | str


class Question(BaseModel):
    number: QuestionNumber
    text: str
    type: str
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
