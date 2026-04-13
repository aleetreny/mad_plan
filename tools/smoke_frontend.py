"""Small runtime smoke test for the static frontend."""

from __future__ import annotations

import json
import socket
import sys
import threading
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import serve


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _fetch_text(url: str) -> str:
    with urlopen(url, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected status for {url}: {response.status}")
        return response.read().decode("utf-8")


def main() -> None:
    port = _free_port()
    server = serve.http.server.HTTPServer(("127.0.0.1", port), serve.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"

    try:
        index = _fetch_text(f"{base_url}/")
        script = _fetch_text(f"{base_url}/app.js")
        styles = _fetch_text(f"{base_url}/styles.css")
        favicon = _fetch_text(f"{base_url}/favicon.ico")
        plans = json.loads(_fetch_text(f"{base_url}/outputs/eventos_madrid_all.json"))
        news = json.loads(_fetch_text(f"{base_url}/outputs/noticias_madrid_all.json"))

        assert "MadPlan" in index
        assert "mood-grid" in index
        assert "share-view" in index
        assert "loadData" in script
        assert ".hero" in styles
        assert "<svg" in favicon
        assert isinstance(plans, list) and len(plans) > 1000
        assert isinstance(news, list) and len(news) > 0

        print(
            json.dumps(
                {
                    "ok": True,
                    "planes": len(plans),
                    "noticias": len(news),
                },
                ensure_ascii=False,
            )
        )
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()