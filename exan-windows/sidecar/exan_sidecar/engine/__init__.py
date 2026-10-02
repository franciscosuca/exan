"""Clients for local vision-model runtimes (Ollama and OpenAI-compatible servers)."""

from .base import EngineError, ModelInfo, RuntimeStatus, VisionEngine, create_engine
from .ollama import OllamaEngine
from .openai_compat import OpenAICompatEngine

__all__ = [
    "EngineError",
    "ModelInfo",
    "OllamaEngine",
    "OpenAICompatEngine",
    "RuntimeStatus",
    "VisionEngine",
    "create_engine",
]
