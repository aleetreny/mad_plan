"""Sala El Sol events scraper.

Uses the public agenda page for discovery and each event detail page for
schedule, pricing, description, and ticketing enrichment.

Output: outputs/eventos_sala_el_sol.json
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://salaelsol.com"
AGENDA_URL = f"{BASE_URL}/agenda/"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "outputs" / "eventos_sala_el_sol.json"
)
SOURCE_NAME = "sala_el_sol"
REQUEST_TIMEOUT = 30
VENUE_NAME = "Sala El Sol"
VENUE_ADDRESS = "Calle de los Jardines 3, 28013 Madrid"
VENUE_LAT = 40.419056529364845
VENUE_LON = -3.703834384604002
DATE_RE = re.compile(
    r"(?:lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+(\d{1,2})\s+([a-záéíóú]+)",
    flags=re.IGNORECASE,
)
TIME_RE = re.compile(r"(\d{1,2})[:.](\d{2})")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}
MONTHS = {
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
CATEGORY_MAP = {
    "conciertos": ["Conciertos", "Musica"],
    "clubbing": ["Clubbing", "Musica", "Noche"],
}
FAMILY_TOKENS = {
    "acompañados de niños",
    "acompanados de ninos",
    "anticipada infantil",
    "entrada infantil",
    "edad recomendada",
    "familiar",
    "familiares",
    "infantil",
    "toda la familia",
    "peques",
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


def _request_html(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _extract_image(node: Tag | BeautifulSoup | None) -> str | None:
    if not node:
        return None
    for image in node.select("img"):
        for attr in ("data-lazy-src", "src"):
            candidate = _clean_text(image.get(attr))
            if not candidate or candidate.startswith("data:image"):
                continue
            return urljoin(BASE_URL, candidate)
    return None


def _parse_day_month(value: str | None) -> tuple[int, int] | None:
    match = DATE_RE.search(_clean_text(value).casefold())
    if not match:
        return None
    day = int(match.group(1))
    month = MONTHS.get(match.group(2))
    if not month:
        return None
    return day, month


def _infer_event_days(cards: list[dict[str, Any]], *, today: date) -> None:
    current_year = today.year
    previous_day: date | None = None

    for card in cards:
        day_month = _parse_day_month(card.get("date_text"))
        if not day_month:
            continue

        day, month = day_month
        candidate = date(current_year, month, day)
        if previous_day is None:
            while candidate < today - timedelta(days=30):
                current_year += 1
                candidate = date(current_year, month, day)
        else:
            while candidate < previous_day:
                current_year += 1
                candidate = date(current_year, month, day)

        card["start_day"] = candidate
        previous_day = candidate


def _normalize_time_text(value: str) -> str:
    match = TIME_RE.search(value)
    if not match:
        return ""
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _parse_time_range(value: str | None) -> tuple[str | None, str | None]:
    matches = TIME_RE.findall(_clean_text(value))
    if not matches:
        return None, None

    start = f"{int(matches[0][0]):02d}:{matches[0][1]}"
    end = None
    if len(matches) > 1:
        end = f"{int(matches[1][0]):02d}:{matches[1][1]}"
    return start, end


def _combine_day_time(target_day: date, time_text: str | None) -> str | None:
    if not time_text:
        return None
    return f"{target_day.isoformat()}T{time_text}:00"


def _first_anchor_by_text(node: Tag, text: str) -> str | None:
    for anchor in node.select("a[href]"):
        if _clean_text(anchor.get_text(" ", strip=True)).casefold() == text.casefold():
            return _clean_text(anchor.get("href")) or None
    return None


def _extract_listing_cards(session: requests.Session) -> list[dict[str, Any]]:
    soup = _request_html(session, AGENDA_URL)
    cards: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for container in soup.select("div.eventos > div.agenda.gran-contenedor-agenda"):
        title_node = container.select_one("p.nombre_evento a[href*='/eventos/']")
        if not title_node or not title_node.get("href"):
            continue

        url = urljoin(BASE_URL, title_node.get("href"))
        if url in seen_urls:
            continue

        title = _clean_text(title_node.get_text(" ", strip=True))
        if not title:
            continue

        date_node = container.select_one("p.fecha-superior-publico") or container.select_one(
            "p.fecha-superior"
        )
        category_node = container.select_one("strong[class*='categoria']")
        description_node = container.select_one("div.descripcion_evento")
        time_node = container.select_one("span.espacio")
        ticket_url = _first_anchor_by_text(container, "Tickets")

        cards.append(
            {
                "id": urlparse(url).path.rstrip("/").split("/")[-1],
                "titulo": title,
                "url": url,
                "date_text": _clean_text(date_node.get_text(" ", strip=True)) if date_node else None,
                "category": _clean_text(category_node.get_text(" ", strip=True)) if category_node else None,
                "time_text": _clean_text(time_node.get_text(" ", strip=True)) if time_node else None,
                "descripcion_hint": _clean_text(description_node.get_text(" ", strip=True))
                if description_node
                else None,
                "imagen_hint": _extract_image(container),
                "url_compra_hint": ticket_url,
            }
        )
        seen_urls.add(url)

    _infer_event_days(cards, today=date.today())
    return cards


def _slice_between(text: str, start_marker: str, end_marker: str | None) -> str | None:
    start_index = text.find(start_marker)
    if start_index == -1:
        return None
    start_index += len(start_marker)
    if end_marker is None:
        return _clean_text(text[start_index:]) or None
    end_index = text.find(end_marker, start_index)
    if end_index == -1:
        return _clean_text(text[start_index:]) or None
    return _clean_text(text[start_index:end_index]) or None


def _parse_meta_fields(meta_text: str | None) -> dict[str, str | None]:
    text = _clean_text(meta_text)
    return {
        "fecha": _slice_between(text, "Fecha:", "Hora:"),
        "hora": _slice_between(text, "Hora:", "Entradas anticipadas:"),
        "anticipada": _slice_between(text, "Entradas anticipadas:", "Entradas taquilla:"),
        "taquilla": _slice_between(text, "Entradas taquilla:", "Tipo:"),
        "tipo": _slice_between(text, "Tipo:", None),
    }


def _parse_price(*values: str | None) -> tuple[float | None, str | None]:
    numeric_values: list[float] = []
    free = False

    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        lowered = text.casefold()
        if any(token in lowered for token in ("gratis", "gratuita", "gratuito", "entrada gratuita")):
            free = True
        for raw in re.findall(r"\d+(?:[.,]\d+)?(?=\s*€)", text):
            try:
                numeric_values.append(float(raw.replace(",", ".")))
            except ValueError:
                continue

    if numeric_values:
        return min(numeric_values), "EUR"
    if free:
        return 0.0, "EUR"
    return None, None


def _collapse_paragraphs(values: list[str]) -> list[str]:
    collapsed: list[str] = []
    for value in values:
        text = _clean_text(value)
        if not text:
            continue

        lowered = text.casefold()
        skip = False
        for index, existing in enumerate(collapsed):
            existing_lowered = existing.casefold()
            if lowered in existing_lowered:
                skip = True
                break
            if existing_lowered in lowered and len(text) > len(existing):
                collapsed[index] = text
                skip = True
                break
        if not skip:
            collapsed.append(text)
    return collapsed


def _build_categories(category: str | None, description: str) -> list[str]:
    normalized_category = _clean_text(category)
    categories = list(CATEGORY_MAP.get(normalized_category.casefold(), [normalized_category] if normalized_category else ["Musica"]))
    blob = _clean_text(description).casefold()
    if any(token in blob for token in FAMILY_TOKENS) and "Familia" not in categories:
        categories.append("Familia")
    return _dedupe_strings(categories)


def _extract_main_node(soup: BeautifulSoup) -> Tag | None:
    return soup.find("main", class_=lambda value: value and "event" in value.split()) or soup.find("main")


def _extract_detail_record(session: requests.Session, card: dict[str, Any]) -> dict[str, Any] | None:
    soup = _request_html(session, card["url"])
    main = _extract_main_node(soup)
    if not main:
        return None

    title_node = main.find("h1")
    title = _clean_text(title_node.get_text(" ", strip=True)) if title_node else card["titulo"]
    paragraphs = [
        _clean_text(node.get_text(" ", strip=True))
        for node in main.find_all("p")
    ]
    meta_text = next((text for text in paragraphs if text.startswith("Fecha:")), None)
    meta_fields = _parse_meta_fields(meta_text)
    narrative = _collapse_paragraphs(
        [text for text in paragraphs if text and not text.startswith("Fecha:")]
    )
    description = narrative[0] if narrative else (card.get("descripcion_hint") or title)
    content = "\n\n".join(narrative) if narrative else description

    start_day = card.get("start_day")
    if not isinstance(start_day, date):
        return None

    time_text = meta_fields.get("hora") or card.get("time_text")
    start_time, end_time = _parse_time_range(time_text)
    start_value: str | None = start_day.isoformat()
    end_value: str | None = start_day.isoformat()
    available_dates: list[str] = [start_day.isoformat()]

    if start_time:
        start_value = _combine_day_time(start_day, start_time)
        available_dates = [start_value]
        end_day = start_day
        if end_time and end_time <= start_time:
            end_day = start_day + timedelta(days=1)
        if end_time:
            end_value = _combine_day_time(end_day, end_time)
            if end_value and end_value != start_value:
                available_dates.append(end_value)
        else:
            end_value = start_value

    ticket_url = _first_anchor_by_text(main, "Tickets") or card.get("url_compra_hint")
    image = _extract_image(main) or card.get("imagen_hint")
    price, currency = _parse_price(meta_fields.get("anticipada"), meta_fields.get("taquilla"))
    category = meta_fields.get("tipo") or card.get("category")

    return {
        "id": card["id"],
        "titulo": title,
        "subtitulo": None,
        "descripcion": description,
        "contenido": content,
        "precio": price,
        "moneda": currency,
        "lugar": VENUE_NAME,
        "direccion": VENUE_ADDRESS,
        "latitud": VENUE_LAT,
        "longitud": VENUE_LON,
        "fecha_inicio": start_value,
        "fecha_fin": end_value,
        "fechas_disponibles": available_dates,
        "categorias": _build_categories(category, content),
        "etiquetas": [VENUE_NAME],
        "url": card["url"],
        "url_articulo": card["url"],
        "url_compra": ticket_url,
        "imagen": image,
        "fecha_publicacion": None,
        "fecha_actualizacion": None,
        "fuente": SOURCE_NAME,
        "metadata": {
            "agenda_date_text": card.get("date_text"),
            "agenda_time_text": card.get("time_text"),
            "agenda_category": card.get("category"),
            "meta_text": meta_text,
            "meta_anticipada": meta_fields.get("anticipada"),
            "meta_taquilla": meta_fields.get("taquilla"),
            "meta_tipo": meta_fields.get("tipo"),
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


def scrape_sala_el_sol() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    cards = _extract_listing_cards(session)
    log.info("Found %d Sala El Sol agenda cards", len(cards))

    records: list[dict[str, Any]] = []
    for index, card in enumerate(cards, start=1):
        try:
            log.info(
                "Fetching Sala El Sol detail %d/%d: %s",
                index,
                len(cards),
                card["url"],
            )
            record = _extract_detail_record(session, card)
        except Exception as error:
            log.warning("Skipping Sala El Sol item %s: %s", card["url"], error)
            continue
        if record:
            records.append(record)

    _drop_shared_purchase_urls(records)
    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d Sala El Sol events to %s", len(normalized), OUTPUT_FILE)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(normalized),
        sum(1 for item in normalized if item.get("latitud") is not None),
        sum(1 for item in normalized if item.get("precio") is not None),
    )
    return normalized


if __name__ == "__main__":
    scrape_sala_el_sol()