"""Espacio Fundacion Telefonica events scraper.

Uses the public WordPress REST collection for `tribe_events` as discovery source
and enriches each item from its public detail page, which exposes Event JSON-LD
and per-session reservation rows.

Output: outputs/eventos_espacio_fundacion_telefonica.json
"""

from __future__ import annotations

import html
import json
import logging
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://espacio.fundaciontelefonica.com"
REST_EVENTS_URL = f"{BASE_URL}/wp-json/wp/v2/tribe_events?per_page=100&_embed=1"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "outputs"
    / "eventos_espacio_fundacion_telefonica.json"
)
SOURCE_NAME = "espacio_fundacion_telefonica"
REQUEST_TIMEOUT = 30
VENUE_NAME = "Espacio Fundacion Telefonica"
VENUE_ADDRESS = "C/ Fuencarral, 3, 28004 Madrid"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}
PRICE_RE = re.compile(r"(?:€\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*€)")
TIME_RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2})\s*-\s*(?P<end>\d{1,2}:\d{2})"
)
ONLINE_ATTENDANCE_SUFFIX = "onlineeventattendancemode"
CATEGORY_LABEL_MAP = {
    "actividades": "Actividades",
    "exposicion": "Exposicion",
    "jovenes": "Jovenes",
    "ninos": "Familia",
    "ninas": "Familia",
    "seniors": "Seniors",
    "taller": "Talleres",
    "talleres": "Talleres",
}
MONTH_MAP = {
    "ene": 1,
    "enero": 1,
    "jan": 1,
    "january": 1,
    "feb": 2,
    "febrero": 2,
    "february": 2,
    "mar": 3,
    "marzo": 3,
    "march": 3,
    "abr": 4,
    "abril": 4,
    "apr": 4,
    "april": 4,
    "may": 5,
    "mayo": 5,
    "jun": 6,
    "junio": 6,
    "june": 6,
    "jul": 7,
    "julio": 7,
    "july": 7,
    "ago": 8,
    "agosto": 8,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "set": 9,
    "septiembre": 9,
    "setiembre": 9,
    "september": 9,
    "oct": 10,
    "octubre": 10,
    "october": 10,
    "nov": 11,
    "noviembre": 11,
    "november": 11,
    "dic": 12,
    "diciembre": 12,
    "dec": 12,
    "december": 12,
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


def _strip_html_fragment(value: Any) -> str:
    text = html.unescape(str(value or ""))
    return _clean_text(BeautifulSoup(text, "html.parser").get_text(" ", strip=True))


def _canonicalize_category(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return CATEGORY_LABEL_MAP.get(_normalize_text(text), text)


def _request_json(session: requests.Session, url: str) -> Any:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _request_html(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _extract_embedded_terms(item: dict[str, Any], taxonomy: str) -> list[str]:
    values: list[str] = []
    for group in item.get("_embedded", {}).get("wp:term", []):
        if not isinstance(group, list):
            continue
        for term in group:
            if not isinstance(term, dict):
                continue
            if term.get("taxonomy") != taxonomy:
                continue
            values.append(term.get("name"))
    return _dedupe_strings(values)


def _extract_featured_image(item: dict[str, Any]) -> str | None:
    media_items = item.get("_embedded", {}).get("wp:featuredmedia", [])
    if not media_items:
        return None
    media = media_items[0]
    if not isinstance(media, dict):
        return None
    return _clean_text(media.get("source_url")) or None


def _is_event_type(value: Any) -> bool:
    if isinstance(value, str):
        return value == "Event"
    if isinstance(value, list):
        return "Event" in value
    return False


def _extract_event_json_ld(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("@graph", [payload])
        else:
            items = []

        for item in items:
            if isinstance(item, dict) and _is_event_type(item.get("@type")):
                return item
    return {}


def _build_date_label(node: Tag | None) -> str:
    if not node:
        return ""
    day = _clean_text(node.select_one(".dia").get_text(" ", strip=True)) if node.select_one(".dia") else ""
    month_parts = [
        _clean_text(month_node.get_text(" ", strip=True))
        for month_node in node.select(".mes")
    ]
    return _clean_text(" ".join([day, *month_parts]))


def _parse_date_label(text: Any) -> str | None:
    parts = _clean_text(text).replace(".", " ").split()
    if len(parts) < 3:
        return None

    try:
        day = int(parts[0])
        year = int(parts[-1])
    except ValueError:
        return None

    month_token = _normalize_text(" ".join(parts[1:-1])) or _normalize_text(parts[1])
    month = MONTH_MAP.get(month_token)
    if month is None:
        month = MONTH_MAP.get(_normalize_text(parts[1]))
    if month is None:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _normalize_time_token(value: str | None) -> str | None:
    if not value:
        return None
    try:
        hour_text, minute_text = value.split(":", 1)
        return f"{int(hour_text):02d}:{int(minute_text):02d}"
    except ValueError:
        return None


def _parse_time_range(text: Any) -> tuple[str | None, str | None]:
    match = TIME_RANGE_RE.search(_clean_text(text))
    if not match:
        return None, None
    return (
        _normalize_time_token(match.group("start")),
        _normalize_time_token(match.group("end")),
    )


def _combine_date_and_time(date_iso: str | None, time_text: str | None) -> str | None:
    if not date_iso:
        return None
    if not time_text:
        return date_iso
    return f"{date_iso}T{time_text}:00"


def _extract_session_rows(soup: BeautifulSoup) -> tuple[list[dict[str, Any]], str | None]:
    sessions: list[dict[str, Any]] = []
    booking_url: str | None = None

    for row in soup.select("div.linea_reserva"):
        date_iso = _parse_date_label(_build_date_label(row.select_one(".fecha")))
        if not date_iso:
            continue

        time_text = _clean_text(
            (row.select_one(".horas") or row.select_one(".horario"))
            .get_text(" ", strip=True)
            if (row.select_one(".horas") or row.select_one(".horario"))
            else ""
        )
        start_time, end_time = _parse_time_range(time_text)
        reserve_node = row.select_one("a.reservabtn[href]")
        reserve_href = _clean_text(reserve_node.get("href")) if reserve_node else None
        row_blob = _normalize_text(row.get_text(" ", strip=True))
        status = None
        if "caducado" in row_blob:
            status = "caducado"
        elif reserve_href:
            status = "reserva"

        sessions.append(
            {
                "fecha": date_iso,
                "inicio": _combine_date_and_time(date_iso, start_time),
                "fin": _combine_date_and_time(date_iso, end_time),
                "estado": status,
            }
        )

        if reserve_href and not booking_url:
            booking_url = reserve_href

    return sessions, booking_url


def _extract_calendar_range(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    date_values = [
        _parse_date_label(_build_date_label(node))
        for node in soup.select("div.calendario > div.fecha")
    ]
    parsed = [value for value in date_values if value]
    if not parsed:
        return None, None
    return parsed[0], parsed[-1]


def _extract_booking_url(soup: BeautifulSoup, session_booking_url: str | None) -> str | None:
    if session_booking_url:
        return session_booking_url
    for anchor in soup.select("a.reservabtn[href], a[href]"):
        href = _clean_text(anchor.get("href"))
        if not href or "google.com/calendar" in href.casefold():
            continue
        text = _normalize_text(anchor.get_text(" ", strip=True))
        if any(token in text for token in ("reserva", "entrada", "inscrip")):
            return href
    return None


def _extract_detail_content(soup: BeautifulSoup) -> str | None:
    paragraphs: list[str] = []
    seen: set[str] = set()
    for node in soup.select("div.exposingle p, div.textoexposingle p"):
        text = _clean_text(node.get_text(" ", strip=True))
        if not text or len(text) < 30 or text.startswith("http"):
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        paragraphs.append(text)
    return "\n\n".join(paragraphs) if paragraphs else None


def _extract_price(detail_text: str) -> float | None:
    values: list[float] = []
    for match in PRICE_RE.finditer(detail_text):
        raw_value = match.group(1) or match.group(2)
        if not raw_value:
            continue
        try:
            values.append(float(raw_value.replace(",", ".")))
        except ValueError:
            continue
    return min(values) if values else None


def _extract_title(item: dict[str, Any], event_payload: dict[str, Any]) -> str:
    return (
        _strip_html_fragment(event_payload.get("name"))
        or _strip_html_fragment(item.get("title", {}).get("rendered"))
        or _clean_text(item.get("slug"))
    )


def _extract_description(item: dict[str, Any], event_payload: dict[str, Any]) -> str | None:
    return (
        _strip_html_fragment(event_payload.get("description"))
        or _strip_html_fragment(item.get("excerpt", {}).get("rendered"))
        or None
    )


def _extract_image(item: dict[str, Any], event_payload: dict[str, Any]) -> str | None:
    image = event_payload.get("image")
    if isinstance(image, list) and image:
        return _clean_text(image[0]) or _extract_featured_image(item)
    if isinstance(image, str):
        return _clean_text(image) or _extract_featured_image(item)
    return _extract_featured_image(item)


def _is_online_only(event_payload: dict[str, Any]) -> bool:
    mode = _normalize_text(event_payload.get("eventAttendanceMode"))
    return mode.endswith(ONLINE_ATTENDANCE_SUFFIX)


def _build_record(session: requests.Session, item: dict[str, Any]) -> dict[str, Any] | None:
    url = _clean_text(item.get("link"))
    if not url:
        return None

    soup = _request_html(session, url)
    event_payload = _extract_event_json_ld(soup)
    if _is_online_only(event_payload):
        return None

    detail_text = _clean_text(soup.get_text(" ", strip=True))
    categories = [
        _canonicalize_category(value)
        for value in _extract_embedded_terms(item, "tribe_events_cat")
    ]
    categories = [value for value in categories if value]
    tags = _extract_embedded_terms(item, "post_tag")
    sessions, session_booking_url = _extract_session_rows(soup)
    calendar_start, calendar_end = _extract_calendar_range(soup)

    if sessions:
        start_value = sessions[0]["inicio"] or sessions[0]["fecha"]
        end_value = sessions[-1]["fin"] or sessions[-1]["inicio"] or sessions[-1]["fecha"]
        available_dates = [session["inicio"] or session["fecha"] for session in sessions]
    else:
        start_value = calendar_start or _clean_text(event_payload.get("startDate")) or None
        end_value = calendar_end or _clean_text(event_payload.get("endDate")) or start_value
        available_dates = []

    price = _extract_price(detail_text)
    if price is None:
        price = 0.0

    description = _extract_description(item, event_payload)
    content = _extract_detail_content(soup) or description
    booking_url = _extract_booking_url(soup, session_booking_url)

    return {
        "id": _clean_text(item.get("slug")) or url.rstrip("/").split("/")[-1],
        "titulo": _extract_title(item, event_payload),
        "descripcion": description,
        "contenido": content,
        "precio": price,
        "moneda": "EUR",
        "lugar": VENUE_NAME,
        "direccion": VENUE_ADDRESS,
        "fecha_inicio": start_value,
        "fecha_fin": end_value,
        "fechas_disponibles": available_dates,
        "categorias": categories,
        "etiquetas": tags,
        "url": url,
        "url_compra": booking_url,
        "imagen": _extract_image(item, event_payload),
        "fecha_publicacion": item.get("date"),
        "fecha_actualizacion": item.get("modified"),
        "metadata": {
            "rest_id": item.get("id"),
            "event_attendance_mode": _clean_text(event_payload.get("eventAttendanceMode")) or None,
            "event_status": _clean_text(event_payload.get("eventStatus")) or None,
            "precio_inferido_desde_politica_venue": price == 0.0,
            "sesiones_fuente": sessions,
        },
    }


def _drop_shared_booking_urls(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    url_counts = Counter(
        record.get("url_compra") for record in records if record.get("url_compra")
    )
    for record in records:
        booking_url = record.get("url_compra")
        if not booking_url or url_counts[booking_url] <= 1:
            continue
        record.setdefault("metadata", {})["shared_booking_url"] = booking_url
        record["url_compra"] = None
    return records


def scrape_espacio_fundacion_telefonica() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)
    discovered = _request_json(session, REST_EVENTS_URL)
    log.info("Found %d Espacio Fundacion Telefonica items in REST discovery", len(discovered))

    records: list[dict[str, Any]] = []
    for index, item in enumerate(discovered, start=1):
        try:
            log.info(
                "Fetching Espacio Fundacion Telefonica detail %d/%d: %s",
                index,
                len(discovered),
                item.get("link"),
            )
            record = _build_record(session, item)
        except Exception as error:
            log.warning("Skipping Telefonica item %s: %s", item.get("link"), error)
            continue
        if record:
            records.append(record)

    records = _drop_shared_booking_urls(records)
    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info(
        "Saved %d Espacio Fundacion Telefonica events to %s",
        len(normalized),
        OUTPUT_FILE,
    )
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(normalized),
        sum(1 for item in normalized if item.get("latitud") is not None),
        sum(1 for item in normalized if item.get("precio") is not None),
    )
    return normalized


if __name__ == "__main__":
    scrape_espacio_fundacion_telefonica()