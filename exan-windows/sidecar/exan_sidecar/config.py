"""Runtime configuration (from the desktop shell) and persisted user settings."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
import tempfile
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationError, field_validator

log = logging.getLogger(__name__)

# The engine must never listen on a public interface: only loopback hosts are accepted.
LOOPBACK_BIND_HOSTS = ("127.0.0.1", "::1")

# Origins used by the Tauri webview on each platform plus the Vite dev server.
DEFAULT_CORS_ORIGINS = (
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "http://localhost:1420",
    "http://127.0.0.1:1420",
)

MIN_SECRET_LENGTH = 16


class ConfigError(Exception):
    """Raised when the sidecar is started with an invalid environment."""


def default_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Exan"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Exan"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "exan"


@dataclass(frozen=True)
class RuntimeConfig:
    secret: str
    host: str
    port: int
    data_dir: Path
    log_dir: Path
    cors_origins: tuple[str, ...]
    watch_stdin: bool

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> RuntimeConfig:
        env = os.environ if env is None else env

        secret = env.get("EXAN_SECRET", "").strip()
        if len(secret) < MIN_SECRET_LENGTH:
            raise ConfigError(
                f"EXAN_SECRET must be set to a random value with at least {MIN_SECRET_LENGTH} characters."
            )

        host = env.get("EXAN_HOST", "127.0.0.1").strip()
        if host not in LOOPBACK_BIND_HOSTS:
            raise ConfigError("EXAN_HOST must be a loopback address (127.0.0.1 or ::1).")

        raw_port = env.get("EXAN_PORT", "0").strip() or "0"
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ConfigError("EXAN_PORT must be a number.") from exc
        if not 0 <= port <= 65535:
            raise ConfigError("EXAN_PORT must be between 0 and 65535.")

        data_dir = Path(env["EXAN_DATA_DIR"]) if env.get("EXAN_DATA_DIR") else default_data_dir()
        log_dir = Path(env["EXAN_LOG_DIR"]) if env.get("EXAN_LOG_DIR") else data_dir / "logs"

        extra = tuple(o.strip().rstrip("/") for o in env.get("EXAN_CORS_ORIGINS", "").split(",") if o.strip())
        origins = tuple(dict.fromkeys(DEFAULT_CORS_ORIGINS + extra))

        return cls(
            secret=secret,
            host=host,
            port=port,
            data_dir=data_dir,
            log_dir=log_dir,
            cors_origins=origins,
            watch_stdin=env.get("EXAN_WATCH_STDIN", "0").strip() == "1",
        )


RuntimeKind = Literal["ollama", "openai"]
ExtractionMode = Literal["auto", "structured", "ocr"]
Language = Literal["de", "en"]


def _validate_http_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("must be an http:// or https:// URL")
    if parts.username or parts.password:
        raise ValueError("must not contain credentials")
    return value


class Settings(BaseModel):
    """User preferences persisted in the app-data directory (no secrets are stored here)."""

    runtime: RuntimeKind = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    openai_url: str = "http://127.0.0.1:1234/v1"
    model: str = Field("", max_length=200)
    extraction_mode: ExtractionMode = "auto"
    max_image_side: int = Field(1600, ge=512, le=4096)
    request_timeout: int = Field(300, ge=30, le=3600)
    language: Language = "de"

    @field_validator("ollama_url", "openai_url")
    @classmethod
    def _check_url(cls, value: str) -> str:
        return _validate_http_url(value)

    @field_validator("model")
    @classmethod
    def _check_model(cls, value: str) -> str:
        return value.strip()

    def runtime_url(self) -> str:
        return self.ollama_url if self.runtime == "ollama" else self.openai_url


class SettingsStore:
    """Thread-safe settings persisted as JSON with atomic writes."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._settings = self._load()

    def _load(self) -> Settings:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return Settings()
        except (OSError, ValueError):
            log.warning("Settings file is unreadable; using defaults")
            return Settings()
        if not isinstance(raw, dict):
            return Settings()
        known = {k: v for k, v in raw.items() if k in Settings.model_fields}
        try:
            return Settings.model_validate(known)
        except ValidationError:
            log.warning("Settings file contains invalid values; using defaults for them")
            defaults = Settings().model_dump()
            merged = dict(defaults)
            for key, value in known.items():
                try:
                    Settings.model_validate({**defaults, key: value})
                except ValidationError:
                    continue
                merged[key] = value
            return Settings.model_validate(merged)

    def get(self) -> Settings:
        with self._lock:
            return self._settings

    def update(self, patch: Mapping[str, Any]) -> Settings:
        with self._lock:
            unknown = set(patch) - set(Settings.model_fields)
            if unknown:
                raise ValueError(f"Unknown settings: {', '.join(sorted(unknown))}")
            updated = Settings.model_validate({**self._settings.model_dump(), **patch})
            self._save(updated)
            self._settings = updated
            return updated

    def _save(self, settings: Settings) -> None:
        tmp: str | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".settings-", suffix=".json", dir=self.path.parent)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(settings.model_dump(), handle, indent=2)
            os.replace(tmp, self.path)
            tmp = None
        except OSError:
            log.exception("Could not save settings")
        finally:
            if tmp is not None:
                with contextlib.suppress(OSError):
                    os.unlink(tmp)
