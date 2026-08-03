"""Persistent, compact records for inference runs."""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_ROOT = Path(__file__).resolve().parents[2] / "logs"
logger = logging.getLogger(__name__)


def start_timer() -> float:
    """Return a monotonic start time for a model call."""
    return time.perf_counter()


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _metadata(provider: Any, output: Any) -> dict[str, Any]:
    usage = None
    usage = getattr(output, "usage", None)
    if isinstance(output, dict):
        usage = usage or output.get("usage") or output.get("token_usage")
    metadata = {
        "provider": getattr(provider, "name", provider.__class__.__name__),
        "model": getattr(provider, "model", None),
    }
    if usage is not None:
        metadata["token_usage"] = usage
    return metadata


def write_run_log(
    category: str,
    *,
    input_snapshot: dict[str, Any],
    outputs: list[dict[str, Any]],
    elapsed: float,
    provider: Any,
) -> Path:
    """Write one JSON record under ``logs/<category>/<yymmddhhmm>/``."""
    now = datetime.now(timezone.utc)
    directory = LOG_ROOT / category / now.strftime("%y%m%d%H%M")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        record = {
            "created_at": now.isoformat(),
            "elapsed_ms": round(elapsed, 2),
            "input": input_snapshot,
            "model": _metadata(provider, outputs[-1]["output"] if outputs else {}).get("model"),
            "provider": _metadata(
                provider, outputs[-1]["output"] if outputs else {}
            ).get("provider"),
            "outputs": [
                {**call, **_metadata(provider, call.get("output"))} for call in outputs
            ],
        }
        path = directory / f"run-{uuid.uuid4().hex}.json"
        path.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
        return path
    except (OSError, TypeError, ValueError):
        logger.exception("Unable to persist %s inference log", category)
        return None
