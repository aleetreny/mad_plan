"""Teatros del Canal events scraper.

Uses The Events Calendar REST API for current/upcoming listings and enriches
each event with its detail page content.

Output: outputs/eventos_teatros_canal.json
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.teatroscanal.com"
API_URL = f"{BASE_URL}/wp-json/tribe/events/v1/events"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "outputs" / "eventos_teatros_canal.json"
)
REQUEST_TIMEOUT = 30
PER_PAGE = 50
UPCOMING_WINDOW_DAYS = 180
MADRID_TZ = ZoneInfo("Europe/Madrid")
TEATROS_ADDRESS = "Calle de Cea Bermúdez, 1, Madrid"
SOURCE_NAME = "teatros_canal"
IGNORED_CATEGORIES = {
    "abono",
    "en cartel",
    "carne joven",
    "carné joven",
    "temporada 25 – 26",
    "temporada 25-26",
}
DETAIL_SPLIT_MARKERS = (
    "ABONO Temporada",
    "Descuentos (según zona elegida)",
    "Descuentos :",
    "Información útil",
    "Información práctica",
    "Precios y Descuentos",
    "Precio localidades",
    "¡Compra ya tus entradas!",
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


def _request_json(
    session: requests.Session, url: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _request_html(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _parse_explicit_price(raw: str | None) -> tuple[float | None, str | None]:
    text = _clean_text(raw).lower()
    if not text:
        return None, None
    if ("entrada gratuita" in text or "gratis" in text or "gratuito" in text or "gratuita" in text) and "acompanante" not in text and "acompañante" not in text:
        return 0.0, "EUR"

    match = re.search(r"desde\s*(\d+(?:[.,]\d+)?)\s*€", text, flags=re.IGNORECASE)
    if match:
        return float(match.group(1).replace(",", ".")), "EUR"

    match = re.search(r"localidades\s+sin\s+numerar\s*(\d+(?:[.,]\d+)?)\s*€", text, flags=re.IGNORECASE)
    if match:
        return float(match.group(1).replace(",", ".")), "EUR"

    section_match = re.search(
        r"precio\s+localidades(?:\s+individuales)?\s*:\s*(.+?)(?:descuentos|canje|carn[eé]|asociaciones|comprar|$)",
        text,
        flags=re.IGNORECASE,
    )
    if section_match:
        values: list[float] = []
        for match in re.findall(r"\d+(?:[.,]\d+)?(?=\s*€)", section_match.group(1)):
            try:
                values.append(float(match.replace(",", ".")))
            except ValueError:
                continue
        if values:
            return min(values), "EUR"

    return None, None


def _strip_tab_prefix(text: str) -> str:
    cleaned = _clean_text(text)
    cleaned = re.sub(
        r"^(?:Información|Ficha Artística|Ficha Artistica|Ofertas)(?:\s+(?:Información|Ficha Artística|Ficha Artistica|Ofertas))*\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def _trim_detail_text(text: str) -> str:
    cleaned = _strip_tab_prefix(text)
    split_positions = [cleaned.find(marker) for marker in DETAIL_SPLIT_MARKERS if marker in cleaned]
    if split_positions:
        cleaned = cleaned[: min(split_positions)]
    return cleaned.strip()


def _extract_place(raw: str | None) -> str | None:
    text = _clean_text(raw)
    if not text:
        return None
    text = re.split(r"Duraci[oó]n\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return text.strip(" .") or None


def _extract_duration(raw: str | None) -> str | None:
    text = _clean_text(raw)
    if not text:
        return None
    match = re.search(r"Duraci[oó]n\s*:\s*([^\.]+)", text, flags=re.IGNORECASE)
    return _clean_text(match.group(1)) if match else None


def _extract_categories(event: dict[str, Any]) -> list[str]:
    categories = [item.get("name") for item in (event.get("categories") or [])]
    tags = [item.get("name") for item in (event.get("tags") or [])]
    filtered = [
        value
        for value in categories + tags
        if _clean_text(value).casefold() not in IGNORED_CATEGORIES
    ]
    deduped = _dedupe_strings(filtered)
    if deduped:
        return deduped
    fallback = _dedupe_strings(categories + tags)
    return fallback or ["Teatro"]


def _format_event_value(value: str | None) -> str | None:
    if not value:
        return None
    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
        return parsed.date().isoformat()
    if parsed.hour == 23 and parsed.minute == 59 and parsed.second == 59:
        return parsed.date().isoformat()
    return parsed.replace(tzinfo=MADRID_TZ).isoformat()


def _extract_available_dates(start_value: str | None, end_value: str | None) -> list[str]:
    values = [_format_event_value(start_value), _format_event_value(end_value)]
    return _dedupe_strings([value for value in values if value])


def _extract_buy_url(soup: BeautifulSoup, event_url: str) -> str:
    container = soup.select_one(".destacado-left")
    if container:
        for anchor in container.select("a[href]"):
            href = urljoin(event_url, anchor.get("href", ""))
            parsed = urlparse(href)
            path = parsed.path.casefold()
            if href == event_url:
                continue
            if any(marker in path for marker in ("/entradas/", "ticket", "compra", "comprar")):
                return href
    return event_url


def _extract_detail_fields(
    session: requests.Session, event_url: str
) -> dict[str, Any]:
    soup = _request_html(session, event_url)

    summary_node = soup.select_one(".summary-show")
    summary_raw_text = _clean_text(summary_node.get_text(" ", strip=True)) if summary_node else ""
    summary_text = _trim_detail_text(summary_raw_text)
    info_text = _clean_text((soup.select_one(".destacado-left") or "").get_text(" ", strip=True))
    sala_text = _clean_text((soup.select_one(".sala-show") or "").get_text(" ", strip=True))

    price, currency = _parse_explicit_price(f"{info_text} {summary_raw_text}")

    return {
        "descripcion": summary_text or None,
        "price_text": info_text or None,
        "precio": price,
        "moneda": currency,
        "lugar": _extract_place(sala_text) or "Teatros del Canal",
        "duracion": _extract_duration(sala_text) or _extract_duration(summary_text),
        "url_compra": _extract_buy_url(soup, event_url),
    }


def _fetch_all_events(session: requests.Session) -> list[dict[str, Any]]:
    window_start = datetime.now(MADRID_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(days=UPCOMING_WINDOW_DAYS)
    page = 1
    total_pages = 1
    events: list[dict[str, Any]] = []

    log.info(
        "Teatros del Canal window: start_date >= %s and end_date <= %s",
        window_start.strftime("%Y-%m-%d %H:%M:%S"),
        window_end.strftime("%Y-%m-%d %H:%M:%S"),
    )

    while page <= total_pages:
        payload = _request_json(
            session,
            API_URL,
            params={
                "per_page": PER_PAGE,
                "page": page,
                "status": "publish",
                "start_date": window_start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": window_end.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        page_events = payload.get("events") or []
        total_pages = int(payload.get("total_pages") or 1)
        events.extend(page_events)
        log.info("Fetched Teatros del Canal page %d/%d: %d events", page, total_pages, len(page_events))
        page += 1

    return events


def scrape_teatros_canal() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    log.info("Fetching Teatros del Canal events via The Events Calendar API …")
    raw_events = _fetch_all_events(session)
    log.info("Raw Teatros del Canal events: %d", len(raw_events))

    records: list[dict[str, Any]] = []
    for event in raw_events:
        event_url = _clean_text(event.get("url"))
        detail = _extract_detail_fields(session, event_url) if event_url else {}
        image = event.get("image") or {}
        categories = _extract_categories(event)

        description = detail.get("descripcion") or _clean_text(event.get("excerpt")) or _clean_text(event.get("title"))

        metadata = {
            "all_day": event.get("all_day"),
            "duration": detail.get("duracion"),
            "price_text": detail.get("price_text"),
            "api_categories": [item.get("name") for item in (event.get("categories") or [])],
            "api_tags": [item.get("name") for item in (event.get("tags") or [])],
        }

        records.append(
            {
                "id": str(event.get("id") or ""),
                "titulo": _clean_text(event.get("title")),
                "subtitulo": None,
                "descripcion": description,
                "contenido": description,
                "precio": detail.get("precio"),
                "moneda": detail.get("moneda"),
                "lugar": detail.get("lugar") or "Teatros del Canal",
                "direccion": TEATROS_ADDRESS,
                "latitud": None,
                "longitud": None,
                "fecha_inicio": _format_event_value(event.get("start_date")),
                "fecha_fin": _format_event_value(event.get("end_date")),
                "fechas_disponibles": _extract_available_dates(event.get("start_date"), event.get("end_date")),
                "categorias": categories,
                "url": event_url or None,
                "url_articulo": event_url or None,
                "url_compra": detail.get("url_compra") if event_url else None,
                "imagen": _clean_text(image.get("url")) or None,
                "fecha_publicacion": _clean_text(event.get("date_utc") or event.get("date")) or None,
                "fecha_actualizacion": _clean_text(event.get("modified_utc") or event.get("modified")) or None,
                "fuente": SOURCE_NAME,
                "metadata": metadata,
            }
        )

    records = normalize_plan_records(records, source=SOURCE_NAME)

    OUTPUT_FILE.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Saved %d Teatros del Canal events to %s", len(records), OUTPUT_FILE)
    return records


if __name__ == "__main__":
    results = scrape_teatros_canal()
    with_price = sum(1 for event in results if event.get("precio") is not None)
    with_coords = sum(1 for event in results if event.get("latitud") is not None)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(results),
        with_coords,
        with_price,
    )