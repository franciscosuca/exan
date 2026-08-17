"""FastAPI dependencies for constructing application services."""

from collections.abc import Callable

from fastapi import Depends

from ..providers import BaseProvider
from ..repositories.exam_repository import ExamRepository
from ..services.exam_comparison import ExamComparisonService
from ..services.grammar_evaluation import GrammarEvaluationService

_exam_repository = ExamRepository()


def get_provider(name: str, model: str) -> BaseProvider:
    """Resolve a provider through the application registry."""
    from .. import main

    return main.get_provider(name, model)


def get_exam_repository() -> ExamRepository:
    """Return the process-local exam repository used by the MVP."""
    return _exam_repository


def get_provider_factory() -> Callable[[str, str], BaseProvider]:
    """Return the provider resolver used by workflow services."""
    return get_provider


def get_exam_comparison_service(
    repository: ExamRepository = Depends(get_exam_repository),
) -> ExamComparisonService:
    """Construct the exam comparison workflow with its repository."""
    return ExamComparisonService(repository, get_provider_factory())


def get_grammar_evaluation_service() -> GrammarEvaluationService:
    """Construct the grammar evaluation workflow."""
    return GrammarEvaluationService(get_provider_factory())
