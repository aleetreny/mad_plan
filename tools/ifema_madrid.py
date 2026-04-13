"""IFEMA Madrid events scraper.

Uses the public calendar page as discovery source, extracting one event card per
listing together with its embedded Event JSON-LD. Detail pages are fetched to
enrich description and outbound info links where available.

Output: outputs/eventos_ifema_madrid.json
"""

from __future__ import annotations

import json
import logging
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

BASE_URL = "https://www.ifema.es"
CALENDAR_URL = f"{BASE_URL}/calendario/todos"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "outputs" / "eventos_ifema_madrid.json"
)
SOURCE_NAME = "ifema_madrid"
REQUEST_TIMEOUT = 30
STOP_HEADINGS = {
    "accesos recomendados",
    "parkings y accesos disponibles",
    "faqs",
    "ifema madrid live",
    "esta web usa cookies",
    "additional links",
    "así fue",
    "asi fue",
    "cómo se vivió",
    "como se vivio",
}
STOP_PREFIXES = {
    "te puede interesar",
    "enlaces destacados",
    "mantente informado",
    "siente la inspiración",
    "siente la inspiracion",
    "descubre todo lo que está ocurriendo en ifema madrid",
    "descubre todo lo que esta ocurriendo en ifema madrid",
    "todos los eventos",
    "destacados",
    "somos ifema madrid",
    "personas y talento",
    "concursos y licitaciones",
    "transparencia",
    "ifema madrid lab",
    "servicios para el visitante",
    "planos interactivos",
    "normativa y soporte",
    "sala de prensa",
    "contáctanos",
    "contacta con nosotros",
    "síguenos",
    "siguenos",
}
OUT_OF_SCOPE_TITLE_URL_TOKENS = {
    "colombia",
    "chile",
    "lisboa",
    "portugal",
    "siconmx",
}
OUT_OF_SCOPE_DESCRIPTION_TOKENS = {
    "guadalajara",
    "bogota",
    "bogotá",
    "corferias",
    "expo guadalajara",
}
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


def _contains_token(text: str, tokens: set[str]) -> bool:
    return any(token in text for token in tokens)


def _is_out_of_scope_event(
    title: str | None,
    url: str | None,
    description: str | None = None,
) -> bool:
    title_url_blob = " ".join(
        part for part in (_clean_text(title), _clean_text(url)) if part
    ).casefold()
    if _contains_token(title_url_blob, OUT_OF_SCOPE_TITLE_URL_TOKENS):
        return True

    description_blob = _clean_text(description).casefold()
    if description_blob and _contains_token(
        description_blob, OUT_OF_SCOPE_DESCRIPTION_TOKENS
    ):
        return True
    return False


def _request_html(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _extract_event_payload(wrapper: Tag) -> dict[str, Any] | None:
    script = wrapper.select_one('script[type="application/ld+json"]')
    if not script:
        return None
    try:
        payload = json.loads(script.get_text(strip=True))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and payload.get("@type") == "Event":
        return payload
    return None


def _extract_categories(wrapper: Tag) -> list[str]:
    categories = [
        _clean_text(node.get_text(" ", strip=True))
        for node in wrapper.select(".tags-wrapper a.tag")
    ]
    return _dedupe_strings(categories)


def _extract_card_image(wrapper: Tag) -> str | None:
    node = wrapper.select_one(".img-wrapper img")
    if not node:
        return None
    candidate = node.get("src") or node.get("data-src")
    return urljoin(BASE_URL, candidate) if candidate else None


def _parse_location(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    location = payload.get("location") or {}
    if not isinstance(location, dict):
        return None, None
    place_name = _clean_text(location.get("name")) or None
    address = location.get("address") or {}
    if not isinstance(address, dict):
        return place_name, None
    street = _clean_text(address.get("streetAddress"))
    locality = _clean_text(address.get("addressLocality"))
    postal_code = _clean_text(address.get("postalCode"))
    address_parts = [part for part in (street, postal_code, locality) if part]
    return place_name, ", ".join(address_parts) if address_parts else None


def _is_madrid_event(payload: dict[str, Any]) -> bool:
    location = payload.get("location") or {}
    address = location.get("address") or {}
    if isinstance(address, dict):
        country = _clean_text(address.get("addressCountry"))
        locality = _clean_text(address.get("addressLocality"))
        if country and country.casefold() != "es":
            return False
        if locality and locality.casefold() not in {"madrid"}:
            return False

    if _is_out_of_scope_event(
        payload.get("name"),
        payload.get("url"),
        payload.get("description"),
    ):
        return False
    return True


def _extract_calendar_cards(session: requests.Session) -> list[dict[str, Any]]:
    soup = _request_html(session, CALENDAR_URL)
    cards: list[dict[str, Any]] = []

    for wrapper in soup.select("div.event-card-wrapper"):
        payload = _extract_event_payload(wrapper)
        if not payload or not _is_madrid_event(payload):
            continue

        title = _clean_text(payload.get("name"))
        url = _clean_text(payload.get("url"))
        if not title or not url:
            continue

        place_name, address = _parse_location(payload)
        cards.append(
            {
                "id": urlparse(url).path.rstrip("/").split("/")[-1] or title,
                "titulo": title,
                "url": url,
                "fecha_inicio": _clean_text(payload.get("startDate")) or None,
                "fecha_fin": _clean_text(payload.get("endDate")) or None,
                "descripcion": _clean_text(payload.get("description")) or None,
                "lugar": place_name,
                "direccion": address,
                "imagen": _extract_card_image(wrapper),
                "categorias": _extract_categories(wrapper),
                "metadata": {
                    "calendar_url": CALENDAR_URL,
                    "caracter_evento": _clean_text(wrapper.get("data-caracterevento")) or None,
                    "categoria_evento_live": _clean_text(wrapper.get("data-categoriaeventolive")) or None,
                },
            }
        )

    unique_by_url: dict[str, dict[str, Any]] = {}
    for card in cards:
        unique_by_url[card["url"]] = card
    return list(unique_by_url.values())


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
    normalized = line.casefold()
    if normalized in STOP_HEADINGS:
        return True
    return any(normalized.startswith(prefix) for prefix in STOP_PREFIXES)


def _trim_core_lines(lines: list[str], title: str) -> list[str]:
    start_index = 0
    for index, line in enumerate(lines):
        if _clean_text(line).casefold() == title.casefold():
            start_index = index
            break
    core = lines[start_index + 1 :]
    for index, line in enumerate(core):
        if _is_stop_line(line):
            return core[:index]
    return core


def _extract_meta_content(soup: BeautifulSoup, selector: str) -> str | None:
    node = soup.select_one(selector)
    if not node:
        return None
    return _clean_text(node.get("content")) or None


def _extract_description(title: str, core_lines: list[str], meta_description: str | None) -> str:
    if meta_description:
        return meta_description

    description_lines: list[str] = []
    for line in core_lines:
        if _is_stop_line(line):
            break
        description_lines.append(line)
    description = _clean_text(" ".join(description_lines))
    return description or title


def _extract_purchase_url(soup: BeautifulSoup, detail_url: str) -> str | None:
    for anchor in soup.select("a[href]"):
        text = _clean_text(anchor.get_text(" ", strip=True)).casefold()
        href = _clean_text(anchor.get("href"))
        if not href:
            continue
        absolute = urljoin(detail_url, href)
        if any(token in text for token in ("comprar entradas", "comprar", "más información", "mas información", "mas informacion")):
            if absolute != detail_url:
                return absolute
    return None


def _extract_detail_fields(session: requests.Session, url: str, fallback_description: str | None) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != urlparse(BASE_URL).netloc:
        return {
            "descripcion": fallback_description,
            "contenido": fallback_description,
            "url_compra": url,
            "imagen": None,
        }

    soup = _request_html(session, url)
    title_node = soup.find("h1")
    title = _clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
    lines = _extract_lines(soup)
    core_lines = _trim_core_lines(lines, title or fallback_description or "")

    meta_description = _extract_meta_content(soup, 'meta[name="description"]')
    description = _extract_description(title or fallback_description or "", core_lines, meta_description)
    content = _clean_text(" ".join(core_lines)) or description
    og_image = _extract_meta_content(soup, 'meta[property="og:image"]')

    return {
        "descripcion": description,
        "contenido": content,
        "url_compra": _extract_purchase_url(soup, url),
        "imagen": og_image,
    }


def scrape_ifema_madrid() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    log.info("Fetching IFEMA Madrid calendar …")
    cards = _extract_calendar_cards(session)
    log.info("Discovered %d IFEMA Madrid calendar cards", len(cards))

    records: list[dict[str, Any]] = []
    for index, card in enumerate(cards, start=1):
        log.info("Fetching IFEMA detail %d/%d: %s", index, len(cards), card["url"])
        detail = _extract_detail_fields(session, card["url"], card.get("descripcion"))
        if _is_out_of_scope_event(
            card.get("titulo"),
            card.get("url"),
            detail.get("descripcion") or card.get("descripcion"),
        ):
            log.info("Skipping IFEMA out-of-scope event: %s", card["url"])
            continue

        metadata = dict(card.get("metadata") or {})
        metadata["detail_url_host"] = urlparse(card["url"]).netloc

        records.append(
            {
                "id": card["id"],
                "titulo": card["titulo"],
                "subtitulo": None,
                "descripcion": detail.get("descripcion") or card.get("descripcion") or card["titulo"],
                "contenido": detail.get("contenido") or detail.get("descripcion") or card.get("descripcion") or card["titulo"],
                "precio": None,
                "moneda": None,
                "lugar": card.get("lugar") or "IFEMA MADRID",
                "direccion": card.get("direccion"),
                "latitud": None,
                "longitud": None,
                "fecha_inicio": card.get("fecha_inicio"),
                "fecha_fin": card.get("fecha_fin"),
                "fechas_disponibles": [],
                "categorias": card.get("categorias") or ["Eventos"],
                "url": card["url"],
                "url_articulo": card["url"],
                "url_compra": detail.get("url_compra"),
                "imagen": detail.get("imagen") or card.get("imagen"),
                "fecha_publicacion": None,
                "fecha_actualizacion": None,
                "fuente": SOURCE_NAME,
                "metadata": metadata,
            }
        )

    records = normalize_plan_records(records, source=SOURCE_NAME)

    OUTPUT_FILE.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Saved %d IFEMA Madrid events to %s", len(records), OUTPUT_FILE)
    return records


if __name__ == "__main__":
    results = scrape_ifema_madrid()
    with_price = sum(1 for event in results if event.get("precio") is not None)
    with_coords = sum(1 for event in results if event.get("latitud") is not None)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(results),
        with_coords,
        with_price,
    )