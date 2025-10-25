#!/usr/bin/env python3
"""Serve neredenaldim.html locally and open it in the default browser."""

from __future__ import annotations

import contextlib
import http.server
import os
import socket
import threading
import time
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "neredenaldim.html"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that silences default logging noise."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: D401 (match signature)
        return


def find_free_port(preferred: int = 8000) -> int:
    """Return an available TCP port, preferring ``preferred`` when free."""

    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if sock.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred

    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> None:
    if not HTML_FILE.exists():
        raise SystemExit(f"Could not find {HTML_FILE.name} next to this script.")

    os.chdir(ROOT)
    port = find_free_port(8000)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), QuietHandler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/{HTML_FILE.name}"
    print("NeredenAldım arayüzü hazır!", flush=True)
    print(f"Tarayıcınız otomatik açılmazsa bu bağlantıyı kopyalayın: {url}", flush=True)

    webbrowser.open(url)

    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nSunucu kapatılıyor...", flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
