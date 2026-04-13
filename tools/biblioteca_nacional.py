"""Biblioteca Nacional de Espana agenda scraper.

Uses the public agenda listing page as discovery source and detail pages for
field-level enrichment. Online-only training pages and generic undated service
pages are filtered out to keep the feed focused on public Madrid activities.

Output: outputs/eventos_biblioteca_nacional.json
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.bne.es"
AGENDA_URL = f"{BASE_URL}/es/agenda"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "outputs"
    / "eventos_biblioteca_nacional.json"
)
SOURCE_NAME = "biblioteca_nacional"
REQUEST_TIMEOUT = 30
VENUE_ADDRESS = "Paseo de Recoletos, 20-22, 28071 Madrid"
PRICE_RE = re.compile(r"(?:€\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*€)")
INTERVAL_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s*-\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
)
DATE_RANGE_RE = re.compile(
    r"Del\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})\s+al\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)
DATE_SINGLE_RE = re.compile(
    r"(?:Lunes|Martes|Miércoles|Miercoles|Jueves|Viernes|Sábado|Sabado|Domingo),?\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})(?:\.\s*(\d{1,2}:\d{2})h\s*-\s*(\d{1,2}:\d{2})h)?",
    re.IGNORECASE,
)
DATE_STARTING_RE = re.compile(
    r"A partir del\s+(?:lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)
SESSION_RE = re.compile(
    r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+):\s*(\d{1,2}:\d{2})\s*h",
    re.IGNORECASE,
)
WEEKLY_SCHEDULE_RE = re.compile(
    r"desde el\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+al\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4}),\s+a las\s+(\d{1,2})\s*h",
    re.IGNORECASE,
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}
SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
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


def _normalize_month(value: str) -> int | None:
    return SPANISH_MONTHS.get(_clean_text(value).casefold())


def _request_html(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _field_strings(node: Tag | None) -> list[str]:
    if not node:
        return []
    label_texts = {
        _clean_text(label.get_text(" ", strip=True))
        for label in node.select(".field__label")
    }
    values: list[str] = []
    for text in node.stripped_strings:
        clean = _clean_text(text)
        if not clean or clean in label_texts:
            continue
        values.append(clean)
    return values


def _field_text(node: Tag | None) -> str | None:
    values = _field_strings(node)
    return " ".join(values) if values else None


def _extract_body_node(soup: BeautifulSoup) -> Tag | None:
    return soup.select_one(".block-field-blocknodeeventobody .field--name-body")


def _extract_body_parts(body_node: Tag | None) -> tuple[str | None, str | None]:
    if not body_node:
        return None, None

    description_parts: list[str] = []
    full_parts: list[str] = []
    reached_sessions = False

    for child in body_node.children:
        if not getattr(child, "name", None):
            continue
        text = _clean_text(child.get_text(" ", strip=True))
        if not text:
            continue
        full_parts.append(text)
        if child.name in {"h2", "h3"} and "próximas sesiones" in text.casefold():
            reached_sessions = True
            continue
        if reached_sessions:
            continue
        if child.name in {"p", "ul", "ol"}:
            description_parts.append(text)

    description = "\n\n".join(description_parts) if description_parts else None
    full_text = "\n\n".join(full_parts) if full_parts else None
    return description, full_text


def _parse_iso_interval(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    match = INTERVAL_RE.search(text)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _date_iso(year: int, month_name: str, day: int) -> str | None:
    month = _normalize_month(month_name)
    if month is None:
        return None
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _parse_card_dates(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None

    match = DATE_RANGE_RE.search(text)
    if match:
        start = _date_iso(int(match.group(3)), match.group(2), int(match.group(1)))
        end = _date_iso(int(match.group(6)), match.group(5), int(match.group(4)))
        return start, end

    match = DATE_SINGLE_RE.search(text)
    if match:
        start = _date_iso(int(match.group(3)), match.group(2), int(match.group(1)))
        if not start:
            return None, None
        start_time = match.group(4)
        end_time = match.group(5)
        if start_time:
            start = f"{start}T{start_time}:00"
        end = start
        if end_time:
            end = f"{start.split('T', 1)[0]}T{end_time}:00"
        return start, end

    match = DATE_STARTING_RE.search(text)
    if match:
        start = _date_iso(int(match.group(3)), match.group(2), int(match.group(1)))
        return start, start

    return None, None


def _parse_body_sessions(body_text: str | None, default_year: int | None) -> list[str]:
    if not body_text or default_year is None:
        return []
    sessions: list[str] = []
    for day_text, month_name, time_text in SESSION_RE.findall(body_text):
        session_date = _date_iso(default_year, month_name, int(day_text))
        if not session_date:
            continue
        sessions.append(f"{session_date}T{time_text}:00")
    return _dedupe_strings(sessions)


def _parse_weekly_schedule(text: str | None) -> list[str]:
    if not text:
        return []
    match = WEEKLY_SCHEDULE_RE.search(text)
    if not match:
        return []

    start_date = _date_iso(int(match.group(5)), match.group(2), int(match.group(1)))
    end_date = _date_iso(int(match.group(5)), match.group(4), int(match.group(3)))
    hour = int(match.group(6))
    if not start_date or not end_date:
        return []

    current = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    sessions: list[str] = []
    while current <= end:
        sessions.append(f"{current.isoformat()}T{hour:02d}:00:00")
        current += timedelta(days=7)
    return sessions


def _extract_price(page_text: str) -> float | None:
    values: list[float] = []
    for match in PRICE_RE.finditer(page_text):
        raw = match.group(1) or match.group(2)
        if not raw:
            continue
        try:
            values.append(float(raw.replace(",", ".")))
        except ValueError:
            continue
    if values:
        return min(values)
    lowered = page_text.casefold()
    if any(token in lowered for token in ("entrada gratuita", "entrada libre", "gratuita", "gratuito")):
        return 0.0
    return None


def _extract_booking_url(soup: BeautifulSoup) -> str | None:
    for selector in (
        ".field--name-field-enlace-formulario-inscripc a[href]",
        ".field--name-field-url a[href]",
    ):
        node = soup.select_one(selector)
        if node and node.get("href"):
            return _clean_text(node.get("href"))

    email_node = soup.select_one(".field--name-field-email-texto")
    email_text = _field_text(email_node)
    if email_text and "@" in email_text:
        return f"mailto:{email_text}"
    return None


def _extract_image(soup: BeautifulSoup) -> str | None:
    image_node = soup.select_one(".field--name-field-media-image img, .field--name-field-imagen-cabecera img")
    if not image_node:
        return None
    candidate = image_node.get("src") or image_node.get("data-src")
    return urljoin(BASE_URL, candidate) if candidate else None


def _extract_detail_record(session: requests.Session, item: dict[str, Any]) -> dict[str, Any] | None:
    url = item["url"]
    soup = _request_html(session, url)
    title = _clean_text((soup.select_one("h1") or soup).get_text(" ", strip=True))
    if not title:
        return None

    modal_text = _field_text(soup.select_one(".field--name-field-modalidad"))
    if modal_text and "digital" in modal_text.casefold():
        return None

    body_node = _extract_body_node(soup)
    description_text, full_body_text = _extract_body_parts(body_node)
    type_values = _field_strings(soup.select_one(".field--name-field-tipo"))
    cycle = _field_text(soup.select_one(".field--name-field-ciclo-campana"))
    place = _field_text(soup.select_one(".field--name-field-lugar"))
    schedule_text = _field_text(
        soup.select_one(".field--name-field-horarios-especificos, .field--name-field-horarios")
    )
    info_text = _field_text(soup.select_one(".field--name-field-informacion-adicional"))
    duration_text = _field_text(soup.select_one(".field--name-field-duracion"))
    interval_text = _field_text(soup.select_one(".field--name-field-intervalo-add-to-cal"))
    interval_start, interval_end = _parse_iso_interval(interval_text)
    fallback_start, fallback_end = _parse_card_dates(item.get("card_text"))

    start_value = interval_start or fallback_start
    end_value = interval_end or fallback_end or start_value
    default_year = None
    for value in (start_value, end_value):
        if not value:
            continue
        default_year = int(value[:4])
        break

    sessions = _parse_body_sessions(full_body_text, default_year)
    if not sessions:
        sessions = _parse_weekly_schedule(schedule_text)

    if not start_value and sessions:
        start_value = sessions[0]
    if not end_value and sessions:
        end_value = sessions[-1]

    if not start_value and not end_value:
        return None

    available_dates = list(sessions)
    if not available_dates and start_value:
        start_day = start_value.split("T", 1)[0]
        end_day = end_value.split("T", 1)[0] if end_value else start_day
        available_dates.append(start_value)
        if end_value and end_day != start_day:
            available_dates.append(end_value)

    page_text = "\n".join(
        part for part in (full_body_text, info_text, schedule_text, duration_text, modal_text) if part
    )
    price = _extract_price(page_text)
    if price is None and (place or cycle or item.get("card_text")):
        price = 0.0

    tags = _dedupe_strings([cycle, modal_text, duration_text])
    booking_url = _extract_booking_url(soup)
    metadata: dict[str, Any] = {"card_text": item.get("card_text")}
    if modal_text:
        metadata["modalidad"] = modal_text
    if duration_text:
        metadata["duracion"] = duration_text
    if schedule_text:
        metadata["horario"] = schedule_text

    return {
        "id": url.rstrip("/").split("/")[-1],
        "titulo": title,
        "descripcion": description_text or info_text or schedule_text,
        "contenido": "\n\n".join(part for part in (description_text, info_text, schedule_text) if part) or None,
        "precio": price,
        "moneda": "EUR",
        "lugar": place,
        "direccion": VENUE_ADDRESS if place else None,
        "fecha_inicio": start_value,
        "fecha_fin": end_value,
        "fechas_disponibles": available_dates,
        "categorias": type_values,
        "etiquetas": tags,
        "url": url,
        "url_compra": booking_url,
        "imagen": _extract_image(soup),
        "metadata": metadata,
    }


def _extract_discovery_rows(session: requests.Session) -> list[dict[str, Any]]:
    soup = _request_html(session, AGENDA_URL)
    records: list[dict[str, Any]] = []

    for row in soup.select(".ps-speaker-row.views-row"):
        link = row.select_one('a[href*="/es/agenda/"]')
        if not link or not link.get("href"):
            continue
        card_text = _clean_text(row.get_text(" ", strip=True))
        if any(token in card_text.casefold() for token in ("consulta los horarios", "exposición permanente")):
            continue
        records.append(
            {
                "url": urljoin(BASE_URL, link.get("href")),
                "card_text": card_text,
            }
        )

    unique_by_url = {record["url"]: record for record in records}
    return list(unique_by_url.values())


def scrape_biblioteca_nacional() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)
    discovered = _extract_discovery_rows(session)
    log.info("Found %d Biblioteca Nacional agenda candidates", len(discovered))

    records: list[dict[str, Any]] = []
    for index, item in enumerate(discovered, start=1):
        try:
            log.info(
                "Fetching Biblioteca Nacional detail %d/%d: %s",
                index,
                len(discovered),
                item["url"],
            )
            record = _extract_detail_record(session, item)
        except Exception as error:
            log.warning("Skipping Biblioteca Nacional item %s: %s", item["url"], error)
            continue
        if record:
            records.append(record)

    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d Biblioteca Nacional events to %s", len(normalized), OUTPUT_FILE)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(normalized),
        sum(1 for item in normalized if item.get("latitud") is not None),
        sum(1 for item in normalized if item.get("precio") is not None),
    )
    return normalized


if __name__ == "__main__":
    scrape_biblioteca_nacional()