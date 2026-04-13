"""Wegow Madrid concerts and festivals scraper.

Uses Wegow's public API to discover Madrid events and enrich each item from its
detail endpoint.

Output: outputs/eventos_wegow.json
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

import requests

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

API_BASE_URL = "https://api.wegow.com/api"
CITY_SEARCH_URL = f"{API_BASE_URL}/location-search/"
EVENTS_URL = f"{API_BASE_URL}/events/"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "eventos_wegow.json"
SOURCE_NAME = "wegow"
REQUEST_TIMEOUT = 30
PAGE_SIZE = 200
MADRID_QUERY = "madrid"
SPAIN_COUNTRY_ID = 1
MADRID_CITY_NAME = "Madrid"
BLOCKLIST_TOKENS = ("prueba", "redirection", "redirections", "barra-baja")
TYPE_CONFIG = {
    0: ["Conciertos", "Musica"],
    1: ["Festivales", "Musica"],
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "es",
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


def _request_json(
    session: requests.Session, url: str, *, params: dict[str, Any] | None = None
) -> Any:
    response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _extract_madrid_city(session: requests.Session) -> dict[str, Any]:
    payload = _request_json(session, CITY_SEARCH_URL, params={"query": MADRID_QUERY})
    cities = payload.get("cities") or []
    for city in cities:
        if _clean_text(city.get("name")) != MADRID_CITY_NAME:
            continue
        country = city.get("country") or {}
        if country.get("code") == SPAIN_COUNTRY_ID or country.get("iso_code") == "ES":
            return city
    raise ValueError("Could not resolve Wegow Madrid city id")


def _extract_event_summaries(
    session: requests.Session, *, city_id: int, country_id: int
) -> list[dict[str, Any]]:
    records_by_id: dict[int, dict[str, Any]] = {}

    for event_type in sorted(TYPE_CONFIG):
        payload = _request_json(
            session,
            EVENTS_URL,
            params={
                "type": event_type,
                "cities": str(city_id),
                "country": country_id,
                "page_size": PAGE_SIZE,
                "count": True,
                "sda": "desktop-filters-events",
            },
        )
        events = payload.get("events") or []
        log.info(
            "Fetched %d Wegow items for type=%s (count=%s)",
            len(events),
            event_type,
            payload.get("count"),
        )
        for item in events:
            event_id = item.get("id")
            if not event_id:
                continue
            records_by_id[event_id] = item

    return list(records_by_id.values())


def _build_categories(detail: dict[str, Any]) -> list[str]:
    event_type = detail.get("type")
    categories = list(TYPE_CONFIG.get(event_type, ["Musica"]))

    description = _clean_text(detail.get("description")).casefold()
    if any(token in description for token in ("festival", "fest ")) and "Festivales" not in categories:
        categories.insert(0, "Festivales")
    return _dedupe_strings(categories)


def _extract_tags(detail: dict[str, Any]) -> list[str]:
    artists = detail.get("artists") or []
    tags = [_clean_text(artist.get("name")) for artist in artists if isinstance(artist, dict)]
    return _dedupe_strings(tags)


def _extract_price(detail: dict[str, Any]) -> tuple[float | None, str | None]:
    for key in ("price", "min_price", "max_price"):
        value = detail.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value), _clean_text(detail.get("currency")) or None
        except (TypeError, ValueError):
            continue
    return None, _clean_text(detail.get("currency")) or None


def _extract_image(detail: dict[str, Any], summary: dict[str, Any]) -> str | None:
    image = _clean_text(detail.get("image_url"))
    if image:
        return image
    return _clean_text(summary.get("image_url")) or None


def _has_madrid_evidence(summary: dict[str, Any], detail: dict[str, Any]) -> bool:
    venue = detail.get("venue") or summary.get("venue") or {}
    city = detail.get("city") or summary.get("city") or {}
    values = [
        detail.get("title"),
        detail.get("subtitle"),
        detail.get("description"),
        detail.get("permalink"),
        detail.get("purchase_url"),
        venue.get("name"),
        venue.get("address"),
        city.get("name"),
        summary.get("title"),
        summary.get("slug"),
    ]
    return any(MADRID_QUERY in _clean_text(value).casefold() for value in values if value)


def _should_skip_event(summary: dict[str, Any], detail: dict[str, Any]) -> bool:
    slug = _clean_text(detail.get("slug") or summary.get("slug")).casefold()
    title = _clean_text(detail.get("title") or summary.get("title")).casefold()
    city = detail.get("city") or summary.get("city") or {}
    city_name = _clean_text(city.get("name")).casefold()

    if city_name and MADRID_QUERY not in city_name:
        return True
    if " en " in title and " en madrid" not in title:
        return True
    if any(token in slug or token in title for token in BLOCKLIST_TOKENS):
        return True
    if not _has_madrid_evidence(summary, detail):
        return True
    return False


def _extract_record(summary: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any] | None:
    if not detail.get("enabled") or detail.get("cancelation_status") not in (None, 0):
        return None

    slug = _clean_text(detail.get("slug") or summary.get("slug"))
    title = _clean_text(detail.get("title") or summary.get("title"))
    if not slug or not title:
        return None
    if _should_skip_event(summary, detail):
        return None

    venue = detail.get("venue") or summary.get("venue") or {}
    city = detail.get("city") or summary.get("city") or {}
    price, currency = _extract_price(detail)
    venue_name = _clean_text(venue.get("name")) or _clean_text(city.get("name")) or None
    venue_address = _clean_text(venue.get("address")) or _clean_text(city.get("name")) or None
    permalink = _clean_text(detail.get("permalink"))
    purchase_url = _clean_text(detail.get("purchase_url")) or None
    description = _clean_text(detail.get("description")) or title

    return {
        "id": str(detail.get("id") or summary.get("id") or slug),
        "titulo": title,
        "subtitulo": _clean_text(detail.get("subtitle")) or None,
        "descripcion": description,
        "contenido": description,
        "precio": price,
        "moneda": currency,
        "lugar": venue_name,
        "direccion": venue_address,
        "latitud": venue.get("latitude"),
        "longitud": venue.get("longitude"),
        "fecha_inicio": _clean_text(detail.get("start_date")) or None,
        "fecha_fin": _clean_text(detail.get("end_date")) or _clean_text(detail.get("start_date")) or None,
        "fechas_disponibles": _dedupe_strings(
            [
                _clean_text(detail.get("start_date")),
                _clean_text(detail.get("end_date")),
            ]
        ),
        "categorias": _build_categories(detail),
        "etiquetas": _extract_tags(detail),
        "url": permalink or purchase_url,
        "url_articulo": permalink or purchase_url,
        "url_compra": purchase_url,
        "imagen": _extract_image(detail, summary),
        "fecha_publicacion": _clean_text(detail.get("created")) or None,
        "fecha_actualizacion": _clean_text(detail.get("modified")) or None,
        "fuente": SOURCE_NAME,
        "metadata": {
            "slug": slug,
            "wegow_type": detail.get("type"),
            "sold_out": bool(detail.get("sold_out")),
            "closed": bool(detail.get("closed")),
            "show_date": detail.get("show_date"),
            "show_time": detail.get("show_time"),
            "venue_permalink": _clean_text(venue.get("permalink")) or None,
            "city_name": _clean_text(city.get("name")) or None,
            "city_slug": _clean_text(city.get("slug")) or None,
            "opening_hour": _clean_text(detail.get("opening_hour")) or None,
        },
    }


def _drop_shared_purchase_urls(records: list[dict[str, Any]]) -> None:
    counts = Counter(record.get("url_compra") for record in records if record.get("url_compra"))
    for record in records:
        purchase_url = record.get("url_compra")
        if not purchase_url or counts[purchase_url] <= 1:
            continue
        record.setdefault("metadata", {})["shared_purchase_url"] = purchase_url
        record["url_compra"] = None


def scrape_wegow() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    madrid_city = _extract_madrid_city(session)
    city_id = int(madrid_city["id"])
    country = madrid_city.get("country") or {}
    country_id = int(country.get("code") or SPAIN_COUNTRY_ID)

    summaries = _extract_event_summaries(session, city_id=city_id, country_id=country_id)
    log.info("Discovered %d Wegow Madrid summary items", len(summaries))

    records: list[dict[str, Any]] = []
    for index, summary in enumerate(summaries, start=1):
        slug = _clean_text(summary.get("slug"))
        if not slug:
            continue
        try:
            log.info("Fetching Wegow detail %d/%d: %s", index, len(summaries), slug)
            detail = _request_json(session, f"{EVENTS_URL}{slug}/")
        except Exception as error:
            log.warning("Skipping Wegow item %s: %s", slug, error)
            continue

        record = _extract_record(summary, detail)
        if record:
            records.append(record)

    _drop_shared_purchase_urls(records)
    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Saved %d Wegow Madrid events to %s", len(normalized), OUTPUT_FILE)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(normalized),
        sum(1 for item in normalized if item.get("latitud") is not None),
        sum(1 for item in normalized if item.get("precio") is not None),
    )
    return normalized


if __name__ == "__main__":
    scrape_wegow()