"""Ticketmaster Madrid scraper.

Discovers Madrid events from Ticketmaster's server-rendered city pages, groups
repeated sessions for the same plan, and enriches native Ticketmaster entries
through the public eventinfo endpoint.

Output: outputs/eventos_ticketmaster.json
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import cloudscraper
import requests
from bs4 import BeautifulSoup

try:
    from .normalization import normalize_plan_records
    from .remote_images import extract_page_image
except ImportError:
    from normalization import normalize_plan_records
    from remote_images import extract_page_image

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.ticketmaster.es"
DISCOVER_URL = f"{BASE_URL}/discover/madrid"
EVENTINFO_URL = f"{BASE_URL}/api/eventinfo/{{event_id}}"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "eventos_ticketmaster.json"
SOURCE_NAME = "ticketmaster"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.35
MAX_PAGES = 80
PAGE_SIZE = 20
GENERIC_IMAGE_TOKEN = "TM_GenCatImgs_Generic"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
CATEGORY_MAP = {
    "KZFzniwnSyZfZ7v7nJ": "Música",
    "KZFzniwnSyZfZ7v7na": "Arte y Teatro",
    "KZFzniwnSyZfZ7v7nE": "Deporte",
    "KZFzniwnSyZfZ7v7nl": "Familia y Otros",
    "family": "Familia y Otros",
}
PARTNER_IMAGE_CACHE: dict[str, str | None] = {}


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


def _build_soup(response: requests.Response) -> BeautifulSoup:
    if response.apparent_encoding and response.encoding != response.apparent_encoding:
        response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def _request_soup(
    session: requests.Session, url: str, *, params: dict[str, Any] | None = None
) -> BeautifulSoup:
    response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return _build_soup(response)


def _request_json(session: requests.Session, url: str) -> dict[str, Any] | None:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    if response.status_code != 200:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _extract_city_payload(soup: BeautifulSoup) -> dict[str, Any] | None:
    next_tag = soup.find("script", id="__NEXT_DATA__")
    if not next_tag or not next_tag.string:
        return None

    try:
        data = json.loads(next_tag.string)
    except json.JSONDecodeError:
        return None

    queries = (
        data.get("props", {})
        .get("pageProps", {})
        .get("initialReduxState", {})
        .get("api", {})
        .get("queries", {})
    )
    for key, value in queries.items():
        if key.startswith("cityEvents("):
            return value.get("data")
    return None


def _collect_raw_events(session: requests.Session) -> list[dict[str, Any]]:
    raw_events: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, ...]] = set()

    for page in range(MAX_PAGES):
        soup = _request_soup(
            session,
            DISCOVER_URL,
            params={"language": "es-es", "page": page},
        )
        payload = _extract_city_payload(soup)
        if not payload:
            log.info("Stopping Ticketmaster discovery at page %d: no payload", page)
            break

        events = payload.get("events") or []
        if not events:
            log.info("Stopping Ticketmaster discovery at page %d: empty page", page)
            break

        signature = tuple(_clean_text(event.get("id")) for event in events[:3])
        if signature and signature in seen_signatures:
            log.info("Stopping Ticketmaster discovery at page %d: repeated page signature", page)
            break
        if signature:
            seen_signatures.add(signature)

        raw_events.extend(events)
        log.info(
            "Ticketmaster page %d: %d events (cumulative=%d)",
            page,
            len(events),
            len(raw_events),
        )

        if len(events) < PAGE_SIZE:
            break
        time.sleep(REQUEST_DELAY)

    return raw_events


def _group_raw_events(raw_events: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in raw_events:
        title = _clean_text(event.get("title"))
        venue_name = _clean_text((event.get("venue") or {}).get("name"))
        url = _clean_text(event.get("url"))
        if not title:
            continue
        groups[(title, venue_name, url)].append(event)

    return list(groups.values())


def _select_representative_event(group: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        group,
        key=lambda item: (
            0 if not (item.get("partnerEvent") or item.get("isPartner")) else 1,
            (item.get("dates") or {}).get("startDate") or "",
        ),
    )[0]


def _fetch_detail(session: requests.Session, event_id: str | None) -> dict[str, Any] | None:
    if not event_id:
        return None
    return _request_json(session, EVENTINFO_URL.format(event_id=event_id))


def _clean_image_url(value: Any) -> str | None:
    text = _clean_text(value)
    if not text or GENERIC_IMAGE_TOKEN in text:
        return None
    return text


def _extract_partner_image(url: str | None) -> str | None:
    link = _clean_text(url)
    if not link:
        return None
    if link in PARTNER_IMAGE_CACHE:
        return PARTNER_IMAGE_CACHE[link]

    image = extract_page_image(
        link,
        headers=HEADERS,
        ignored_tokens=(GENERIC_IMAGE_TOKEN,),
        use_render=True,
    )
    PARTNER_IMAGE_CACHE[link] = image
    return image


def _extract_image(summary: dict[str, Any], detail: dict[str, Any] | None) -> str | None:
    if detail:
        image = _clean_image_url(detail.get("imageUrl"))
        if image:
            return image

    for artist in summary.get("artists") or []:
        image_urls = artist.get("imageUrls") or {}
        image = _clean_image_url(
            image_urls.get("EVENT_DETAIL_PAGE_16_9")
            or image_urls.get("RETINA_PORTRAIT_16_9")
            or image_urls.get("ARTIST_PAGE_3_2")
        )
        if image:
            return image

    venue = detail.get("venue") if detail else None
    image = _clean_image_url((venue or {}).get("imageUrl"))
    if image:
        return image

    image = _clean_image_url((summary.get("venue") or {}).get("imageUrl"))
    if image:
        return image

    host = urlparse(_clean_text(summary.get("url"))).netloc.lower()
    if host and not host.endswith("ticketmaster.es"):
        return _extract_partner_image(summary.get("url"))
    return None


def _extract_description(summary: dict[str, Any], detail: dict[str, Any] | None) -> str:
    if detail:
        description = _clean_text(detail.get("webInfoNoHtml"))
        if description:
            return description

        html_description = detail.get("webInfo")
        if html_description:
            description = _clean_text(BeautifulSoup(str(html_description), "html.parser").get_text(" "))
            if description:
                return description

    return _clean_text(summary.get("title"))


def _build_categories(summary: dict[str, Any], detail: dict[str, Any] | None) -> list[str]:
    categories: list[str] = []

    if detail:
        primary = detail.get("primaryCategory") or {}
        subcategory = detail.get("subCategory") or {}
        categories.extend([
            primary.get("title"),
            subcategory.get("title"),
        ])
        for classification in detail.get("classifications") or []:
            segment = classification.get("segment") or {}
            genre = classification.get("genre") or {}
            sub_genre = classification.get("subGenre") or {}
            categories.extend([
                segment.get("name"),
                genre.get("name"),
                sub_genre.get("name"),
            ])

    major_category = summary.get("majorCategory") or {}
    categories.append(CATEGORY_MAP.get(major_category.get("id")))
    return _dedupe_strings(categories) or ["Otros"]


def _extract_tags(summary: dict[str, Any], detail: dict[str, Any] | None) -> list[str]:
    tags: list[str] = []
    for artist in summary.get("artists") or []:
        tags.append(artist.get("name"))

    if detail:
        for artist in detail.get("artists") or []:
            tags.append(artist.get("name"))

    return _dedupe_strings(tags)


def _build_address(venue: dict[str, Any]) -> str | None:
    parts = _dedupe_strings(
        [
            venue.get("streetAddress") or venue.get("addressLineOne"),
            venue.get("city"),
            venue.get("zip") or venue.get("code"),
        ]
    )
    if parts:
        return ", ".join(parts)
    return None


def _collect_session_values(group: list[dict[str, Any]]) -> list[str]:
    datetimes = _dedupe_strings(
        [(item.get("dates") or {}).get("startDate") for item in group]
    )
    date_values = _dedupe_strings(value.split("T", 1)[0] for value in datetimes if value)

    if len(datetimes) > len(date_values) or len(datetimes) > 10:
        return date_values
    return datetimes


def _extract_record(session: requests.Session, group: list[dict[str, Any]]) -> dict[str, Any] | None:
    summary = _select_representative_event(group)
    url = _clean_text(summary.get("url")) or None
    host = urlparse(url).netloc.lower() if url else ""
    native_ticketmaster = host.endswith("ticketmaster.es") and not (
        summary.get("partnerEvent") or summary.get("isPartner")
    )

    detail = _fetch_detail(session, _clean_text(summary.get("id"))) if native_ticketmaster else None
    detail_venue = (detail or {}).get("venue") or {}
    summary_venue = summary.get("venue") or {}
    venue = detail_venue or summary_venue
    title = _clean_text((detail or {}).get("name") or summary.get("title"))
    if not title:
        return None

    session_values = _collect_session_values(group)
    if not session_values:
        session_values = _dedupe_strings(
            [
                _clean_text(((detail or {}).get("dates") or {}).get("startDate")),
                _clean_text(((detail or {}).get("dates") or {}).get("eventDate")),
            ]
        )
    if not session_values:
        return None

    description = _extract_description(summary, detail)
    native_url = url if host.endswith("ticketmaster.es") else None
    ticketmaster_ids = _dedupe_strings(item.get("id") for item in group)
    discovery_ids = _dedupe_strings(item.get("discoveryId") for item in group)
    origin_type = "partner" if (summary.get("partnerEvent") or summary.get("isPartner")) else "native"

    return {
        "id": ticketmaster_ids[0] if ticketmaster_ids else title,
        "titulo": title,
        "subtitulo": None,
        "descripcion": description,
        "contenido": description,
        "precio": None,
        "moneda": "EUR",
        "lugar": _clean_text(venue.get("name")) or None,
        "direccion": _build_address(venue),
        "latitud": venue.get("latitude") or summary_venue.get("latitude"),
        "longitud": venue.get("longitude") or summary_venue.get("longitude"),
        "fecha_inicio": session_values[0],
        "fecha_fin": session_values[-1],
        "fechas_disponibles": session_values,
        "categorias": _build_categories(summary, detail),
        "etiquetas": _extract_tags(summary, detail),
        "url": native_url or url,
        "url_articulo": url,
        "url_compra": native_url,
        "imagen": _extract_image(summary, detail),
        "fecha_publicacion": _clean_text(((detail or {}).get("dates") or {}).get("onsaleDate")) or None,
        "fuente": SOURCE_NAME,
        "tipo_origen": f"{origin_type}:{host or 'desconocido'}",
        "url_fuente_editorial": url,
    }


def scrape_ticketmaster_madrid() -> list[dict[str, Any]]:
    # cloudscraper: Ticketmaster bloquea requests planos desde IPs de datacenter
    session = cloudscraper.create_scraper()
    session.headers.update(HEADERS)

    raw_events = _collect_raw_events(session)
    if not raw_events:
        # No sobrescribir el último output bueno con una lista vacía: un
        # scrape sin resultados aquí es un fallo, no "no hay eventos".
        raise RuntimeError("No Ticketmaster Madrid events collected")

    grouped = _group_raw_events(raw_events)
    log.info(
        "Ticketmaster grouped %d raw entries into %d candidate plans",
        len(raw_events),
        len(grouped),
    )

    records: list[dict[str, Any]] = []
    for index, group in enumerate(grouped, start=1):
        record = _extract_record(session, group)
        if record:
            records.append(record)
        if index % 20 == 0:
            log.info("Processed %d/%d Ticketmaster groups", index, len(grouped))
        time.sleep(REQUEST_DELAY)

    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d Ticketmaster events to %s", len(normalized), OUTPUT_FILE)
    return normalized


if __name__ == "__main__":
    results = scrape_ticketmaster_madrid()
    native = sum(
        1
        for item in results
        if not _clean_text((item.get("metadata") or {}).get("tipo_origen")).startswith("partner:")
    )
    with_image = sum(1 for item in results if item.get("imagen"))
    with_location = sum(1 for item in results if item.get("lugar") or item.get("direccion"))
    log.info(
        "Summary: %d events, %d native, %d with image, %d with location",
        len(results),
        native,
        with_image,
        with_location,
    )