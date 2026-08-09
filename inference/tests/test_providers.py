"""Tests for provider implementations and the registry."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.providers import BaseProvider
from app.providers.prompts import custom_criteria_evaluation_prompt, grammar_evaluation_prompt
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


def test_get_provider_gpt():
    """get_provider returns GPTProvider."""
    from app.providers.gpt import GPTProvider

    provider = get_provider("gpt")
    assert isinstance(provider, GPTProvider)


def test_get_provider_ollama():
    """get_provider returns OllamaProvider."""
    from app.providers.ollama import OllamaProvider

    provider = get_provider("ollama")
    assert isinstance(provider, OllamaProvider)


def test_get_provider_lmstudio():
    """get_provider returns LMStudioProvider."""
    from app.providers.lmstudio import LMStudioProvider

    provider = get_provider("lmstudio")
    assert isinstance(provider, LMStudioProvider)


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


@patch("app.providers.registry.httpx.get")
@patch("app.providers.registry.settings")
def test_get_available_providers_shape(mock_settings, mock_get):
    """Provider availability has the exact names and metadata."""
    mock_settings.gemini_api_key = "gemini-key"
    mock_settings.anthropic_api_key = ""
    mock_settings.openai_api_key = "openai-key"
    mock_settings.ollama_base_url = "http://ollama"
    mock_settings.lmstudio_base_url = "http://lmstudio/v1"
    mock_get.return_value.status_code = 200

    providers = get_available_providers()
    assert [p["provider"] for p in providers] == [
        "gemini",
        "claude",
        "gpt",
        "ollama",
        "lmstudio",
    ]
    for p in providers:
        assert set(p) == {"provider", "available", "requires_api_key", "is_local"}

    by_name = {p["provider"]: p for p in providers}
    assert by_name["gemini"] == {
        "provider": "gemini",
        "available": True,
        "requires_api_key": True,
        "is_local": False,
    }
    assert by_name["claude"]["available"] is False
    assert by_name["gpt"] == {
        "provider": "gpt",
        "available": True,
        "requires_api_key": True,
        "is_local": False,
    }
    for name in ("ollama", "lmstudio"):
        assert by_name[name]["available"] is True
        assert by_name[name]["requires_api_key"] is False
        assert by_name[name]["is_local"] is True

    assert mock_get.call_args_list[1].args[0] == "http://lmstudio/v1/models"
    assert mock_get.call_args_list[1].kwargs["timeout"] == 2.0


def test_gpt_preserves_multimodal_data_urls():
    """GPT sends images as OpenAI-compatible data URLs."""
    provider = get_provider("gpt")

    content = provider._build_content([b"image"], ["image/png"], "Inspect")

    assert content == [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,aW1hZ2U="}},
        {"type": "text", "text": "Inspect"},
    ]


def test_provider_feedback_is_plain_readable_text():
    """Provider evaluation output does not expose Markdown-only decoration."""
    result = BaseProvider._with_metadata(
        {
            "score": 80,
            "feedback": "**Grammar:**\n\n- Good flow.\n- [Review](https://example.com) commas.",
        },
        {},
    )

    assert result["feedback"] == "Grammar:\n\n- Good flow.\n- Review commas."


def test_grammar_prompt_requests_structured_response():
    prompt = grammar_evaluation_prompt("Spanish")

    assert '"grammar": {' in prompt
    assert '"issues": [' in prompt
    assert "one JSON object (one row) per issue" in prompt
    assert "Do not use Markdown formatting or tables" in prompt
    assert '"issues": []' in prompt
    assert '"feedback":' not in prompt


def test_custom_criteria_prompt_preserves_plain_text_feedback_contract():
    prompt = custom_criteria_evaluation_prompt(
        "Clarity", "Clear writing", "Unclear", "Clear", "Spanish"
    )

    assert "Issue found | Correction" in prompt
    assert "Include one table row per issue" in prompt
    assert "Keep the entire bulleted summary under 100 words" in prompt
    assert '"feedback": "The text demonstrates...' in prompt
    assert '"grammar": {' not in prompt


async def test_gemini_uses_schema_only_for_grammar_evaluation():
    from app.providers.gemini import GeminiProvider

    provider = GeminiProvider()
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(
        text='{"score": 90, "grammar": {"issues": [], "summary": "No issues."}}',
        usage=None,
        usage_metadata=None,
    )
    provider._client = client

    await provider.evaluate_text("Text", grammar_evaluation_prompt("Spanish"))
    grammar_config = client.models.generate_content.call_args.kwargs["config"]
    assert grammar_config.response_schema is not None

    client.models.generate_content.return_value = SimpleNamespace(
        text='{"score": 90, "feedback": "Clear."}',
        usage=None,
        usage_metadata=None,
    )
    await provider.evaluate_text(
        "Text",
        custom_criteria_evaluation_prompt("Clarity", "Clear", "Unclear", "Clear", "Spanish"),
    )
    custom_config = client.models.generate_content.call_args.kwargs["config"]
    assert custom_config.response_schema is None
