"""esMadrid agenda scraper.

Discovers Madrid event pages from esMadrid agenda verticals and enriches each
detail page from its JSON-LD Event schema and visible ticketing links.

Output: outputs/eventos_esmadrid.json
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.esmadrid.com"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "eventos_esmadrid.json"
REQUEST_DELAY = 0.2
REQUEST_TIMEOUT = 45
REQUEST_RETRIES = 3
RETRY_BACKOFF_SECONDS = 4.0
SOURCE_NAME = "esmadrid"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
DISCOVERY_PAGES = {
    "Agenda": f"{BASE_URL}/agenda-madrid",
    "Eventos": f"{BASE_URL}/agenda-eventos-madrid",
    "Exposiciones": f"{BASE_URL}/agenda-exposiciones-madrid",
    "Musica": f"{BASE_URL}/agenda-musica-madrid",
    "Teatro y Danza": f"{BASE_URL}/agenda-teatro-madrid",
    "Musicales": f"{BASE_URL}/agenda-musicales",
    "Familia": f"{BASE_URL}/agenda-infantil",
    "Deportes": f"{BASE_URL}/agenda-deportes-madrid",
    "Ferias y Congresos": f"{BASE_URL}/agenda-ferias-y-congresos-madrid",
}
TICKET_KEYWORDS = (
    "entrada",
    "entradas",
    "compra",
    "comprar",
    "tickets",
    "ticket",
    "reserva",
    "reservar",
    "venta",
)
IGNORED_PURCHASE_PATHS = {
    "/compras-madrid",
}
AMBIGUOUS_LOCATION_HINTS = (
    "varios locales",
    "varias salas",
    "varios espacios",
    "varias estaciones",
)


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


def _request_soup(session: requests.Session, url: str) -> BeautifulSoup:
    last_error: Exception | None = None
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as error:
            last_error = error
            if attempt < REQUEST_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * attempt
                log.warning(
                    "esMadrid request failed (%d/%d) %s: %s — retrying in %.0fs",
                    attempt, REQUEST_RETRIES, url, error, wait,
                )
                time.sleep(wait)
    raise last_error  # type: ignore[misc]


def _extract_discovery_links(session: requests.Session) -> dict[str, set[str]]:
    links_to_categories: dict[str, set[str]] = {}
    failed_pages = 0

    for category, url in DISCOVERY_PAGES.items():
        try:
            soup = _request_soup(session, url)
        except requests.RequestException as error:
            failed_pages += 1
            log.warning("Skipping esMadrid discovery page %s: %s", url, error)
            continue
        found = 0
        for anchor in soup.find_all("a", href=True):
            href = urljoin(url, anchor["href"])
            if "/agenda/" not in href:
                continue
            if href.rstrip("/") == url.rstrip("/"):
                continue
            links_to_categories.setdefault(href, set()).add(category)
            found += 1
        log.info("esMadrid %s: %d agenda links", category, len(links_to_categories))
        time.sleep(REQUEST_DELAY)

    if failed_pages == len(DISCOVERY_PAGES):
        raise RuntimeError("All esMadrid discovery pages failed")

    return links_to_categories


def _extract_event_schema(soup: BeautifulSoup) -> dict[str, Any] | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(tag.string)
        except (TypeError, json.JSONDecodeError):
            continue

        graph = payload.get("@graph") if isinstance(payload, dict) else None
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict) and item.get("@type") == "Event":
                    return item

        if isinstance(payload, dict) and payload.get("@type") == "Event":
            return payload

    return None


def _extract_image(schema: dict[str, Any] | None, soup: BeautifulSoup) -> str | None:
    image = (schema or {}).get("image")
    if isinstance(image, dict):
        image = image.get("url")
    if isinstance(image, list):
        for candidate in image:
            text = _clean_text(candidate)
            if text:
                return text
    else:
        text = _clean_text(image)
        if text:
            return text

    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        return _clean_text(meta["content"])
    return None


def _extract_description(schema: dict[str, Any] | None, soup: BeautifulSoup) -> str:
    description = _clean_text((schema or {}).get("description"))
    if description:
        return description

    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        description = _clean_text(meta["content"])
        if description:
            return description

    title = soup.find("h1")
    return _clean_text(title.get_text(" ", strip=True) if title else "")


def _description_has_ambiguous_location(description: str) -> bool:
    text = _clean_text(description).casefold()
    if not text:
        return False
    return any(token in text for token in AMBIGUOUS_LOCATION_HINTS)


def _build_source_id(page_url: str) -> str:
    path = urlparse(page_url).path.rstrip("/")
    if path:
        return path.rsplit("/", 1)[-1]
    return page_url.rstrip("/").rsplit("/", 1)[-1]


def _build_address(location: dict[str, Any]) -> str | None:
    address = location.get("address") or {}
    if not isinstance(address, dict):
        return None
    parts = _dedupe_strings(
        [
            address.get("streetAddress"),
            address.get("addressLocality") or address.get("addressRegion"),
            address.get("postalCode"),
        ]
    )
    if parts:
        return ", ".join(parts)
    return None


def _extract_purchase_url(soup: BeautifulSoup, page_url: str) -> str | None:
    candidates: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(page_url, anchor["href"])
        if href.rstrip("/") == page_url.rstrip("/"):
            continue

        parsed = urlparse(href)
        if parsed.netloc.lower().endswith("esmadrid.com") and parsed.path.rstrip("/") in IGNORED_PURCHASE_PATHS:
            continue

        text = _clean_text(anchor.get_text(" ", strip=True)).casefold()
        if any(keyword in text for keyword in TICKET_KEYWORDS):
            candidates.append(href)
            continue

        host = parsed.netloc.lower()
        if any(token in host for token in ("ticket", "entrad", "reserv", "taquilla")):
            candidates.append(href)

    unique = _dedupe_strings(candidates)
    return unique[0] if unique else None


def _extract_offer(schema: dict[str, Any] | None) -> tuple[float | None, str | None]:
    offers = (schema or {}).get("offers")
    if isinstance(offers, dict):
        offers = [offers]
    if not isinstance(offers, list):
        return None, None

    prices: list[float] = []
    currency = None
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        value = offer.get("price")
        if value not in (None, ""):
            try:
                prices.append(float(value))
            except (TypeError, ValueError):
                pass
        if not currency:
            currency = _clean_text(offer.get("priceCurrency")) or None

    if prices:
        return min(prices), currency or "EUR"
    return None, currency


def _extract_record(
    session: requests.Session, page_url: str, categories: set[str]
) -> dict[str, Any] | None:
    soup = _request_soup(session, page_url)
    schema = _extract_event_schema(soup)
    if not schema:
        return None

    title = _clean_text(schema.get("name"))
    if not title:
        return None

    location = schema.get("location") or {}
    if not isinstance(location, dict):
        location = {}

    price, currency = _extract_offer(schema)
    description = _extract_description(schema, soup)
    ticket_url = _extract_purchase_url(soup, page_url)
    location_name = _clean_text(location.get("name")) or None
    address = _build_address(location)
    location_ambiguous = False
    if not (location_name or address):
        location_ambiguous = _description_has_ambiguous_location(description)

    metadata: dict[str, Any] = {}
    schema_id = _clean_text(schema.get("@id")) or None
    if schema_id:
        metadata["schema_id"] = schema_id
    if location_ambiguous:
        metadata["ubicacion_ambigua"] = True

    return {
        "id": _build_source_id(page_url),
        "titulo": title,
        "precio": price,
        "moneda": currency,
        "lugar": location_name,
        "direccion": address,
        "latitud": None,
        "longitud": None,
        "fecha_inicio": _clean_text(schema.get("startDate")) or None,
        "fecha_fin": _clean_text(schema.get("endDate")) or _clean_text(schema.get("startDate")) or None,
        "fechas_disponibles": _dedupe_strings(
            [schema.get("startDate"), schema.get("endDate")]
        ),
        "categorias": _dedupe_strings(sorted(categories)),
        "url": page_url,
        "url_articulo": page_url,
        "url_compra": ticket_url,
        "imagen": _extract_image(schema, soup),
        "descripcion": description,
        "contenido": description,
        "fuente": SOURCE_NAME,
        "metadata": metadata,
    }


def _drop_shared_purchase_urls(records: list[dict[str, Any]]) -> None:
    counts = Counter(record.get("url_compra") for record in records if record.get("url_compra"))
    for record in records:
        purchase_url = record.get("url_compra")
        if not purchase_url or counts[purchase_url] <= 1:
            continue
        record.setdefault("metadata", {})["shared_purchase_url"] = purchase_url
        record["url_compra"] = None


def scrape_esmadrid() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    links_to_categories = _extract_discovery_links(session)
    if not links_to_categories:
        # Do not overwrite the previous good output with an empty list: a
        # discovery failure is a scrape failure, not "no events in Madrid".
        raise RuntimeError("No esMadrid agenda links discovered")

    log.info("esMadrid unique agenda pages: %d", len(links_to_categories))
    records: list[dict[str, Any]] = []
    for index, (page_url, categories) in enumerate(sorted(links_to_categories.items()), start=1):
        try:
            record = _extract_record(session, page_url, categories)
        except requests.RequestException as error:
            log.warning("Failed esMadrid detail %s: %s", page_url, error)
            continue

        if record:
            records.append(record)

        if index % 25 == 0 or index == len(links_to_categories):
            log.info("Processed %d/%d esMadrid detail pages", index, len(links_to_categories))
        time.sleep(REQUEST_DELAY)

    _drop_shared_purchase_urls(records)
    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d esMadrid events to %s", len(normalized), OUTPUT_FILE)
    return normalized


if __name__ == "__main__":
    results = scrape_esmadrid()
    with_image = sum(1 for item in results if item.get("imagen"))
    with_location = sum(1 for item in results if item.get("lugar") or item.get("direccion"))
    with_price = sum(1 for item in results if item.get("precio") is not None)
    log.info(
        "Summary: %d events, %d with image, %d with location, %d with price",
        len(results),
        with_image,
        with_location,
        with_price,
    )