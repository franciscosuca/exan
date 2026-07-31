"""LM Studio provider using its local OpenAI-compatible API."""

from ..config import settings
from .openai_compatible import OpenAICompatibleProvider


class LMStudioProvider(OpenAICompatibleProvider):
    name = "lmstudio"

    def __init__(self):
        super().__init__(
            api_key="lm-studio",
            base_url=settings.lmstudio_base_url,
            model=settings.lmstudio_model,
        )
