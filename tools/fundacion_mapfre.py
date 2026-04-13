"""Fundacion MAPFRE Madrid exhibitions scraper.

Uses the current Sala Recoletos exhibitions page for discovery and each public
detail page for structured schema data plus editorial description extraction.

Output: outputs/eventos_fundacion_mapfre.json
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections import Counter
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

BASE_URL = "https://www.fundacionmapfre.org"
DISCOVERY_URL = f"{BASE_URL}/arte-y-cultura/exposiciones/sala-recoletos/"
GENERIC_PURCHASE_URL = f"{BASE_URL}/arte-y-cultura/compra-de-entradas/"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "outputs" / "eventos_fundacion_mapfre.json"
)
SOURCE_NAME = "fundacion_mapfre"
VENUE_NAME = "Sala Recoletos Fundacion MAPFRE"
VENUE_ADDRESS = "Paseo de Recoletos, 23, 28004 Madrid"
REQUEST_TIMEOUT = 30
DISCOVERY_PATH_PREFIX = "/arte-y-cultura/exposiciones/sala-recoletos/"
DISCOVERY_LINK_TOKEN = "descubre la exposicion"
DATE_RANGE_RE = re.compile(r"(\d{1,2}\.[A-Z]{3}\.\d{4}).*?(\d{1,2}\.[A-Z]{3}\.\d{4})")
DETAIL_SKIP_TOKENS = {
    "inicio >",
    "exposicion ",
    "donde ",
    "como llegar",
    "horario general",
    "audiogui",
    "accesibilidad",
    "libreria",
    "prensa",
    "descargate",
    "compra de entradas",
    "selecciona una opcion",
    "entrada general",
    "clientes mapfre",
    "entidades colaboradoras",
    "visita de grupo",
    "colegios ",
    "familias ",
    "otras tarifas",
    "si necesitas mas informacion",
    "suscribete a nuestra newsletter",
    "tratamiento de datos personales",
}
DESCRIPTION_STOP_MARKERS = (
    "Descárgate las claves de la exposición",
    "Descárgate los textos de sala",
    "Accede a la visita virtual de la exposición",
    "Descargate las claves de la exposicion",
    "Descargate los textos de sala",
    "Accede a la visita virtual de la exposicion",
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


def _normalize_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", _clean_text(value))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return normalized.casefold()


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
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return BeautifulSoup(response.text, "html.parser")


def _normalize_iso_datetime(value: Any) -> str | None:
    raw = _clean_text(value)
    if not raw:
        return None
    if any(token in raw for token in ("T00:00:00", "T23:59:00", "T23:59:59")):
        return raw.split("T", 1)[0]
    if re.search(r"[+-]\d{4}$", raw):
        return f"{raw[:-2]}:{raw[-2:]}"
    return raw


def _extract_card_image(row: Tag | None) -> str | None:
    if not row:
        return None
    image_node = row.select_one("img[src], img[data-src]")
    if not image_node:
        return None
    candidate = image_node.get("src") or image_node.get("data-src")
    return urljoin(BASE_URL, candidate) if candidate else None


def _extract_card_dates(row_text: str) -> tuple[str | None, str | None]:
    match = DATE_RANGE_RE.search(row_text)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _extract_discovery_cards(session: requests.Session) -> list[dict[str, Any]]:
    soup = _request_html(session, DISCOVERY_URL)
    cards_by_url: dict[str, dict[str, Any]] = {}

    for anchor in soup.select("a[href]"):
        href = _clean_text(anchor.get("href"))
        if not href:
            continue
        absolute = urljoin(BASE_URL, href)
        path = urlparse(absolute).path.rstrip("/") + "/"
        if not path.startswith(DISCOVERY_PATH_PREFIX):
            continue
        if absolute.rstrip("/") == DISCOVERY_URL.rstrip("/"):
            continue
        if _normalize_text(anchor.get_text(" ", strip=True)) != DISCOVERY_LINK_TOKEN:
            continue

        row = anchor.find_parent(
            "div",
            class_=lambda value: value and "et_pb_row" in str(value).split(),
        )
        row_text = _clean_text(row.get_text(" ", strip=True)) if row else ""
        if "COMPRAR ENTRADA" not in row_text:
            continue

        start_hint, end_hint = _extract_card_dates(row_text)
        cards_by_url[absolute] = {
            "url": absolute,
            "row_text": row_text,
            "fecha_inicio_hint": start_hint,
            "fecha_fin_hint": end_hint,
            "imagen_hint": _extract_card_image(row),
        }

    return list(cards_by_url.values())


def _extract_event_payload(soup: BeautifulSoup) -> dict[str, Any]:
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
            if isinstance(item, dict) and item.get("@type") == "ExhibitionEvent":
                return item
    return {}


def _extract_detail_fragments(soup: BeautifulSoup, title: str) -> list[str]:
    fragments: list[str] = []
    seen: set[str] = set()
    normalized_title = _normalize_text(title)

    for node in soup.select(".et_pb_text_inner"):
        text = _clean_text(node.get_text(" ", strip=True))
        if len(text) < 80:
            continue
        normalized = _normalize_text(text)
        if normalized == normalized_title or normalized.startswith(f"{normalized_title} "):
            continue
        if any(token in normalized for token in DETAIL_SKIP_TOKENS):
            continue
        if text.casefold() in seen:
            continue
        seen.add(text.casefold())
        fragments.append(text)

    return fragments


def _trim_description_text(text: str) -> str:
    trimmed = text
    for marker in DESCRIPTION_STOP_MARKERS:
        if marker in trimmed:
            trimmed = trimmed.split(marker, 1)[0]
    return _clean_text(trimmed)


def _extract_description(soup: BeautifulSoup, payload: dict[str, Any], title: str) -> str:
    for node in soup.select(".fm-expo-list-text"):
        text = _trim_description_text(_clean_text(node.get_text(" ", strip=True)))
        if len(text) >= 180:
            return text

    fragments = _extract_detail_fragments(soup, title)
    for fragment in fragments:
        trimmed = _trim_description_text(fragment)
        normalized = _normalize_text(trimmed)
        if normalized.startswith(("visita guiada", "visita comentada", "importante:")):
            continue
        if len(trimmed) >= 120:
            return trimmed
    return _clean_text(payload.get("description")) or title


def _extract_image(payload: dict[str, Any], fallback: str | None) -> str | None:
    image = payload.get("image") or {}
    if isinstance(image, dict):
        candidate = _clean_text(image.get("url"))
        if candidate:
            return candidate
    if isinstance(image, str):
        candidate = _clean_text(image)
        if candidate:
            return candidate
    return fallback


def _extract_place(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    location = payload.get("location") or {}
    if not isinstance(location, dict):
        return VENUE_NAME, VENUE_ADDRESS

    name = _clean_text(location.get("name")) or VENUE_NAME
    address = location.get("address") or {}
    if not isinstance(address, dict):
        return name, VENUE_ADDRESS

    street = _clean_text(address.get("streetAddress"))
    postal_code = _clean_text(address.get("postalCode"))
    locality = _clean_text(address.get("addressLocality"))
    address_parts = [part for part in (street, postal_code, locality) if part]
    return name, ", ".join(address_parts) if address_parts else VENUE_ADDRESS


def _extract_price(payload: dict[str, Any]) -> tuple[float | None, str | None, str | None]:
    offers = payload.get("offers") or {}
    if not isinstance(offers, dict):
        return None, None, None

    raw_price = _clean_text(offers.get("price"))
    currency = _clean_text(offers.get("priceCurrency")) or None
    if not raw_price:
        return None, currency, _clean_text(offers.get("url")) or None
    try:
        return float(raw_price.replace(",", ".")), currency, _clean_text(offers.get("url")) or None
    except ValueError:
        return None, currency, _clean_text(offers.get("url")) or None


def _build_categories(title: str, description: str) -> list[str]:
    categories = ["Exposiciones", "Arte"]
    blob = _normalize_text(f"{title} {description}")
    if "fotograf" in blob:
        categories.append("Fotografia")
    return categories


def _build_record(session: requests.Session, card: dict[str, Any]) -> dict[str, Any] | None:
    soup = _request_html(session, card["url"])
    payload = _extract_event_payload(soup)
    title_node = soup.find("h1")
    title = _clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
    title = title or _clean_text(payload.get("name"))
    if not title:
        return None

    description = _extract_description(soup, payload, title)
    price, currency, purchase_url = _extract_price(payload)
    place, address = _extract_place(payload)

    metadata = {
        "row_text": card.get("row_text"),
        "fecha_inicio_hint": card.get("fecha_inicio_hint"),
        "fecha_fin_hint": card.get("fecha_fin_hint"),
        "schema_type": _clean_text(payload.get("@type")) or None,
        "schema_offer_url": purchase_url,
        "schema_offer_price": _clean_text((payload.get("offers") or {}).get("price")),
    }

    return {
        "id": urlparse(card["url"]).path.rstrip("/").split("/")[-1],
        "titulo": title,
        "subtitulo": None,
        "descripcion": description,
        "contenido": description,
        "precio": price,
        "moneda": currency,
        "lugar": place,
        "direccion": address,
        "latitud": None,
        "longitud": None,
        "fecha_inicio": _normalize_iso_datetime(payload.get("startDate")),
        "fecha_fin": _normalize_iso_datetime(payload.get("endDate")),
        "fechas_disponibles": [],
        "categorias": _build_categories(title, description),
        "etiquetas": ["Sala Recoletos"],
        "url": card["url"],
        "url_articulo": card["url"],
        "url_compra": purchase_url,
        "imagen": _extract_image(payload, card.get("imagen_hint")),
        "fecha_publicacion": None,
        "fecha_actualizacion": None,
        "fuente": SOURCE_NAME,
        "metadata": metadata,
    }


def _drop_shared_purchase_urls(records: list[dict[str, Any]]) -> None:
    counts = Counter(record.get("url_compra") for record in records if record.get("url_compra"))
    for record in records:
        purchase_url = record.get("url_compra")
        if not purchase_url:
            continue
        if purchase_url == GENERIC_PURCHASE_URL or counts[purchase_url] > 1:
            record.setdefault("metadata", {})["shared_purchase_url"] = purchase_url
            record["url_compra"] = None


def scrape_fundacion_mapfre() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    cards = _extract_discovery_cards(session)
    log.info("Found %d Fundacion MAPFRE Madrid exhibition cards", len(cards))

    records: list[dict[str, Any]] = []
    for index, card in enumerate(cards, start=1):
        try:
            log.info(
                "Fetching Fundacion MAPFRE detail %d/%d: %s",
                index,
                len(cards),
                card["url"],
            )
            record = _build_record(session, card)
        except Exception as error:
            log.warning("Skipping Fundacion MAPFRE item %s: %s", card["url"], error)
            continue
        if record:
            records.append(record)

    _drop_shared_purchase_urls(records)
    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d Fundacion MAPFRE events to %s", len(normalized), OUTPUT_FILE)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(normalized),
        sum(1 for item in normalized if item.get("latitud") is not None),
        sum(1 for item in normalized if item.get("precio") is not None),
    )
    return normalized


if __name__ == "__main__":
    scrape_fundacion_mapfre()