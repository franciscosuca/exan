from pydantic import BaseModel, Field, model_validator


class GrammarIssue(BaseModel):
    """A single finding with an unambiguous before/after representation."""

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


class GrammarEvaluationResponse(BaseModel):
    id: str
    results: list[FileEvaluationResult]
    created_at: str
