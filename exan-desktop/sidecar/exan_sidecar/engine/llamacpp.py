"""Built-in model runtime: Exan ships llama.cpp's ``llama-server`` and starts it for the selected model.

The server listens on 127.0.0.1 with a random port and a random API key, runs one model at a time and is
stopped when the engine stops. A PID file lets a restarted engine stop a server left over by a crash.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import secrets
import shlex
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import httpx

from .base import EngineError, ModelInfo, ProgressCallback, RuntimeStatus
from .builtin_catalog import BuiltinModel, catalog, get_model
from .model_store import ModelStore
from .openai_compat import OpenAICompatEngine

log = logging.getLogger(__name__)

SERVER_NAME = "llama-server.exe" if sys.platform == "win32" else "llama-server"
STARTUP_TIMEOUT = 180.0
STOP_TIMEOUT = 5.0
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _process_command(pid: int) -> str:
    """Name/path of a running process, or "" when it does not exist (best effort, no extra packages)."""
    try:
        if sys.platform == "win32":
            out = subprocess.run(  # noqa: S603 - fixed system tool, numeric argument
                ["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV", "/NH"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=_NO_WINDOW,
            ).stdout
            return out if f'"{int(pid)}"' in out else ""
        out = subprocess.run(  # noqa: S603 - fixed system tool, numeric argument
            ["ps", "-o", "comm=", "-p", str(int(pid))],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        return out.strip()
    except (OSError, subprocess.SubprocessError, ValueError):
        return ""


def _terminate_pid(pid: int) -> None:
    with contextlib.suppress(OSError):
        os.kill(pid, signal.SIGTERM)
    if sys.platform == "win32":
        return
    deadline = time.monotonic() + STOP_TIMEOUT
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.1)
    with contextlib.suppress(OSError):
        os.kill(pid, signal.SIGKILL)


class LlamaServer:
    """Starts, watches and stops one ``llama-server`` process."""

    def __init__(
        self,
        runtime_dir: Path | None,
        log_dir: Path,
        state_dir: Path,
        *,
        command: Sequence[str] | None = None,
        startup_timeout: float = STARTUP_TIMEOUT,
    ) -> None:
        self.runtime_dir = runtime_dir
        self.log_path = log_dir / "runtime.log"
        self.pid_file = state_dir / "runtime.pid"
        self.startup_timeout = startup_timeout
        self._command = list(command) if command else None
        self._process: subprocess.Popen[bytes] | None = None
        self._model_id: str | None = None
        self._port: int | None = None
        self._api_key: str | None = None
        self._lock = asyncio.Lock()

    # -- discovery ------------------------------------------------------------------
    @property
    def binary(self) -> Path | None:
        if self.runtime_dir is None:
            return None
        path = self.runtime_dir / SERVER_NAME
        return path if path.is_file() else None

    @property
    def available(self) -> bool:
        return self._command is not None or self.binary is not None

    @property
    def version(self) -> str | None:
        if self.runtime_dir is None:
            return None
        with contextlib.suppress(OSError):
            return (self.runtime_dir / "VERSION").read_text(encoding="utf-8").strip() or None
        return None

    @property
    def model_id(self) -> str | None:
        return self._model_id if self._alive() else None

    def _alive(self) -> bool:
        return self._process is not None and self._process.poll() is None

    # -- lifecycle ------------------------------------------------------------------
    async def ensure(self, model: BuiltinModel, paths: dict[str, Path]) -> tuple[str, str]:
        """Make sure ``model`` is loaded; returns (base URL of the OpenAI API, API key)."""
        async with self._lock:
            if not (self._alive() and self._model_id == model.id):
                await asyncio.to_thread(self._stop_sync)
                await self._start(model, paths)
            assert self._port is not None and self._api_key is not None
            return f"http://127.0.0.1:{self._port}/v1", self._api_key

    async def stop(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._stop_sync)

    def stop_now(self) -> None:
        """Synchronous stop for the shutdown path (called from a non-event-loop thread)."""
        self._stop_sync()

    def _base_command(self) -> list[str]:
        if self._command is not None:
            return list(self._command)
        binary = self.binary
        if binary is None:
            raise EngineError(
                "runtime_missing",
                "The built-in model runtime is missing from this installation. Reinstall Exan "
                "(developers: run `npm run setup`).",
            )
        return [str(binary)]

    async def _start(self, model: BuiltinModel, paths: dict[str, Path]) -> None:
        command = self._base_command()
        await asyncio.to_thread(self.cleanup_stale)
        port = free_port()
        # Hex keys never start with "-" (which a command-line parser would read as an option).
        api_key = secrets.token_hex(24)
        args = [
            *command,
            "--model",
            str(paths["model"]),
            "--mmproj",
            str(paths["mmproj"]),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--ctx-size",
            str(model.ctx_size),
            "--parallel",
            "1",
            "--alias",
            model.id,
            "--no-webui",
            *shlex.split(os.environ.get("EXAN_RUNTIME_ARGS", "")),
        ]
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Starting the built-in runtime for %s on port %s", model.id, port)
        with self.log_path.open("wb") as log_file:
            try:
                process = subprocess.Popen(  # noqa: S603 - our own bundled binary, no shell
                    args,
                    # The key goes through the environment, so it does not show up in process lists.
                    env={**os.environ, "LLAMA_API_KEY": api_key},
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.runtime_dir) if self.runtime_dir and self.runtime_dir.is_dir() else None,
                    creationflags=_NO_WINDOW,
                )
            except OSError as exc:
                raise EngineError(
                    "runtime_failed", f"The built-in runtime could not be started: {exc}"
                ) from exc
        self._process, self._model_id, self._port, self._api_key = process, model.id, port, api_key
        with contextlib.suppress(OSError):
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            self.pid_file.write_text(json.dumps({"pid": process.pid}), encoding="utf-8")
        try:
            await self._wait_ready(process, port, model)
        except BaseException:
            await asyncio.to_thread(self._stop_sync)
            raise

    async def _wait_ready(self, process: subprocess.Popen[bytes], port: int, model: BuiltinModel) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.startup_timeout
        async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
            while True:
                if process.poll() is not None:
                    details = self.log_tail()
                    raise EngineError(
                        "runtime_failed",
                        f"The built-in runtime stopped while loading {model.label}. {details}".strip(),
                    )
                with contextlib.suppress(httpx.HTTPError):
                    if (await client.get(f"http://127.0.0.1:{port}/health")).status_code == 200:
                        return
                if loop.time() > deadline:
                    raise EngineError("runtime_failed", f"{model.label} did not load in time.")
                await asyncio.sleep(0.25)

    def _stop_sync(self) -> None:
        process, self._process = self._process, None
        self._model_id = self._port = self._api_key = None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=STOP_TIMEOUT)
            except subprocess.TimeoutExpired:
                process.kill()
                with contextlib.suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=STOP_TIMEOUT)
        with contextlib.suppress(OSError):
            self.pid_file.unlink()

    def cleanup_stale(self) -> None:
        """Stop a runtime left over by an engine that crashed (identified through the PID file)."""
        try:
            pid = int(json.loads(self.pid_file.read_text(encoding="utf-8"))["pid"])
        except (OSError, ValueError, KeyError, TypeError):
            return
        if self._process is not None and self._process.pid == pid:
            return
        if "llama-server" in _process_command(pid).lower():
            log.warning("Stopping a built-in runtime left over from a previous start (pid %s)", pid)
            _terminate_pid(pid)
        with contextlib.suppress(OSError):
            self.pid_file.unlink()

    def log_tail(self, lines: int = 3) -> str:
        try:
            text = self.log_path.read_bytes()[-4000:].decode("utf-8", "replace")
        except OSError:
            return ""
        useful = [line.strip() for line in text.splitlines() if line.strip()]
        errors = [line for line in useful if "error" in line.lower() or "failed" in line.lower()]
        return " | ".join((errors or useful)[-lines:])[:500]


class BuiltinEngine:
    """VisionEngine for the built-in runtime: downloads models and reads pages with llama-server."""

    kind = "builtin"
    base_url = "builtin"

    def __init__(self, store: ModelStore, server: LlamaServer, *, timeout: float = 300) -> None:
        self.store = store
        self.server = server
        self.timeout = timeout
        self._clients: dict[tuple[str, str], OpenAICompatEngine] = {}

    async def status(self) -> RuntimeStatus:
        status = RuntimeStatus(
            kind=self.kind,
            url="",
            reachable=self.server.available,
            version=self.server.version,
            models=[
                ModelInfo(name=m.id, size=m.download_bytes, vision=True, parameters=m.params)
                for m in catalog()
                if self.store.is_installed(m)
            ],
        )
        if not self.server.available:
            status.error = EngineError(
                "runtime_missing", "The built-in model runtime is missing from this installation."
            )
        return status

    def _model(self, name: str) -> BuiltinModel:
        model = get_model(name)
        if model is None:
            raise EngineError("model_missing", f"'{name}' is not one of Exan's built-in models.")
        return model

    async def complete(self, *, model: str, prompt: str, image_jpeg: bytes, schema: dict | None) -> str:
        entry = self._model(model)
        if not self.store.is_installed(entry):
            raise EngineError(
                "model_missing", f"{entry.label} is not downloaded yet. Download it in the settings."
            )
        base_url, api_key = await self.server.ensure(entry, self.store.paths(entry))
        client = self._clients.get((base_url, api_key))
        if client is None:
            for stale in self._clients.values():
                await stale.aclose()
            client = OpenAICompatEngine(
                base_url,
                timeout=self.timeout,
                max_tokens=entry.max_tokens,
                api_key=api_key,
                options=entry.sampling,
            )
            self._clients = {(base_url, api_key): client}
        try:
            return await client.complete(model=entry.id, prompt=prompt, image_jpeg=image_jpeg, schema=schema)
        except EngineError as exc:
            if exc.code == "unreachable":
                # The server crashed (for example out of memory); start it again on the next page.
                await self.server.stop()
                raise EngineError(
                    "runtime_failed",
                    f"The built-in runtime stopped while reading. {self.server.log_tail()}".strip(),
                ) from exc
            raise

    async def pull(self, model: str, progress: ProgressCallback) -> None:
        from ..downloads import DownloadError

        entry = self._model(model)
        try:
            await self.store.download(entry, progress)
        except DownloadError as exc:
            raise EngineError(exc.code, exc.message) from exc

    async def aclose(self) -> None:
        for client in self._clients.values():
            with contextlib.suppress(Exception):
                await client.aclose()
        self._clients.clear()
        await self.server.stop()
