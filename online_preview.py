#!/usr/bin/env python3
"""Serve neredenaldim.html publicly via an ngrok tunnel."""
from __future__ import annotations

import argparse
import contextlib
import http.server
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Optional

try:
    from pyngrok import conf, ngrok
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    print(
        "pyngrok module is required. Install it with 'pip install pyngrok' and try again.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


class SingleFileHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serve a single HTML file while keeping asset paths relative."""

    def __init__(self, *args, base_path: Path, **kwargs):
        self.base_path = base_path
        super().__init__(*args, directory=str(base_path.parent), **kwargs)

    def translate_path(self, path: str) -> str:  # pragma: no cover - inherited behaviour
        # Always map the root URL to the requested file and delegate other paths normally.
        if path in {"/", ""}:
            return str(self.base_path)
        return super().translate_path(path)

    def log_message(self, format: str, *args):  # pragma: no cover - cosmetic override
        # Reduce console noise to just status codes.
        sys.stdout.write("[HTTP] " + format % args + "\n")


def find_available_port(preferred: int = 8000) -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if not sock.connect_ex(("127.0.0.1", preferred)):
            preferred = 0
        sock.bind(("", preferred))
        return sock.getsockname()[1]


def start_server(html_file: Path, port: int) -> http.server.ThreadingHTTPServer:
    handler_factory = lambda *args, **kwargs: SingleFileHTTPRequestHandler(  # noqa: E731
        *args, base_path=html_file, **kwargs
    )
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler_factory)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def open_tunnel(port: int, auth_token: Optional[str]) -> str:
    if auth_token:
        conf.get_default().auth_token = auth_token
    public_url = ngrok.connect(port, proto="http")
    return str(public_url.public_url)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "html",
        nargs="?",
        default="neredenaldim.html",
        help="HTML file to publish (default: neredenaldim.html)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Local port to serve before tunnelling (default: 8000)",
    )
    parser.add_argument(
        "--auth-token",
        dest="auth_token",
        default=os.getenv("NGROK_AUTHTOKEN"),
        help="Ngrok auth token. Falls back to NGROK_AUTHTOKEN env var if omitted.",
    )

    args = parser.parse_args()
    html_file = Path(args.html).resolve()

    if not html_file.exists():
        print(f"Cannot find {html_file}.", file=sys.stderr)
        return 1

    port = find_available_port(args.port)
    server = start_server(html_file, port)

    print(f"Serving {html_file} on http://127.0.0.1:{port}")

    try:
        public_url = open_tunnel(port, args.auth_token)
    except Exception as exc:  # pragma: no cover - depends on ngrok responses
        server.shutdown()
        raise SystemExit(f"Failed to establish ngrok tunnel: {exc}")

    print("Public preview ready:")
    print(public_url)
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        ngrok.disconnect(public_url)
        server.shutdown()
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
