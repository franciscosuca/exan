"""Resumable, checksum-verified downloads of model files.

A file is written to ``<name>.part`` and only renamed to its final name after its size and SHA-256 match
the pinned values, so a half-downloaded or tampered file is never used. An interrupted download
continues from the ``.part`` file with an HTTP Range request.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import httpx

from . import __version__

USER_AGENT = f"Exan/{__version__} (+https://github.com/franciscosuca/exan)"
FREE_SPACE_MARGIN = 256 * 1024 * 1024
_HASH_CHUNK = 4 * 1024 * 1024


class DownloadError(Exception):
    """A download problem with a stable ``code`` the UI can translate."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def part_path(target: Path) -> Path:
    return target.with_name(target.name + ".part")


def ensure_free_space(directory: Path, needed: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(directory).free
    if needed > 0 and free < needed + FREE_SPACE_MARGIN:
        gb = 1024**3
        raise DownloadError(
            "disk_full",
            f"Not enough free disk space: {needed / gb:.1f} GB are needed, {free / gb:.1f} GB are free.",
        )


def _hash_file(path: Path, digest: hashlib._Hash) -> None:
    with path.open("rb") as handle:
        while chunk := handle.read(_HASH_CHUNK):
            digest.update(chunk)


def new_client(transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    # trust_env keeps system proxy settings, which school networks often need.
    return httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, read=120.0),
        headers={"User-Agent": USER_AGENT},
        transport=transport,
    )


async def download_file(
    client: httpx.AsyncClient,
    url: str,
    target: Path,
    *,
    size: int,
    sha256: str,
    on_progress: Callable[[int], None] | None = None,
) -> None:
    """Download ``url`` to ``target`` unless it is already complete. Raises DownloadError."""
    report = on_progress or (lambda _done: None)
    if target.is_file() and target.stat().st_size == size:
        report(size)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    part = part_path(target)
    digest = hashlib.sha256()
    done = part.stat().st_size if part.is_file() else 0
    if done > size:
        part.unlink()
        done = 0
    if done:
        await asyncio.to_thread(_hash_file, part, digest)
    report(done)

    if done < size:
        headers = {"Range": f"bytes={done}-"} if done else {}
        try:
            async with client.stream("GET", url, headers=headers) as response:
                if response.status_code == 206 and done:
                    mode = "ab"
                elif response.status_code == 200:
                    # The server sent the whole file (Range ignored or no partial file): start over.
                    mode, done, digest = "wb", 0, hashlib.sha256()
                else:
                    raise DownloadError(
                        "download_failed", f"The download server answered with HTTP {response.status_code}."
                    )
                with part.open(mode) as handle:
                    async for chunk in response.aiter_bytes():
                        done += len(chunk)
                        if done > size:
                            raise DownloadError(
                                "download_corrupt", "The downloaded file is larger than expected."
                            )
                        handle.write(chunk)
                        digest.update(chunk)
                        report(done)
        except httpx.HTTPError as exc:
            raise DownloadError(
                "download_failed", f"The download was interrupted ({type(exc).__name__}). Try again."
            ) from exc

    if done != size:
        raise DownloadError("download_failed", "The download ended early. Try again to continue it.")
    if digest.hexdigest() != sha256.lower():
        part.unlink(missing_ok=True)
        raise DownloadError(
            "download_corrupt", "The downloaded file is damaged (checksum mismatch). Try again."
        )
    os.replace(part, target)
