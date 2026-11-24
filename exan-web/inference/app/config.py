from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Provider API keys (optional - only needed for cloud providers)
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Ollama settings (for local/offline inference)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-vl"

    # LM Studio settings (for local/offline inference)
    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "qwen2.5-vl-7b-instruct"

    # Default provider preference order
    default_provider: str = "gemini"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
