"""Models for the built-in runtime (llama.cpp), loaded from ``models.json``.

Each model is downloaded from Hugging Face only after the user agreed, pinned to a repository revision
and checked with SHA-256. The same file feeds the model page of the Windows installer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any

STRUCTURED = "structured"
OCR = "ocr"

_ID = re.compile(r"^[a-z0-9][a-z0-9.\-]{1,62}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REPO = re.compile(r"^[A-Za-z0-9][\w.\-]*/[\w.\-]+$")
_FILE = re.compile(r"^[\w.\-]+\.gguf$")


class CatalogError(ValueError):
    """models.json is malformed (a packaging bug, never user input)."""


@dataclass(frozen=True)
class ModelFile:
    role: str
    repo: str
    revision: str
    path: str
    size: int
    sha256: str

    @property
    def url(self) -> str:
        return f"https://huggingface.co/{self.repo}/resolve/{self.revision}/{self.path}"


@dataclass(frozen=True)
class BuiltinModel:
    id: str
    label: str
    vendor: str
    params: str
    mode: str
    recommended: bool
    license: str
    homepage: str
    min_ram_gb: int
    prompt: str
    image_side: int
    max_tokens: int
    ctx_size: int
    files: tuple[ModelFile, ...]
    sampling: dict[str, Any] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)
    summary: dict[str, str] = field(default_factory=dict)

    @property
    def download_bytes(self) -> int:
        return sum(f.size for f in self.files)

    def file(self, role: str) -> ModelFile:
        for item in self.files:
            if item.role == role:
                return item
        raise KeyError(role)

    def view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "vendor": self.vendor,
            "params": self.params,
            "mode": self.mode,
            "recommended": self.recommended,
            "license": self.license,
            "homepage": self.homepage,
            "min_ram_gb": self.min_ram_gb,
            "download_bytes": self.download_bytes,
            "notes": dict(self.notes),
            "summary": dict(self.summary),
            "source": "huggingface.co/" + self.files[0].repo,
        }


def _model_from(raw: dict[str, Any]) -> BuiltinModel:
    try:
        files = tuple(
            ModelFile(
                role=str(f["role"]),
                repo=str(f["repo"]),
                revision=str(f["revision"]),
                path=str(f["path"]),
                size=int(f["size"]),
                sha256=str(f["sha256"]).lower(),
            )
            for f in raw["files"]
        )
        model = BuiltinModel(
            id=str(raw["id"]),
            label=str(raw["label"]),
            vendor=str(raw["vendor"]),
            params=str(raw["params"]),
            mode=str(raw["mode"]),
            recommended=bool(raw["recommended"]),
            license=str(raw["license"]),
            homepage=str(raw["homepage"]),
            min_ram_gb=int(raw["min_ram_gb"]),
            prompt=str(raw.get("prompt") or ""),
            image_side=int(raw["image_side"]),
            max_tokens=int(raw["max_tokens"]),
            ctx_size=int(raw["ctx_size"]),
            files=files,
            sampling=dict(raw.get("sampling") or {}),
            notes={str(k): str(v) for k, v in (raw.get("notes") or {}).items()},
            summary={str(k): str(v) for k, v in (raw.get("summary") or {}).items()},
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogError(f"invalid model entry {raw.get('id')!r}: {exc}") from exc
    _validate(model)
    return model


def _validate(model: BuiltinModel) -> None:
    problems: list[str] = []
    if not _ID.match(model.id):
        problems.append("id")
    if model.mode not in (STRUCTURED, OCR):
        problems.append("mode")
    if model.mode == OCR and not model.prompt:
        problems.append("prompt (OCR models need their own prompt)")
    if sorted(f.role for f in model.files) != ["mmproj", "model"]:
        problems.append("files (need one 'model' and one 'mmproj')")
    for item in model.files:
        if not (_REPO.match(item.repo) and _REVISION.match(item.revision) and _FILE.match(item.path)):
            problems.append(f"file {item.path!r}")
        if not _SHA256.match(item.sha256) or item.size <= 0:
            problems.append(f"checksum/size of {item.path!r}")
    if not (512 <= model.image_side <= 4096 and 256 <= model.max_tokens <= model.ctx_size):
        problems.append("image_side/max_tokens/ctx_size")
    if problems:
        raise CatalogError(f"model {model.id!r}: invalid {', '.join(problems)}")


def parse_catalog(data: dict[str, Any]) -> tuple[BuiltinModel, ...]:
    models = tuple(_model_from(raw) for raw in data.get("models", []))
    ids = [m.id for m in models]
    if len(ids) != len(set(ids)):
        raise CatalogError("model ids must be unique")
    if sum(m.recommended for m in models) != 1:
        raise CatalogError("exactly one model must be recommended")
    return models


@cache
def catalog() -> tuple[BuiltinModel, ...]:
    text = resources.files(__package__).joinpath("models.json").read_text(encoding="utf-8")
    return parse_catalog(json.loads(text))


def get_model(model_id: str) -> BuiltinModel | None:
    for model in catalog():
        if model.id == model_id:
            return model
    return None


def recommended_model() -> BuiltinModel:
    return next(m for m in catalog() if m.recommended)
