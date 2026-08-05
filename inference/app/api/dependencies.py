"""FastAPI dependencies for constructing application services."""

from collections.abc import Callable

from fastapi import Depends

from ..providers import BaseProvider
from ..repositories.exam_repository import ExamRepository
from ..services.batch_evaluation import BatchEvaluationService
from ..services.exam_comparison import ExamComparisonService

_exam_repository = ExamRepository()


def get_provider(name: str) -> BaseProvider:
    """Resolve a provider through the application registry."""
    from .. import main

    return main.get_provider(name)


def get_exam_repository() -> ExamRepository:
    """Return the process-local exam repository used by the MVP."""
    return _exam_repository


def get_provider_factory() -> Callable[[str], BaseProvider]:
    """Return the provider resolver used by workflow services."""
    return get_provider


def get_exam_comparison_service(
    repository: ExamRepository = Depends(get_exam_repository),
) -> ExamComparisonService:
    """Construct the exam comparison workflow with its repository."""
    return ExamComparisonService(repository, get_provider_factory())


def get_batch_evaluation_service() -> BatchEvaluationService:
    """Construct the batch evaluation workflow."""
    return BatchEvaluationService(get_provider_factory())
