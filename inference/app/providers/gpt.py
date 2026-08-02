"""OpenAI GPT provider."""

from ..config import settings
from .openai_compatible import OpenAICompatibleProvider


class GPTProvider(OpenAICompatibleProvider):
    name = "gpt"

    def __init__(self):
        super().__init__(
            api_key=settings.openai_api_key or "placeholder",
            model=settings.openai_model,
        )
