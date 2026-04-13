"""Minimal dev server that serves frontend/ and outputs/ under one origin."""

import http.server
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
OUTPUTS = ROOT / "outputs"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        # Strip query / fragment
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path == "/favicon.ico":
            return str(FRONTEND / "favicon.svg")
        # Route outputs/* to project outputs/
        if path.startswith("/outputs/"):
            return str(OUTPUTS / path[len("/outputs/"):])
        # Everything else from frontend/
        rel = path.lstrip("/") or "index.html"
        return str(FRONTEND / rel)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    os.chdir(str(ROOT))
    with http.server.HTTPServer(("127.0.0.1", PORT), Handler) as srv:
        print(f"  → http://127.0.0.1:{PORT}")
        srv.serve_forever()
