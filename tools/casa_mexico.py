"""Casa de Mexico events scraper.

Uses the public AJAX fragment behind Casa de Mexico's agenda page to discover
current and upcoming activities across the monthly and category views, then
enriches each item from its detail page.

Output: outputs/eventos_casa_mexico.json
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections import Counter
from datetime import datetime
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

BASE_URL = "https://www.casademexico.es"
AGENDA_URL = f"{BASE_URL}/agenda/"
AGENDA_ENDPOINT = f"{BASE_URL}/wp-content/themes/hello-elementor/rellenar-agenda.php"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "outputs" / "eventos_casa_mexico.json"
)
REQUEST_TIMEOUT = 30
SOURCE_NAME = "casa_mexico"
CASA_MEXICO_ADDRESS = "C. de Alberto Aguilera, 20, Chamberi, 28015 Madrid"
DISCOVERY_VIEWS = [
    ("todas", "mes", "Este mes en Casa de Mexico"),
    ("exposiciones", "todas", "Exposiciones en Casa de Mexico"),
    ("cine", "todas", "Cine en Casa de Mexico"),
    ("academicas", "todas", "Actividades Academicas en Casa de Mexico"),
    ("teatro", "todas", "Escenicas en Casa de Mexico"),
    ("gastronomia", "todas", "Gastronomia en Casa de Mexico"),
    ("literatura", "todas", "Literatura en Casa de Mexico"),
    ("musica", "todas", "Musica en Casa de Mexico"),
    ("familias", "todas", "Actividades Infantiles en Casa de Mexico"),
]
STOP_HEADINGS = {
    "actividades relacionadas",
    "exposiciones pasadas",
    "visitas guiadas",
    "enlaces de interes",
    "sobre nosotros",
    "additional links",
    "gestionar consentimiento",
    "© casa de mexico 2026",
}
SKIP_BODY_PREFIXES = (
    "sesiones",
    "inscripciones",
    "entradas",
    "reservar",
)
GENERIC_LOCATION_LINES = {
    "fundacion casa de mexico en espana",
    "casa de mexico en espana",
}
URL_CATEGORY_MAP = {
    "/exposicion/": ["Exposicion"],
    "/cine-en-casa-de-mexico/": ["Cine"],
    "/actividades-academicas/": ["Academicas"],
    "/teatro/": ["Escenicas"],
    "/gastronomia/": ["Gastronomia"],
    "/literatura/": ["Literatura"],
    "/musica/": ["Musica"],
    "/familias/": ["Infantiles"],
    "/talleres-fcdme/": ["Talleres"],
}
CATEGORY_LABEL_MAP = {
    "academicas": "Academicas",
    "actividad academica": "Academicas",
    "actividades academicas": "Academicas",
    "cine": "Cine",
    "escenicas": "Escenicas",
    "exposicion": "Exposicion",
    "familia": "Familia",
    "familias": "Familia",
    "gastronomia": "Gastronomia",
    "infantiles": "Familia",
    "literatura": "Literatura",
    "musica": "Musica",
    "privado": "Privado",
    "taller": "Talleres",
    "talleres": "Talleres",
    "teatro": "Teatro",
}
SPANISH_MONTHS = {
    "ene": 1,
    "enero": 1,
    "feb": 2,
    "febrero": 2,
    "mar": 3,
    "marzo": 3,
    "abr": 4,
    "abril": 4,
    "may": 5,
    "mayo": 5,
    "jun": 6,
    "junio": 6,
    "jul": 7,
    "julio": 7,
    "ago": 8,
    "agosto": 8,
    "sep": 9,
    "sept": 9,
    "set": 9,
    "septiembre": 9,
    "setiembre": 9,
    "oct": 10,
    "octubre": 10,
    "nov": 11,
    "noviembre": 11,
    "dic": 12,
    "diciembre": 12,
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Referer": AGENDA_URL,
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


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", _clean_text(value))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return normalized.casefold()


def _request_html(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _request_fragment(
    session: requests.Session, tipo: str, fecha: str, titular: str
) -> BeautifulSoup:
    response = session.post(
        AGENDA_ENDPOINT,
        data={"tipo": tipo, "fecha": fecha, "titular": titular},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _split_categories(raw: str | None) -> list[str]:
    if not raw:
        return []
    return _dedupe_strings(_canonicalize_category(part.strip()) for part in raw.split(","))


def _canonicalize_category(value: str | None) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return CATEGORY_LABEL_MAP.get(_normalize_text(text), text)


def _categories_from_url(url: str) -> list[str]:
    for marker, categories in URL_CATEGORY_MAP.items():
        if marker in url:
            return [_canonicalize_category(category) for category in categories]
    return []


def _extract_card_buy_url(card: Tag, detail_url: str) -> str | None:
    for anchor in card.select("a[href]"):
        href = _clean_text(anchor.get("href"))
        if not href:
            continue
        absolute = urljoin(BASE_URL, href)
        if absolute == detail_url:
            continue
        text = _normalize_text(anchor.get_text(" ", strip=True))
        if "eventbrite" in absolute.casefold() or any(
            token in text for token in ("reservar", "entradas", "entrada")
        ):
            return absolute
    return None


def _extract_card(card: Tag, tipo: str, fecha: str, titular: str) -> dict[str, Any] | None:
    link_node = card.select_one(".block-header a[href]") or card.select_one("a[href]")
    if not link_node:
        return None

    detail_url = _clean_text(link_node.get("href"))
    if not detail_url:
        return None
    if "/privado/" in detail_url:
        return None

    title_node = card.select_one(".info-nombre")
    title = _clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
    if not title:
        return None

    category_node = card.select_one(".info-tipo-actividad")
    category_text = (
        _clean_text(category_node.get_text(" ", strip=True)) if category_node else ""
    )
    date_node = card.select_one(".info-fecha .fecha")
    date_text = _clean_text(date_node.get_text(" ", strip=True)) if date_node else ""
    summary_node = card.select_one(".info-descripcion")
    summary = _clean_text(summary_node.get_text(" ", strip=True)) if summary_node else ""
    image_node = card.select_one("img.imagen") or card.select_one("img")
    image = urljoin(BASE_URL, image_node.get("src")) if image_node and image_node.get("src") else None

    return {
        "id": detail_url.rstrip("/").split("/")[-1] or title,
        "titulo": title,
        "url": detail_url,
        "categorias": _dedupe_strings(
            _split_categories(category_text) + _categories_from_url(detail_url)
        ),
        "resumen": summary or None,
        "imagen": image,
        "date_text": date_text or None,
        "url_compra": _extract_card_buy_url(card, detail_url),
        "metadata": {
            "agenda_tipo": tipo,
            "agenda_fecha": fecha,
            "agenda_titular": titular,
            "categoria_tarjeta": category_text or None,
        },
    }


def _merge_card(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    merged["categorias"] = _dedupe_strings(
        (existing.get("categorias") or []) + (incoming.get("categorias") or [])
    )
    if not merged.get("resumen") and incoming.get("resumen"):
        merged["resumen"] = incoming["resumen"]
    if not merged.get("imagen") and incoming.get("imagen"):
        merged["imagen"] = incoming["imagen"]
    if not merged.get("date_text") and incoming.get("date_text"):
        merged["date_text"] = incoming["date_text"]
    if not merged.get("url_compra") and incoming.get("url_compra"):
        merged["url_compra"] = incoming["url_compra"]
    metadata = dict(existing.get("metadata") or {})
    metadata.setdefault("descubierto_en", []).append(
        {
            "tipo": incoming.get("metadata", {}).get("agenda_tipo"),
            "fecha": incoming.get("metadata", {}).get("agenda_fecha"),
            "titular": incoming.get("metadata", {}).get("agenda_titular"),
        }
    )
    metadata["descubierto_en"] = [
        item
        for index, item in enumerate(metadata["descubierto_en"])
        if item not in metadata["descubierto_en"][:index]
    ]
    merged["metadata"] = metadata
    return merged


def _extract_discovery_cards(session: requests.Session) -> list[dict[str, Any]]:
    cards_by_url: dict[str, dict[str, Any]] = {}

    for tipo, fecha, titular in DISCOVERY_VIEWS:
        log.info("Fetching Casa de Mexico agenda view tipo=%s fecha=%s", tipo, fecha)
        soup = _request_fragment(session, tipo, fecha, titular)
        cards = soup.select("div.agenda")
        log.info("Found %d Casa de Mexico cards in view %s/%s", len(cards), tipo, fecha)

        for card in cards:
            parsed = _extract_card(card, tipo, fecha, titular)
            if not parsed:
                continue
            url = parsed["url"]
            if url in cards_by_url:
                cards_by_url[url] = _merge_card(cards_by_url[url], parsed)
            else:
                parsed["metadata"] = {
                    **(parsed.get("metadata") or {}),
                    "calendar_url": AGENDA_URL,
                    "descubierto_en": [
                        {
                            "tipo": tipo,
                            "fecha": fecha,
                            "titular": titular,
                        }
                    ],
                }
                cards_by_url[url] = parsed

    return list(cards_by_url.values())


def _extract_lines(soup: BeautifulSoup) -> list[str]:
    body = soup.body or soup
    lines: list[str] = []
    for raw_line in body.get_text("\n").splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        if lines and line == lines[-1]:
            continue
        lines.append(line)
    return lines


def _is_stop_line(line: str) -> bool:
    normalized = _normalize_text(line)
    return normalized in STOP_HEADINGS


def _find_title_index(lines: list[str], title: str) -> int:
    normalized_title = _normalize_text(title)
    for index, line in enumerate(lines):
        if _normalize_text(line) == normalized_title:
            return index
    return 0


def _month_number(month_name: str) -> int | None:
    return SPANISH_MONTHS.get(_normalize_text(month_name).rstrip("."))


def _parse_spanish_date(day: str, month_name: str, year: str) -> datetime | None:
    month = _month_number(month_name)
    if month is None:
        return None
    try:
        return datetime(int(year), month, int(day))
    except ValueError:
        return None


def _extract_date_range(date_text: str | None) -> tuple[datetime | None, datetime | None]:
    text = _normalize_text(date_text or "")
    if not text:
        return None, None

    range_match = re.search(
        r"del?\s+(\d{1,2})\s+de\s+([a-z.]+)(?:\s+de\s+(\d{4}))?\s+al\s+(\d{1,2})\s+de\s+([a-z.]+)\s+de\s+(\d{4})",
        text,
    )
    if range_match:
        start_day, start_month, start_year, end_day, end_month, end_year = range_match.groups()
        start_year = start_year or end_year
        start = _parse_spanish_date(start_day, start_month, start_year)
        end = _parse_spanish_date(end_day, end_month, end_year)
        return start, end

    single_match = re.search(r"(\d{1,2})\s+de\s+([a-z.]+)\s+de\s+(\d{4})", text)
    if single_match:
        start = _parse_spanish_date(*single_match.groups())
        return start, start
    return None, None


def _extract_time_range(text: str | None) -> tuple[str | None, str | None]:
    raw = _clean_text(text)
    if not raw:
        return None, None
    match = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", raw)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _combine_date_time(value: datetime | None, time_text: str | None) -> str | None:
    if not value or not time_text:
        return None
    try:
        hour, minute = (int(part) for part in time_text.split(":", 1))
    except ValueError:
        return None
    return value.replace(hour=hour, minute=minute).isoformat()


def _parse_price(raw: str | None) -> tuple[float | None, str | None]:
    text = _normalize_text(raw or "")
    if not text:
        return None, None
    if any(token in text for token in ("gratis", "gratuito", "gratuita", "entrada libre")):
        return 0.0, "EUR"

    values: list[float] = []
    for match in re.findall(r"\d+(?:[.,]\d+)?(?=\s*€)", _clean_text(raw)):
        try:
            values.append(float(match.replace(",", ".")))
        except ValueError:
            continue
    if values:
        return min(values), "EUR"
    return None, None


def _looks_like_audience(line: str) -> bool:
    normalized = _normalize_text(line)
    return any(token in normalized for token in ("publico", "interesad", "ninos", "ninas", "familia"))


def _looks_like_content(line: str) -> bool:
    normalized = _normalize_text(line)
    if any(normalized.startswith(prefix) for prefix in SKIP_BODY_PREFIXES):
        return False
    if re.search(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", line):
        return False
    if re.search(r"\d{1,2}\s+de\s+[A-Za-z]", line):
        return False
    if _looks_like_audience(line):
        return False
    if "€" in line or "gratis" in normalized:
        return False
    return len(line) >= 70


def _extract_meta_content(soup: BeautifulSoup, selector: str) -> str | None:
    node = soup.select_one(selector)
    if not node:
        return None
    return _clean_text(node.get("content")) or None


def _extract_purchase_url(soup: BeautifulSoup, detail_url: str) -> str | None:
    for anchor in soup.select("a[href]"):
        href = _clean_text(anchor.get("href"))
        if not href:
            continue
        absolute = urljoin(detail_url, href)
        text = _normalize_text(anchor.get_text(" ", strip=True))
        if absolute == detail_url:
            continue
        if "eventbrite" in absolute.casefold() or any(
            token in text for token in ("entrada", "entradas", "reservar")
        ):
            return absolute
    return None


def _extract_location_lines(metadata_lines: list[str], time_line: str | None) -> list[str]:
    ignored: set[str] = set()
    for line in metadata_lines:
        normalized = _normalize_text(line)
        if _looks_like_audience(line):
            ignored.add(normalized)
        if "€" in line or "gratis" in normalized:
            ignored.add(normalized)
        if re.search(r"\d{1,2}\s+de\s+[A-Za-z]", line):
            ignored.add(normalized)
        if time_line and _clean_text(line) == _clean_text(time_line):
            ignored.add(normalized)
        if any(normalized.startswith(prefix) for prefix in SKIP_BODY_PREFIXES):
            ignored.add(normalized)

    location_lines = [
        line
        for line in metadata_lines
        if _normalize_text(line) not in ignored and len(line) <= 90
    ]
    return _dedupe_strings(location_lines)


def _extract_detail_fields(
    session: requests.Session,
    detail_url: str,
    fallback_title: str,
    fallback_description: str | None,
) -> dict[str, Any]:
    soup = _request_html(session, detail_url)
    title_node = soup.find("h1")
    title = _clean_text(title_node.get_text(" ", strip=True)) if title_node else fallback_title
    meta_description = _extract_meta_content(soup, 'meta[name="description"]')

    lines = _extract_lines(soup)
    title_index = _find_title_index(lines, title)
    core_lines = lines[title_index + 1 :]

    metadata_lines: list[str] = []
    body_lines: list[str] = []
    in_body = False
    for line in core_lines:
        normalized = _normalize_text(line)
        if _is_stop_line(line):
            break
        if not in_body:
            if _looks_like_content(line):
                in_body = True
                body_lines.append(line)
                continue
            metadata_lines.append(line)
            continue

        if any(normalized.startswith(prefix) for prefix in SKIP_BODY_PREFIXES):
            continue
        body_lines.append(line)

    date_line = next(
        (line for line in metadata_lines if re.search(r"\d{1,2}\s+de\s+[A-Za-z]", line)),
        None,
    )
    time_line = next(
        (line for line in metadata_lines if re.search(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", line)),
        None,
    )
    start_date, end_date = _extract_date_range(date_line)
    start_time, end_time = _extract_time_range(time_line or date_line)

    start_value: str | None = None
    end_value: str | None = None
    if start_date and end_date and start_date == end_date and start_time and end_time:
        start_value = _combine_date_time(start_date, start_time)
        end_value = _combine_date_time(end_date, end_time)
    else:
        start_value = start_date.date().isoformat() if start_date else None
        end_value = end_date.date().isoformat() if end_date else None

    location_lines = _extract_location_lines(metadata_lines, time_line)
    room_lines = [
        line
        for line in location_lines
        if _normalize_text(line) not in GENERIC_LOCATION_LINES
    ]
    if room_lines:
        location = " - ".join(room_lines + ["Fundacion Casa de Mexico en Espana"])
    elif location_lines:
        location = " - ".join(location_lines)
    else:
        location = "Fundacion Casa de Mexico en Espana"

    body_text = _clean_text(" ".join(body_lines)) or fallback_description or title
    description = meta_description or fallback_description or body_text or title
    price_line = next(
        (line for line in metadata_lines if "€" in line or "gratis" in _normalize_text(line)),
        None,
    )
    price, currency = _parse_price(price_line)
    og_image = _extract_meta_content(soup, 'meta[property="og:image"]')

    return {
        "titulo": title,
        "descripcion": description,
        "contenido": body_text,
        "fecha_inicio": start_value,
        "fecha_fin": end_value,
        "fechas_disponibles": _dedupe_strings(
            value for value in (start_value, end_value) if value
        ),
        "precio": price,
        "moneda": currency,
        "lugar": location,
        "imagen": og_image,
        "url_compra": _extract_purchase_url(soup, detail_url),
        "metadata": {
            "date_line": date_line,
            "time_line": time_line,
            "price_line": price_line,
            "location_lines": location_lines,
        },
    }


def _drop_shared_purchase_urls(records: list[dict[str, Any]]) -> None:
    counts = Counter(record.get("url_compra") for record in records if record.get("url_compra"))
    for record in records:
        purchase_url = record.get("url_compra")
        if purchase_url and counts[purchase_url] > 1:
            metadata = dict(record.get("metadata") or {})
            metadata["shared_url_compra"] = purchase_url
            record["metadata"] = metadata
            record["url_compra"] = None


def scrape_casa_mexico() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    discovery_cards = _extract_discovery_cards(session)
    log.info("Discovered %d Casa de Mexico unique agenda URLs", len(discovery_cards))

    records: list[dict[str, Any]] = []
    for index, card in enumerate(discovery_cards, start=1):
        log.info("Fetching Casa de Mexico detail %d/%d: %s", index, len(discovery_cards), card["url"])
        detail = _extract_detail_fields(
            session,
            card["url"],
            fallback_title=card["titulo"],
            fallback_description=card.get("resumen"),
        )
        metadata = {
            **(card.get("metadata") or {}),
            **(detail.get("metadata") or {}),
        }

        records.append(
            {
                "id": card["id"],
                "titulo": detail.get("titulo") or card["titulo"],
                "subtitulo": None,
                "descripcion": detail.get("descripcion") or card.get("resumen") or card["titulo"],
                "contenido": detail.get("contenido") or detail.get("descripcion") or card.get("resumen") or card["titulo"],
                "precio": detail.get("precio"),
                "moneda": detail.get("moneda"),
                "lugar": detail.get("lugar") or "Fundacion Casa de Mexico en Espana",
                "direccion": CASA_MEXICO_ADDRESS,
                "latitud": None,
                "longitud": None,
                "fecha_inicio": detail.get("fecha_inicio"),
                "fecha_fin": detail.get("fecha_fin"),
                "fechas_disponibles": detail.get("fechas_disponibles") or [],
                "categorias": card.get("categorias") or _categories_from_url(card["url"]) or ["Cultura"],
                "url": card["url"],
                "url_articulo": card["url"],
                "url_compra": detail.get("url_compra") or card.get("url_compra"),
                "imagen": card.get("imagen") or detail.get("imagen"),
                "fecha_publicacion": None,
                "fecha_actualizacion": None,
                "fuente": SOURCE_NAME,
                "metadata": metadata,
            }
        )

    _drop_shared_purchase_urls(records)
    records = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Saved %d Casa de Mexico events to %s", len(records), OUTPUT_FILE)
    return records


if __name__ == "__main__":
    results = scrape_casa_mexico()
    with_price = sum(1 for event in results if event.get("precio") is not None)
    with_coords = sum(1 for event in results if event.get("latitud") is not None)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(results),
        with_coords,
        with_price,
    )