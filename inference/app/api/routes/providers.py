"""Provider discovery routes."""

from fastapi import APIRouter

from ...providers.registry import get_available_providers

router = APIRouter(prefix="/api")


@router.get("/providers")
async def list_providers() -> list[dict]:
    """List available AI providers and their status."""
    return get_available_providers()
