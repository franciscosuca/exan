"""Where built-in models live on disk, which ones are installed, and how they are downloaded."""

from __future__ import annotations

import shutil
from pathlib import Path

import httpx

from ..downloads import DownloadError, download_file, ensure_free_space, new_client, part_path
from .base import ProgressCallback
from .builtin_catalog import BuiltinModel


class ModelStore:
    def __init__(self, root: Path, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.root = root
        self._transport = transport

    def model_dir(self, model: BuiltinModel) -> Path:
        return self.root / model.id

    def paths(self, model: BuiltinModel) -> dict[str, Path]:
        return {item.role: self.model_dir(model) / item.path for item in model.files}

    def is_installed(self, model: BuiltinModel) -> bool:
        paths = self.paths(model)
        return all(paths[f.role].is_file() and paths[f.role].stat().st_size == f.size for f in model.files)

    def downloaded_bytes(self, model: BuiltinModel) -> int:
        """Bytes already on disk (complete files plus resumable partial files)."""
        total = 0
        for item in model.files:
            target = self.paths(model)[item.role]
            if target.is_file() and target.stat().st_size == item.size:
                total += item.size
            elif part_path(target).is_file():
                total += min(part_path(target).stat().st_size, item.size)
        return total

    def delete(self, model: BuiltinModel) -> None:
        shutil.rmtree(self.model_dir(model), ignore_errors=True)

    async def download(self, model: BuiltinModel, progress: ProgressCallback) -> None:
        """Download every missing file of ``model``; resumes partial files. Raises DownloadError."""
        total = model.download_bytes
        ensure_free_space(self.root, total - self.downloaded_bytes(model))
        finished = 0
        progress("downloading", self.downloaded_bytes(model), total)
        async with new_client(self._transport) as client:
            for item in model.files:
                offset = finished
                await download_file(
                    client,
                    item.url,
                    self.paths(model)[item.role],
                    size=item.size,
                    sha256=item.sha256,
                    on_progress=lambda done, offset=offset: progress("downloading", offset + done, total),
                )
                finished += item.size
        if not self.is_installed(model):
            raise DownloadError("download_failed", "The model files are incomplete. Try again.")
        progress("success", total, total)
