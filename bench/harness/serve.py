"""Serve the model-facing forms. Only bench/site is reachable, so no schema or gold can be fetched.

    serve.py [--port 8787]
"""
from __future__ import annotations

import argparse
import functools
import http.server
import threading
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def do_POST(self) -> None:  # the submit beacon
        self.send_response(204)
        self.end_headers()


def start(port: int = 0) -> http.server.ThreadingHTTPServer:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Quiet, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", ap.parse_args().port), functools.partial(Quiet, directory=str(SITE)))
    print(f"http://127.0.0.1:{server.server_address[1]}/", flush=True)
    server.serve_forever()
