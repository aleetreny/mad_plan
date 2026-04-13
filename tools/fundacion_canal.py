"""Fundacion Canal events scraper.

Collects the current public programming published on the venue's archive pages
for exhibitions, conferences, and family music, plus the next chamber concert
featured on its dedicated cycle page.

Output: outputs/eventos_fundacion_canal.json
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.fundacioncanal.com"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "outputs" / "eventos_fundacion_canal.json"
)
SOURCE_NAME = "fundacion_canal"
REQUEST_TIMEOUT = 30
VENUE_NAME = "Fundacion Canal"
MATEO_INURRIA_ADDRESS = "C/ Mateo Inurria, 2, 28036 Madrid"
CASTELLANA_ADDRESS = "Paseo de la Castellana, 214, 28046 Madrid"
ARCHIVE_SOURCES = [
    {
        "archive_url": f"{BASE_URL}/exposiciones/",
        "section": "exposiciones",
        "categorias": ["Exposiciones"],
    },
    {
        "archive_url": f"{BASE_URL}/ciclo-de-conferencias/",
        "section": "ciclo_conferencias",
        "categorias": ["Conferencias"],
    },
    {
        "archive_url": f"{BASE_URL}/ciclo-musica-en-familia/",
        "section": "musica_familia",
        "categorias": ["Musica", "Familia"],
    },
]
MUSIC_CHAMBER_URL = f"{BASE_URL}/ciclo-musica-camara/"
DATE_RANGE_RE = re.compile(
    r"(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d{1,2}/\d{1,2}/\d{4})"
)
DATE_TIME_RE = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})\s*(\d{1,2}:\d{2})h?", re.IGNORECASE)
DATE_ONLY_RE = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})")
PRICE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*€")
MINUTES_RE = re.compile(r"(\d+)\s*min", re.IGNORECASE)
HOURS_RE = re.compile(r"(\d+)\s*horas?", re.IGNORECASE)
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


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", _clean_text(value))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "fundacion-canal-item"


def _request_html(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _normalize_url(url: str) -> str:
    absolute = urljoin(BASE_URL, url)
    parsed = urlparse(absolute)
    path = parsed.path.rstrip("/")
    if path:
        path = f"{path}/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _normalize_booking_url(url: str | None) -> str | None:
    if not url:
        return None
    absolute = urljoin(BASE_URL, url)
    parsed = urlparse(absolute)
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _extract_meta_content(soup: BeautifulSoup, selector: str) -> str | None:
    node = soup.select_one(selector)
    if not node:
        return None
    return _clean_text(node.get("content")) or None


def _extract_description_text(soup: BeautifulSoup) -> str | None:
    section = soup.select_one("div.izquierda_contenido > section.descripcion")
    if section:
        text = _clean_text(section.get_text(" ", strip=True))
        text = re.sub(r"^DESCRIPCI[ÓO]N\s+", "", text, flags=re.IGNORECASE)
        if text:
            return text

    meta_description = _extract_meta_content(soup, 'meta[name="description"]')
    if meta_description:
        return meta_description

    main = soup.select_one("div.izquierda_contenido")
    if not main:
        return None
    text = _clean_text(main.get_text(" ", strip=True))
    text = re.sub(r"^@\s*Fundaci[óo]n Canal\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^DESCRIPCI[ÓO]N\s+", "", text, flags=re.IGNORECASE)
    return text or None


def _extract_primary_box(soup: BeautifulSoup) -> Tag | None:
    return soup.select_one("div.lista_comun.elemento_fijo") or soup.select_one("div.lista_comun")


def _extract_box_fields(box: Tag | None) -> tuple[dict[str, str], dict[str, str]]:
    fields: dict[str, str] = {}
    links: dict[str, str] = {}
    if not box:
        return fields, links

    for element in box.find_all("div", class_="elemento", recursive=False):
        title_node = None
        value_node = None
        for child in element.find_all(recursive=False):
            classes = child.get("class") or []
            if "titulo_lista_comun" in classes:
                title_node = child
            elif "texto_lista_comun" in classes:
                value_node = child

        title = _clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
        if not title:
            continue
        value = _clean_text(value_node.get_text(" ", strip=True)) if value_node else ""
        fields[title] = value

        if value_node:
            anchor = value_node.select_one("a[href]")
            if anchor and anchor.get("href"):
                links[title] = _normalize_booking_url(anchor.get("href"))
    return fields, links


def _parse_dmy(value: str) -> str | None:
    try:
        return datetime.strptime(value, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _parse_duration_minutes(text: str | None) -> int | None:
    raw = _clean_text(text)
    if not raw:
        return None
    match = MINUTES_RE.search(raw)
    if match:
        return int(match.group(1))
    match = HOURS_RE.search(raw)
    if match:
        return int(match.group(1)) * 60
    return None


def _parse_date_fields(text: str | None) -> tuple[str | None, str | None, list[str]]:
    raw = _clean_text(text)
    if not raw:
        return None, None, []

    range_match = DATE_RANGE_RE.search(raw)
    if range_match:
        start = _parse_dmy(range_match.group(1))
        end = _parse_dmy(range_match.group(2))
        return start, end, _dedupe_strings([start, end])

    datetime_match = DATE_TIME_RE.search(raw)
    if datetime_match:
        start_date = _parse_dmy(datetime_match.group(1))
        time_text = datetime_match.group(2)
        if not start_date:
            return None, None, []
        start_value = f"{start_date}T{time_text}:00"
        end_value = start_value
        duration_minutes = _parse_duration_minutes(raw)
        if duration_minutes:
            end_dt = datetime.fromisoformat(start_value) + timedelta(minutes=duration_minutes)
            end_value = end_dt.isoformat()
        return start_value, end_value, [start_value]

    date_match = DATE_ONLY_RE.search(raw)
    if date_match:
        value = _parse_dmy(date_match.group(1))
        return value, value, [value] if value else []

    return None, None, []


def _parse_price(text: str | None) -> float | None:
    raw = _clean_text(text)
    if not raw:
        return None
    lowered = raw.casefold()
    if any(token in lowered for token in ("entrada gratuita", "gratuita", "gratuito", "gratis")):
        return 0.0

    values: list[float] = []
    for match in PRICE_RE.findall(raw):
        try:
            values.append(float(match.replace(",", ".")))
        except ValueError:
            continue
    return min(values) if values else None


def _infer_address(location: str | None) -> str:
    raw = _clean_text(location)
    lowered = raw.casefold()
    if "castellana 214" in lowered:
        return CASTELLANA_ADDRESS
    return MATEO_INURRIA_ADDRESS


def _record_is_live(record: dict[str, Any], *, today: date) -> bool:
    candidate_values = list(record.get("fechas_disponibles") or [])
    candidate_values.extend(
        value for value in (record.get("fecha_fin"), record.get("fecha_inicio")) if value
    )
    for value in candidate_values:
        raw = _clean_text(value)
        if not raw:
            continue
        date_text = raw[:10]
        try:
            if date.fromisoformat(date_text) >= today:
                return True
        except ValueError:
            continue
    return False


def _extract_archive_items(session: requests.Session) -> list[dict[str, Any]]:
    items_by_url: dict[str, dict[str, Any]] = {}

    for source in ARCHIVE_SOURCES:
        soup = _request_html(session, source["archive_url"])
        for anchor in soup.select("div.exposiciones_contenedor a.imagen_evento[href]"):
            url = _normalize_url(anchor.get("href"))
            container = anchor.find_parent("div", class_="exposiciones_contenido")
            listing_text = _clean_text(container.get_text(" ", strip=True)) if container else ""
            existing = items_by_url.get(url)
            if existing:
                existing["categorias"] = _dedupe_strings(
                    existing.get("categorias", []) + source["categorias"]
                )
                continue
            items_by_url[url] = {
                "url": url,
                "section": source["section"],
                "categorias": list(source["categorias"]),
                "listing_text": listing_text,
            }

    return list(items_by_url.values())


def _extract_image(soup: BeautifulSoup) -> str | None:
    return _extract_meta_content(soup, 'meta[property="og:image"]')


def _extract_chamber_summary(card: Tag) -> tuple[str, str]:
    description_node = card.select_one("div.desplegable_descripcion")
    if not description_node:
        return "", ""

    paragraphs = [
        _clean_text(paragraph.get_text(" ", strip=True))
        for paragraph in description_node.select("p")
    ]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    if not paragraphs:
        text = _clean_text(description_node.get_text(" ", strip=True))
        return text, text

    summary_parts: list[str] = []
    collect = False
    for paragraph in paragraphs:
        if paragraph.casefold() == "notas al concierto":
            collect = True
            continue
        if collect:
            summary_parts.append(paragraph)

    full_text = " ".join(paragraphs)
    summary = " ".join(summary_parts) if summary_parts else full_text
    return summary, full_text


def _extract_detail_record(
    session: requests.Session,
    item: dict[str, Any],
) -> dict[str, Any] | None:
    soup = _request_html(session, item["url"])
    title_node = soup.find("h1")
    title = _clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
    if not title:
        return None

    box = _extract_primary_box(soup)
    fields, links = _extract_box_fields(box)
    raw_date = fields.get("Fecha") or fields.get("Fecha y hora") or fields.get("Fecha y horario")
    start_value, end_value, available_dates = _parse_date_fields(raw_date)
    if not start_value and not end_value:
        return None

    price_sources = [
        fields.get("Entradas"),
        fields.get("Donación en concepto de elección de asiento"),
        fields.get("Coste"),
    ]
    price = None
    for source in price_sources:
        price = _parse_price(source)
        if price is not None:
            break

    location = fields.get("Ubicación") or VENUE_NAME
    description = _extract_description_text(soup) or item.get("listing_text") or title
    booking_url = links.get("Entradas")

    tags = _dedupe_strings([fields.get("Edades")])

    return {
        "id": urlparse(item["url"]).path.rstrip("/").split("/")[-1],
        "titulo": title,
        "subtitulo": None,
        "descripcion": description,
        "contenido": description,
        "precio": price,
        "moneda": "EUR" if price is not None else None,
        "lugar": location,
        "direccion": _infer_address(location),
        "latitud": None,
        "longitud": None,
        "fecha_inicio": start_value,
        "fecha_fin": end_value,
        "fechas_disponibles": available_dates,
        "categorias": item.get("categorias") or ["Cultura"],
        "etiquetas": tags,
        "url": item["url"],
        "url_articulo": item["url"],
        "url_compra": booking_url,
        "imagen": _extract_image(soup),
        "fecha_publicacion": None,
        "fecha_actualizacion": None,
        "fuente": SOURCE_NAME,
        "metadata": {
            "section": item.get("section"),
            "raw_date": raw_date,
            "raw_price": next((value for value in price_sources if value), None),
            "raw_location": fields.get("Ubicación"),
        },
    }


def _extract_music_chamber_record(session: requests.Session) -> dict[str, Any] | None:
    soup = _request_html(session, MUSIC_CHAMBER_URL)
    current_card = soup.select_one("div.elemento.ciclo_camara")
    info_box = soup.select_one(
        "section.programa_contenedor.contenedor_principal .lista_comun.elemento_fijo"
    )
    if not current_card or not info_box:
        return None

    title_node = current_card.select_one("h3.titulo_2")
    date_node = current_card.select_one("div.fecha")
    description_node = current_card.select_one("div.desplegable_descripcion")
    if not title_node or not date_node:
        return None

    fields, _ = _extract_box_fields(info_box)
    title = _clean_text(title_node.get_text(" ", strip=True))
    raw_date = _clean_text(date_node.get_text(" ", strip=True))
    start_value, end_value, available_dates = _parse_date_fields(raw_date)
    if not start_value and not end_value:
        return None

    summary, full_description = _extract_chamber_summary(current_card)

    booking_url = None
    for anchor in info_box.select("a[href]"):
        href = _normalize_booking_url(anchor.get("href"))
        if href and "entradas.fundacioncanal.com" in href:
            booking_url = href
            break

    price = _parse_price(fields.get("Donación en concepto de elección de asiento"))
    location = fields.get("Ubicación") or VENUE_NAME

    return {
        "id": _slugify(f"{title}-{start_value or raw_date}"),
        "titulo": title,
        "subtitulo": None,
        "descripcion": summary or title,
        "contenido": full_description or summary or title,
        "precio": price,
        "moneda": "EUR" if price is not None else None,
        "lugar": location,
        "direccion": _infer_address(location),
        "latitud": None,
        "longitud": None,
        "fecha_inicio": start_value,
        "fecha_fin": end_value,
        "fechas_disponibles": available_dates,
        "categorias": ["Musica"],
        "etiquetas": ["Ciclo de Musica de Camara"],
        "url": MUSIC_CHAMBER_URL,
        "url_articulo": MUSIC_CHAMBER_URL,
        "url_compra": booking_url,
        "imagen": _extract_image(soup),
        "fecha_publicacion": None,
        "fecha_actualizacion": None,
        "fuente": SOURCE_NAME,
        "metadata": {
            "section": "musica_camara",
            "raw_date": raw_date,
            "raw_price": fields.get("Donación en concepto de elección de asiento"),
            "raw_location": fields.get("Ubicación"),
        },
    }


def _drop_shared_booking_urls(records: list[dict[str, Any]]) -> None:
    counts = Counter(record.get("url_compra") for record in records if record.get("url_compra"))
    for record in records:
        booking_url = record.get("url_compra")
        if not booking_url or counts[booking_url] <= 1:
            continue
        record.setdefault("metadata", {})["shared_booking_url"] = booking_url
        record["url_compra"] = None


def scrape_fundacion_canal() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)
    today = date.today()

    discovered = _extract_archive_items(session)
    log.info("Found %d Fundacion Canal detail URLs", len(discovered))

    records: list[dict[str, Any]] = []
    for index, item in enumerate(discovered, start=1):
        try:
            log.info(
                "Fetching Fundacion Canal detail %d/%d: %s",
                index,
                len(discovered),
                item["url"],
            )
            record = _extract_detail_record(session, item)
        except Exception as error:
            log.warning("Skipping Fundacion Canal item %s: %s", item["url"], error)
            continue
        if record and _record_is_live(record, today=today):
            records.append(record)

    try:
        chamber_record = _extract_music_chamber_record(session)
    except Exception as error:
        log.warning("Skipping Fundacion Canal chamber record: %s", error)
        chamber_record = None
    if chamber_record and _record_is_live(chamber_record, today=today):
        records.append(chamber_record)

    _drop_shared_booking_urls(records)
    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d Fundacion Canal events to %s", len(normalized), OUTPUT_FILE)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(normalized),
        sum(1 for item in normalized if item.get("latitud") is not None),
        sum(1 for item in normalized if item.get("precio") is not None),
    )
    return normalized


if __name__ == "__main__":
    scrape_fundacion_canal()