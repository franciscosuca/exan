"""Tests for the provider registry."""

from unittest.mock import patch

import pytest

from app.providers import BaseProvider
from app.providers.registry import get_available_providers, get_provider


@patch("app.providers.gemini.settings")
def test_get_provider_gemini(mock_settings):
    """get_provider returns GeminiProvider."""
    mock_settings.gemini_api_key = "test-key"
    from app.providers.gemini import GeminiProvider

    provider = get_provider("gemini")
    assert isinstance(provider, GeminiProvider)


def test_get_provider_claude():
    """get_provider returns ClaudeProvider."""
    from app.providers.claude import ClaudeProvider

    provider = get_provider("claude")
    assert isinstance(provider, ClaudeProvider)


def test_get_provider_qwen():
    """get_provider returns QwenProvider."""
    from app.providers.qwen import QwenProvider

    provider = get_provider("qwen")
    assert isinstance(provider, QwenProvider)


def test_get_provider_ollama():
    """get_provider returns OllamaProvider."""
    from app.providers.ollama import OllamaProvider

    provider = get_provider("ollama")
    assert isinstance(provider, OllamaProvider)


def test_get_provider_unknown_raises():
    """get_provider raises ValueError for unknown provider."""
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent")


def test_ollama_implements_base():
    """Ollama provider implements BaseProvider interface."""
    provider = get_provider("ollama")
    assert isinstance(provider, BaseProvider)
    assert hasattr(provider, "analyze_exam_structure")
    assert hasattr(provider, "extract_answers")
    assert hasattr(provider, "grade_exam")


def test_get_available_providers_shape():
    """get_available_providers returns correctly shaped data."""
    providers = get_available_providers()
    assert len(providers) == 4
    for p in providers:
        assert "provider" in p
        assert "available" in p
        assert "requires_api_key" in p
        assert "is_local" in p

    ollama = next(p for p in providers if p["provider"] == "ollama")
    assert ollama["is_local"] is True
    assert ollama["requires_api_key"] is False
