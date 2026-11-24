"""Provider registry - resolves provider name to instance."""

import httpx

from ..config import settings
from . import BaseProvider
from .claude import ClaudeProvider
from .gemini import GeminiProvider, list_gemini_models
from .gpt import GPTProvider
from .lmstudio import LMStudioProvider
from .ollama import OllamaProvider


def get_provider(name: str, model: str) -> BaseProvider:
    # TODO: Make this registry data-driven (name -> class + capabilities) instead of
    # hardcoded branches below.
    providers = {
        "gemini": GeminiProvider,
        "claude": ClaudeProvider,
        "gpt": GPTProvider,
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
    }
    if name not in providers:
        raise ValueError(f"Unknown provider: {name}. Available: {list(providers.keys())}")
    if name == "gemini":
        return GeminiProvider(model)
    if name == "lmstudio":
        return LMStudioProvider(model)
    return providers[name]()


def get_provider_models(name: str) -> list[dict]:
    # TODO: Replace this provider-specific branching with a capability-driven registry
    # so new providers expose their model catalogue without editing this function.
    if name == "gemini":
        return list_gemini_models()
    if name == "lmstudio":
        resp = httpx.get(f"{settings.lmstudio_base_url}/models", timeout=5.0)
        resp.raise_for_status()
        return [
            {
                "id": model_id,
                "name": model_id,
                "display_name": model_id,
                "supported_actions": [],
            }
            for model_id in (entry.get("id") for entry in resp.json().get("data", []))
            if model_id
        ]
    raise ValueError(f"Model catalogue is not supported for provider: {name}")


def get_available_providers() -> list[dict]:
    """Check which providers are configured and available."""
    results = []

    # Gemini
    results.append(
        {
            "provider": "gemini",
            "available": bool(settings.gemini_api_key),
            "requires_api_key": True,
            "is_local": False,
        }
    )

    # Claude
    results.append(
        {
            "provider": "claude",
            "available": bool(settings.anthropic_api_key),
            "requires_api_key": True,
            "is_local": False,
        }
    )

    # GPT (cloud)
    results.append(
        {
            "provider": "gpt",
            "available": bool(settings.openai_api_key),
            "requires_api_key": True,
            "is_local": False,
        }
    )

    # Ollama (local)
    ollama_available = False
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0)
        ollama_available = resp.status_code == 200
    except Exception:
        pass

    results.append(
        {
            "provider": "ollama",
            "available": ollama_available,
            "requires_api_key": False,
            "is_local": True,
        }
    )

    # LM Studio (local)
    lmstudio_available = False
    try:
        resp = httpx.get(f"{settings.lmstudio_base_url}/models", timeout=2.0)
        lmstudio_available = resp.status_code == 200
    except Exception:
        pass

    results.append(
        {
            "provider": "lmstudio",
            "available": lmstudio_available,
            "requires_api_key": False,
            "is_local": True,
        }
    )

    return results
