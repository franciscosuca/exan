"""Provider registry - resolves provider name to instance."""

import httpx

from ..config import settings
from . import BaseProvider
from .claude import ClaudeProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .qwen import QwenProvider


def get_provider(name: str) -> BaseProvider:
    providers = {
        "gemini": GeminiProvider,
        "claude": ClaudeProvider,
        "qwen": QwenProvider,
        "ollama": OllamaProvider,
    }
    if name not in providers:
        raise ValueError(f"Unknown provider: {name}. Available: {list(providers.keys())}")
    return providers[name]()


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

    # Qwen (cloud)
    results.append(
        {
            "provider": "qwen",
            "available": bool(settings.qwen_api_key),
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

    return results
