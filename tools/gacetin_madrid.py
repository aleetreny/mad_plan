"""Gacetin Madrid culture and leisure news scraper.

Uses the public WordPress REST API limited to the `Cultura y Ocio` category,
keeping only recent Madrid culture/news items with clear event, plan, or leisure
signal.

Output: outputs/noticias_gacetin_madrid.json
"""

from __future__ import annotations

import json
import logging
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

try:
    from .normalization import normalize_news_records
except ImportError:
    from normalization import normalize_news_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://gacetinmadrid.com"
API_URL = f"{BASE_URL}/wp-json/wp/v2/posts"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "outputs" / "noticias_gacetin_madrid.json"
)
SOURCE_NAME = "gacetin_madrid"
REQUEST_TIMEOUT = 30
DISCOVERY_LOOKBACK_DAYS = 30
PER_PAGE = 100
MAX_PAGES = 5
OCIO_CATEGORY_ID = 7
GENERIC_CATEGORIES = {"Noticias"}
SCOPE_TOKENS = (
    "actividad",
    "agenda",
    "arte",
    "cine",
    "ciclo",
    "conciert",
    "cultural",
    "cultura",
    "danza",
    "entrada",
    "espectac",
    "experiencia",
    "expo",
    "expos",
    "familia",
    "feria",
    "festival",
    "fiesta",
    "gastron",
    "gratuit",
    "guardia",
    "libro",
    "mercad",
    "muestra",
    "museo",
    "ocio",
    "palacio",
    "patrimonio",
    "plan",
    "programa",
    "recorrido",
    "relevo",
    "ruta",
    "sesion",
    "tapa",
    "teatro",
    "tren",
    "vermu",
    "visita",
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split())


def _dedupe_strings(values: list[Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(text)
    return ordered


def _normalize_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", _clean_text(value))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return normalized.casefold()


def _strip_html(value: Any) -> str:
    text = str(value or "")
    return _clean_text(BeautifulSoup(text, "html.parser").get_text(" ", strip=True))


def _request_posts(session: requests.Session, *, page: int, after: str) -> tuple[list[dict[str, Any]], int]:
    response = session.get(
        API_URL,
        params={
            "categories": OCIO_CATEGORY_ID,
            "per_page": PER_PAGE,
            "page": page,
            "after": after,
            "_embed": "1",
            "orderby": "date",
            "order": "desc",
            "status": "publish",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    total_pages = int(response.headers.get("X-WP-TotalPages") or "1")
    return response.json(), total_pages


def _discovery_after_iso() -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DISCOVERY_LOOKBACK_DAYS)
    return cutoff.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _wp_datetime_to_iso(value: str | None) -> str | None:
    raw = _clean_text(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_author(post: dict[str, Any]) -> str | None:
    authors = post.get("_embedded", {}).get("author") or []
    if not authors:
        return None
    return _clean_text(authors[0].get("name")) or None


def _extract_featured_image(post: dict[str, Any]) -> str | None:
    media_items = post.get("_embedded", {}).get("wp:featuredmedia") or []
    if not media_items:
        return None
    return _clean_text(media_items[0].get("source_url")) or None


def _extract_embedded_terms(post: dict[str, Any], taxonomy: str) -> list[str]:
    values: list[str] = []
    for group in post.get("_embedded", {}).get("wp:term", []):
        if not isinstance(group, list):
            continue
        for term in group:
            if not isinstance(term, dict):
                continue
            if term.get("taxonomy") != taxonomy:
                continue
            values.append(term.get("name"))
    return _dedupe_strings(values)


def _extract_categories(post: dict[str, Any]) -> list[str]:
    categories = _extract_embedded_terms(post, "category")
    primary = [value for value in categories if value == "Cultura y Ocio"]
    secondary = [
        value for value in categories if value not in GENERIC_CATEGORIES and value != "Cultura y Ocio"
    ]
    return primary + secondary or ["Cultura y Ocio"]


def _extract_tags(post: dict[str, Any]) -> list[str]:
    return _extract_embedded_terms(post, "post_tag")


def _extract_body(content_html: str) -> str:
    soup = BeautifulSoup(content_html or "", "html.parser")
    paragraphs: list[str] = []
    for node in soup.find_all(["p", "h2", "h3", "li"]):
        text = _clean_text(node.get_text(" ", strip=True))
        if not text or text.startswith("http"):
            continue
        if len(text) < 30 and node.name == "p":
            continue
        if text not in paragraphs:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _extract_summary(excerpt_html: str, body_text: str) -> str | None:
    excerpt = _strip_html(excerpt_html)
    if excerpt:
        return excerpt
    if not body_text:
        return None
    return body_text.split("\n\n", 1)[0]


def _has_scope_signal(*, title: str, summary: str | None, tags: list[str]) -> bool:
    blob = " ".join(
        _normalize_text(part)
        for part in [title, summary or "", *tags]
        if part
    )
    return any(token in blob for token in SCOPE_TOKENS)


def _build_record(post: dict[str, Any]) -> dict[str, Any] | None:
    title = _strip_html(post.get("title", {}).get("rendered"))
    if not title:
        return None

    categories = _extract_categories(post)
    tags = _extract_tags(post)
    body_text = _extract_body(post.get("content", {}).get("rendered") or "")
    summary = _extract_summary(post.get("excerpt", {}).get("rendered") or "", body_text)
    if not _has_scope_signal(title=title, summary=summary, tags=tags):
        return None

    return {
        "id": str(post.get("id") or post.get("slug") or title),
        "titulo": title,
        "descripcion": summary,
        "contenido": body_text or summary,
        "categorias": categories,
        "etiquetas": tags,
        "autor": _extract_author(post),
        "url": _clean_text(post.get("link")) or None,
        "imagen": _extract_featured_image(post),
        "fecha_publicacion": _wp_datetime_to_iso(post.get("date_gmt") or post.get("date")),
        "fecha_actualizacion": _wp_datetime_to_iso(post.get("modified_gmt") or post.get("modified")),
        "metadata": {
            "wp_post_id": post.get("id"),
            "slug": _clean_text(post.get("slug")) or None,
            "status": _clean_text(post.get("status")) or None,
        },
    }


def scrape_gacetin_madrid_news() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)
    after = _discovery_after_iso()
    raw_posts: list[dict[str, Any]] = []
    total_pages = 1

    for page in range(1, MAX_PAGES + 1):
        posts, total_pages = _request_posts(session, page=page, after=after)
        raw_posts.extend(posts)
        log.info(
            "Fetched Gacetin Madrid ocio page %d/%d: %d posts",
            page,
            total_pages,
            len(posts),
        )
        if page >= total_pages:
            break

    records: list[dict[str, Any]] = []
    for post in raw_posts:
        record = _build_record(post)
        if record:
            records.append(record)

    normalized = normalize_news_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d Gacetin Madrid news items to %s", len(normalized), OUTPUT_FILE)
    return normalized


if __name__ == "__main__":
    results = scrape_gacetin_madrid_news()
    by_category: dict[str, int] = {}
    for item in results:
        category = item.get("categoria_principal") or "Sin categoria"
        by_category[category] = by_category.get(category, 0) + 1
    log.info("Summary: %d news items, %d categories", len(results), len(by_category))