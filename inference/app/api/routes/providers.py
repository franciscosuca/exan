"""Provider discovery and model catalogue routes."""

from fastapi import APIRouter, HTTPException

from ...models import ProviderModel
from ...providers.registry import get_available_providers, get_provider_models

router = APIRouter(prefix="/api")


@router.get("/providers")
async def list_providers() -> list[dict]:
    """List available AI providers and their status."""
    return get_available_providers()


@router.get("/providers/{provider}/models", response_model=list[ProviderModel])
async def list_models(provider: str) -> list[dict]:
    """List generation-capable models for a provider."""
    if provider != "gemini":
        raise HTTPException(
            status_code=400,
            detail=f"Model catalogue is not supported for provider: {provider}",
        )
    try:
        return get_provider_models(provider)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch models for provider {provider}: {exc}",
        ) from exc
