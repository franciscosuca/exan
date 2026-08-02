"""Focused tests for persistent inference run records."""

import json
from types import SimpleNamespace

from app import run_logging
from app.providers import ProviderResponse


def test_write_run_log_creates_timestamped_exam_comparison_record(tmp_path, monkeypatch):
    monkeypatch.setattr(run_logging, "LOG_ROOT", tmp_path)
    provider = SimpleNamespace(name="gemini", model="test-model")

    path = run_logging.write_run_log(
        "exam-comparison",
        input_snapshot={"files": [{"filename": "student.pdf", "bytes": 10}]},
        outputs=[
            {
                "operation": "grade_exam",
                "elapsed_ms": 3.2,
                "output": ProviderResponse({"score": 9}, usage={"total": 12}),
            }
        ],
        elapsed=4.5,
        provider=provider,
    )

    assert path.parent.parent == tmp_path / "exam-comparison"
    assert len(path.parent.name) == 10
    record = json.loads(path.read_text())
    assert record["provider"] == "gemini"
    assert record["model"] == "test-model"
    assert record["outputs"][0]["output"] == {"score": 9}
    assert record["outputs"][0]["token_usage"] == {"total": 12}


def test_write_run_log_creates_batch_evaluation_record(tmp_path, monkeypatch):
    monkeypatch.setattr(run_logging, "LOG_ROOT", tmp_path)

    path = run_logging.write_run_log(
        "batch-evaluation",
        input_snapshot={"files": [{"filename": "essay.pdf", "text_preview": "Example"}]},
        outputs=[
            {"operation": "grammar", "output": {"score": 80}},
            {"operation": "custom_criteria", "output": {"score": 70}},
        ],
        elapsed=20,
        provider=SimpleNamespace(name="ollama", model="local"),
    )

    assert path.parent.parent == tmp_path / "batch-evaluation"
    assert len(json.loads(path.read_text())["outputs"]) == 2


def test_usage_is_kept_with_each_model_output(tmp_path, monkeypatch):
    monkeypatch.setattr(run_logging, "LOG_ROOT", tmp_path)

    path = run_logging.write_run_log(
        "batch-evaluation",
        input_snapshot={},
        outputs=[
            {"operation": "grammar", "output": ProviderResponse({}, usage={"total": 3})},
            {"operation": "custom", "output": ProviderResponse({}, usage={"total": 7})},
        ],
        elapsed=1,
        provider=SimpleNamespace(name="gpt", model="test"),
    )

    outputs = json.loads(path.read_text())["outputs"]
    assert [output["token_usage"] for output in outputs] == [{"total": 3}, {"total": 7}]
