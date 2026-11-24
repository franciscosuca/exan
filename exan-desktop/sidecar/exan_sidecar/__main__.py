"""Entry point: ``python -m exan_sidecar`` (or the frozen ``exan-sidecar`` executable).

The desktop shell starts this process with ``EXAN_SECRET`` (and optionally ``EXAN_PORT``) in the environment,
reads the ``EXAN_PORT=<port>`` line from stdout and sends the secret as a bearer token on every request.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import socket
import sys
import threading
import time
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

import uvicorn

from . import __version__, cli
from .config import ConfigError, RuntimeConfig

log = logging.getLogger("exan_sidecar")

SHUTDOWN_COMMANDS = {"shutdown", "exit", "quit"}
FORCED_EXIT_GRACE_SECONDS = 5.0


def setup_logging(log_dir: Path) -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    root.addHandler(console)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "sidecar.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    except OSError:
        log.warning("Cannot write log files to %s", log_dir)
    else:
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    for noisy in ("httpx", "httpcore", "multipart", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def watch_stdin(
    server: uvicorn.Server, stream: TextIO | None = None, *, on_exit: Callable[[], None] | None = None
) -> threading.Thread:
    """Stop when the desktop shell says so or disappears (stdin closes)."""
    source = stream if stream is not None else sys.stdin

    def run() -> None:
        try:
            for line in source:
                if line.strip().lower() in SHUTDOWN_COMMANDS:
                    break
        except (OSError, ValueError):
            pass
        log.info("Shutting down (requested by the desktop shell)")
        server.should_exit = True
        time.sleep(FORCED_EXIT_GRACE_SECONDS)
        log.warning("Forcing exit after the shutdown grace period")
        if on_exit is not None:
            with contextlib.suppress(Exception):
                on_exit()
        logging.shutdown()
        os._exit(0)

    thread = threading.Thread(target=run, name="exan-stdin-watch", daemon=True)
    thread.start()
    return thread


def bind_socket(host: str, port: int) -> socket.socket:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((host, port))
        sock.listen(128)
    except OSError:
        sock.close()
        raise
    return sock


def configure_stdio() -> None:
    # Windows pipes default to the ANSI code page; file names in log lines must never crash the engine.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(prog="exan-sidecar", description="Local engine of the Exan desktop app.")
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    subparsers = parser.add_subparsers(dest="command")
    cli.add_parser(subparsers)
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command == "models":
        return cli.run(args)

    try:
        config = RuntimeConfig.from_env()
    except ConfigError as exc:
        print(f"exan-sidecar: {exc}", file=sys.stderr)
        return 2

    setup_logging(config.log_dir)

    from .api import create_app
    from .state import AppState

    state = AppState(config)
    app = create_app(state)
    try:
        sock = bind_socket(config.host, config.port)
    except OSError as exc:
        log.error("Cannot listen on %s:%s: %s", config.host, config.port, exc)
        return 3
    port = int(sock.getsockname()[1])
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            log_config=None,
            access_log=False,
            lifespan="on",
            http="h11",
            loop="asyncio",
            ws="none",
            server_header=False,
            proxy_headers=False,
            timeout_graceful_shutdown=2,
            timeout_keep_alive=30,
        )
    )
    if config.watch_stdin:
        watch_stdin(server, on_exit=state.llama.stop_now)
    log.info("Exan engine %s listening on %s:%s", __version__, config.host, port)
    print(f"EXAN_PORT={port}", flush=True)
    server.run(sockets=[sock])
    state.llama.stop_now()
    log.info("Exan engine stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
