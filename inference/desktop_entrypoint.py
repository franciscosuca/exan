"""Run the inference API as a Tauri-managed local sidecar."""

import socket
import sys

import uvicorn

from app.config import settings


def main() -> None:
    secret = settings.startup_secret
    if not secret:
        raise RuntimeError("STARTUP_SECRET must be set for the desktop sidecar")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        sock.set_inheritable(True)
        port = sock.getsockname()[1]
        print(f"EXAN_PORT={port}", flush=True)
        config = uvicorn.Config(
            "app.main:app",
            host="127.0.0.1",
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        server.run(sockets=[sock])


if __name__ == "__main__":
    sys.exit(main())
