from __future__ import annotations

import json
from pathlib import Path

import pytest

from exan_sidecar.config import ConfigError, RuntimeConfig, SettingsStore
from exan_sidecar.export import export_csv, safe_cell
from exan_sidecar.grading import AnswerItem, KeyItem
from exan_sidecar.session import Session


def test_runtime_config_from_env(tmp_path: Path) -> None:
    config = RuntimeConfig.from_env(
        {
            "EXAN_SECRET": "x" * 32,
            "EXAN_DATA_DIR": str(tmp_path),
            "EXAN_CORS_ORIGINS": "http://localhost:5173/, http://localhost:1420",
            "EXAN_WATCH_STDIN": "1",
        }
    )
    assert config.host == "127.0.0.1" and config.port == 0
    assert config.log_dir == tmp_path / "logs"
    assert config.cors_origins.count("http://localhost:1420") == 1
    assert "http://localhost:5173" in config.cors_origins
    assert config.watch_stdin is True
    with pytest.raises(ConfigError):
        RuntimeConfig.from_env({"EXAN_SECRET": "x" * 32, "EXAN_HOST": "192.168.1.2"})
    with pytest.raises(ConfigError):
        RuntimeConfig.from_env({"EXAN_SECRET": "x" * 32, "EXAN_PORT": "abc"})


def test_settings_store_recovers_from_bad_files(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert SettingsStore(path).get().runtime == "ollama"

    path.write_text(json.dumps({"model": "gemma3:4b", "max_image_side": 1, "language": "en", "legacy": True}))
    settings = SettingsStore(path).get()
    assert settings.model == "gemma3:4b" and settings.language == "en"
    assert settings.max_image_side == 1600  # invalid value replaced by the default


def test_settings_store_writes_atomically(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "nested" / "settings.json")
    store.update({"model": "  qwen2.5vl:3b  ", "runtime": "openai"})
    assert store.get().model == "qwen2.5vl:3b"
    assert json.loads((tmp_path / "nested" / "settings.json").read_text())["runtime"] == "openai"
    assert [p.name for p in (tmp_path / "nested").iterdir()] == ["settings.json"]
    with pytest.raises(ValueError):
        store.update({"secret": "x"})
    with pytest.raises(ValueError):
        store.update({"openai_url": "******localhost:1234/v1"})


@pytest.mark.parametrize("value", ["=1+1", "+49 170", "-5", "@SUM(A1)", "\tx"])
def test_formula_cells_are_neutralised(value: str) -> None:
    assert safe_cell(value) == "'" + value


def test_export_neutralises_names_and_answers() -> None:
    session = Session()
    session.key.items = [KeyItem("1", "A")]
    participant = session.add_participant([])
    participant.name = '=HYPERLINK("http://evil")'
    participant.answers = [AnswerItem("1", "@cmd")]
    summary = export_csv(session, "summary", "en")
    detail = export_csv(session, "detail", "en")
    assert "'=HYPERLINK" in summary
    assert "'@cmd" in detail
    unnamed = Session()
    unnamed.add_participant([])
    assert "Teilnehmende Person 1" in export_csv(unnamed, "summary", "de")
