"""Clients for vision-model runtimes: the built-in llama.cpp runtime, Ollama and OpenAI-compatible servers."""

from .base import EngineError, ModelInfo, RuntimeStatus, VisionEngine, create_engine
from .llamacpp import BuiltinEngine, LlamaServer
from .model_store import ModelStore
from .ollama import OllamaEngine
from .openai_compat import OpenAICompatEngine

__all__ = [
    "BuiltinEngine",
    "EngineError",
    "LlamaServer",
    "ModelInfo",
    "ModelStore",
    "OllamaEngine",
    "OpenAICompatEngine",
    "RuntimeStatus",
    "VisionEngine",
    "create_engine",
]
