"""Static server for the current MadPlan frontend and live outputs feed."""

import http.server
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend_new" / "dist"
OUTPUTS = ROOT / "outputs"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
SERVER_CLASS = http.server.ThreadingHTTPServer


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path == "/favicon.ico":
            return str(FRONTEND / "favicon.svg")
        if path.startswith("/outputs/"):
            return str(OUTPUTS / path[len("/outputs/"):])
        rel = path.lstrip("/") or "index.html"
        return str(FRONTEND / rel)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    if not FRONTEND.exists():
        raise SystemExit(
            "No se encontró frontend_new/dist. Ejecuta `cd frontend_new && npm run build` antes de usar serve.py."
        )
    os.chdir(str(ROOT))
    with SERVER_CLASS(("127.0.0.1", PORT), Handler) as srv:
        print(f"  -> http://127.0.0.1:{PORT}")
        srv.serve_forever()
