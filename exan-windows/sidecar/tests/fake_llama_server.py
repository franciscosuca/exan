"""Stand-in for llama.cpp's llama-server in tests: same flags, /health and /v1/chat/completions.

Every chat request is appended (as JSON) to the file named by FAKE_LLAMA_LOG. FAKE_LLAMA_MODE=crash makes
the server exit before it becomes healthy.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main() -> int:
    parser = argparse.ArgumentParser()
    for flag in (
        "--model",
        "--mmproj",
        "--host",
        "--port",
        "--ctx-size",
        "--parallel",
        "--alias",
        "--api-key",
    ):
        parser.add_argument(flag)
    parser.add_argument("--no-webui", action="store_true")
    args, _unknown = parser.parse_known_args()
    api_key = args.api_key or os.environ.get("LLAMA_API_KEY")
    print(f"fake llama-server loading {args.model}", flush=True)
    if os.environ.get("FAKE_LLAMA_MODE") == "crash":
        print("error: failed to load model (out of memory)", flush=True)
        return 1
    log_path = os.environ.get("FAKE_LLAMA_LOG")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            pass

        def _send(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self) -> None:
            if not api_key or self.headers.get("Authorization") != f"Bearer {api_key}":
                self._send(401, {"error": {"message": "Invalid API Key"}})
                return
            request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            if log_path:
                with open(log_path, "a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps({"alias": args.alias, "model_path": args.model, **request}) + "\n"
                    )
            text = os.environ.get("FAKE_LLAMA_REPLY", "1. B\n2. C")
            self._send(200, {"choices": [{"message": {"role": "assistant", "content": text}}]})

    server = ThreadingHTTPServer((args.host, int(args.port)), Handler)
    with contextlib.suppress(KeyboardInterrupt):
        server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
