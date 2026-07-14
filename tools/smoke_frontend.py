"""End-to-end smoke test for the built MadPlan frontend.

Serves `frontend_new/dist` plus the live `outputs/` feeds with the same
handler used by serve.py, then drives the real UI with Playwright:
search, event modal, agenda, map view and news view.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import serve


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    port = _free_port()
    server = serve.SERVER_CLASS(("127.0.0.1", port), serve.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1600})
            console_errors: list[str] = []
            page_errors: list[str] = []

            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))

            page.goto(base_url, wait_until="domcontentloaded", timeout=30_000)

            page.get_by_text("Qué hacer en Madrid").wait_for(timeout=30_000)
            page.locator('[data-testid="search-input"]').wait_for(timeout=30_000)
            page.locator('[data-testid="event-card"]').first.wait_for(timeout=30_000)

            first_title = page.locator('[data-testid="event-card"] h3').first.inner_text(timeout=10_000).split()[0]
            page.locator('[data-testid="search-input"]').fill(first_title)
            page.wait_for_timeout(400)
            assert page.locator('[data-testid="event-card"]').count() > 0, "search returned no cards"
            assert "q=" in page.url, "query not synced to URL"

            page.locator('[data-testid="event-card"]').first.locator("button").first.click()
            dialog = page.get_by_role("dialog")
            assert dialog.is_visible(timeout=10_000)
            dialog.get_by_role("button", name="Guardar en mi agenda").click(timeout=10_000)
            page.get_by_role("button", name="Cerrar detalle del evento").click(timeout=10_000)

            page.locator('[data-testid="open-agenda"]').click(timeout=10_000)
            assert page.get_by_text("Mi agenda").first.is_visible(timeout=10_000)
            page.get_by_role("button", name="Cerrar agenda").click(timeout=10_000)

            page.get_by_role("navigation", name="Secciones").get_by_role("button").nth(1).click(timeout=10_000)
            page.wait_for_timeout(1500)
            assert page.locator(".leaflet-container").is_visible(), "map did not render"
            assert "view=map" in page.url

            page.get_by_role("navigation", name="Secciones").get_by_role("button").nth(2).click(timeout=10_000)
            page.wait_for_timeout(500)
            assert page.get_by_text("Actualidad de Madrid").is_visible(timeout=10_000)
            assert "view=news" in page.url

            browser.close()

        assert not console_errors, f"Console errors detected: {console_errors}"
        assert not page_errors, f"Page errors detected: {page_errors}"

        print(
            json.dumps(
                {
                    "ok": True,
                    "url": base_url,
                    "checks": [
                        "home_loaded",
                        "search_works",
                        "url_state_works",
                        "modal_works",
                        "agenda_works",
                        "map_works",
                        "news_works",
                    ],
                },
                ensure_ascii=False,
            )
        )
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
