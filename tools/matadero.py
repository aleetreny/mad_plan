"""Matadero Madrid activities scraper.

Uses the public Drupal JSON:API exposed by Matadero Madrid to fetch current and
upcoming activities with structured dates, categories, institution, and images.

Output: outputs/eventos_matadero.json
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.mataderomadrid.org"
API_URL = f"{BASE_URL}/jsonapi/node/activity"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "eventos_matadero.json"
PAGE_LIMIT = 50
MAX_PAGES = 20
REQUEST_TIMEOUT = 30
UPCOMING_WINDOW_DAYS = 180
MATADERO_ADDRESS = "Plaza de Legazpi, 8, Madrid"
MATADERO_LAT = 40.3915
MATADERO_LON = -3.6996
MADRID_TZ = ZoneInfo("Europe/Madrid")
INCLUDE_PARAM = ",".join(
    (
        "field_category",
        "field_category_md",
        "field_format",
        "field_images",
        "field_institution",
        "field_home_image.image",
        "field_image_galery.image",
    )
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "application/vnd.api+json",
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(unescape(str(value)).replace("\xa0", " ").split())


def _html_to_text(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return _clean_text(BeautifulSoup(text, "html.parser").get_text(" ", strip=True))


def _processed_html_text(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return _html_to_text(value.get("processed"))


def _request_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _build_lookup(included: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for item in included:
        resource_type = item.get("type")
        resource_id = item.get("id")
        if resource_type and resource_id:
            lookup[(resource_type, resource_id)] = item
    return lookup


def _related_resources(
    resource: dict[str, Any],
    relationship_name: str,
    lookup: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rel_data = resource.get("relationships", {}).get(relationship_name, {}).get("data")
    if not rel_data:
        return []
    if isinstance(rel_data, dict):
        rel_data = [rel_data]

    resolved: list[dict[str, Any]] = []
    for ref in rel_data:
        resource_type = ref.get("type")
        resource_id = ref.get("id")
        resource = lookup.get((resource_type, resource_id))
        if resource:
            resolved.append(resource)
    return resolved


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return None


def _parse_price(raw: str | None) -> tuple[float | None, str | None]:
    text = _clean_text(raw).lower()
    if not text:
        return None, None
    if "entrada libre" in text or "gratis" in text or "gratuita" in text:
        return 0.0, "EUR"

    values: list[float] = []
    for match in re.findall(r"\d+(?:[.,]\d+)?", text):
        try:
            values.append(float(match.replace(",", ".")))
        except ValueError:
            continue

    if values:
        return min(values), "EUR"
    return None, "EUR" if "€" in text else None


def _clean_institution_name(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return re.sub(r"\s*\(\d+\)\s*$", "", text).strip() or None


def _extract_categories(resource: dict[str, Any], lookup: dict[tuple[str, str], dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for relationship_name in ("field_category", "field_category_md", "field_format"):
        for related in _related_resources(resource, relationship_name, lookup):
            name = _clean_text(related.get("attributes", {}).get("name"))
            if name and name not in names:
                names.append(name)
    return names or ["Cultura"]


def _extract_institution(resource: dict[str, Any], lookup: dict[tuple[str, str], dict[str, Any]]) -> str | None:
    institutions = _related_resources(resource, "field_institution", lookup)
    if not institutions:
        return _clean_institution_name(resource.get("attributes", {}).get("field_custom_institution"))

    title = _clean_institution_name(institutions[0].get("attributes", {}).get("title"))
    return title or _clean_institution_name(resource.get("attributes", {}).get("field_custom_institution"))


def _extract_media_file_url(
    resource: dict[str, Any],
    relationship_name: str,
    lookup: dict[tuple[str, str], dict[str, Any]],
) -> str | None:
    for media in _related_resources(resource, relationship_name, lookup):
        media_image = media.get("relationships", {}).get("image", {}).get("data")
        if not media_image:
            continue
        if isinstance(media_image, list):
            media_image = media_image[0] if media_image else None
        if not isinstance(media_image, dict):
            continue
        file_resource = lookup.get((media_image.get("type"), media_image.get("id")))
        if not file_resource:
            continue
        uri = file_resource.get("attributes", {}).get("uri", {}).get("url")
        if uri:
            return urljoin(BASE_URL, uri)
    return None


def _extract_image(resource: dict[str, Any], lookup: dict[tuple[str, str], dict[str, Any]]) -> str | None:
    images = _related_resources(resource, "field_images", lookup)
    if images:
        uri = images[0].get("attributes", {}).get("uri", {}).get("url")
        if uri:
            return urljoin(BASE_URL, uri)

    home_image = _extract_media_file_url(resource, "field_home_image", lookup)
    if home_image:
        return home_image

    gallery_image = _extract_media_file_url(resource, "field_image_galery", lookup)
    if gallery_image:
        return gallery_image

    return None


def _extract_event_url(attributes: dict[str, Any]) -> str:
    alias = attributes.get("path", {}).get("alias")
    if alias:
        return urljoin(BASE_URL, alias)
    nid = attributes.get("drupal_internal__nid")
    return f"{BASE_URL}/node/{nid}"


def _extract_purchase_url(attributes: dict[str, Any]) -> str | None:
    for field_name in ("field_buy_url", "field_ticketing_links"):
        field_value = attributes.get(field_name)
        if isinstance(field_value, list):
            for item in field_value:
                if not isinstance(item, dict):
                    continue
                uri = item.get("uri")
                if uri:
                    return uri
        elif isinstance(field_value, dict):
            uri = field_value.get("uri")
            if uri:
                return uri
    return None


def _extract_info_url(attributes: dict[str, Any]) -> str | None:
    for field_name in ("field_info_link", "field_url_original"):
        field_value = attributes.get(field_name)
        if isinstance(field_value, list):
            for item in field_value:
                if not isinstance(item, dict):
                    continue
                uri = item.get("uri")
                if uri:
                    return uri
        elif isinstance(field_value, dict):
            uri = field_value.get("uri")
            if uri:
                return uri
    return None


def _extract_sessions(attributes: dict[str, Any]) -> list[str]:
    values: list[str] = []
    occurrences = attributes.get("field_ocurrences") or []
    if isinstance(occurrences, list):
        for item in occurrences:
            if not isinstance(item, dict):
                continue
            value = _clean_text(item.get("value"))
            if value and value not in values:
                values.append(value)

    if values:
        return values

    field_dates = attributes.get("field_dates") or []
    if isinstance(field_dates, list):
        for value in field_dates:
            cleaned = _clean_text(value)
            if cleaned and cleaned not in values:
                values.append(cleaned)

    return values


def _matadero_place_hint(place: str | None) -> bool | None:
    place_text = _clean_text(place).casefold()
    if not place_text:
        return None

    if any(marker in place_text for marker in ("movistar koi",)):
        return False

    if any(
        marker in place_text
        for marker in (
            "matadero",
            "cineteca",
            "nave",
            "casa del lector",
            "centro danza",
            "auditorio",
            "nube",
            "aulas",
            "archivo",
            "cantina",
            "vestibulo",
            "vestíbulo",
            "patio",
            "punto de información",
            "paseo de la chopera",
        )
    ):
        return True

    return None


def _should_assign_matadero_coords(
    institution: str | None,
    external_url: str | None,
    place: str | None,
) -> bool:
    place_hint = _matadero_place_hint(place)
    if place_hint is not None:
        return place_hint

    institution_text = _clean_text(institution).casefold()
    if any(
        marker in institution_text
        for marker in (
            "matadero",
            "cineteca",
            "casa del lector",
            "nave 10",
            "naves del español",
            "centro danza",
            "intermediae",
        )
    ):
        return True
    if external_url and any(
        host_fragment in external_url
        for host_fragment in (
            "mataderomadrid.org",
            "cinetecamadrid.com",
            "nave10matadero.es",
            "centrodanzamatadero.es",
            "casalector.fundaciongsr.org",
        )
    ):
        return True
    return False


def _fetch_all_activities() -> list[dict[str, Any]]:
    activities: list[dict[str, Any]] = []
    next_url: str | None = API_URL
    window_start = datetime.now(MADRID_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(days=UPCOMING_WINDOW_DAYS)
    params: dict[str, Any] | None = {
        "page[limit]": PAGE_LIMIT,
        "sort": "field_end_date",
        "include": INCLUDE_PARAM,
        "filter[end_date_min][condition][path]": "field_end_date",
        "filter[end_date_min][condition][operator]": ">=",
        "filter[end_date_min][condition][value]": window_start.isoformat(timespec="seconds"),
        "filter[start_date_max][condition][path]": "field_init_date",
        "filter[start_date_max][condition][operator]": "<=",
        "filter[start_date_max][condition][value]": window_end.isoformat(timespec="seconds"),
    }
    page = 1
    seen_urls: set[str] = set()

    log.info(
        "Matadero window: end_date >= %s and init_date <= %s",
        window_start.isoformat(timespec="seconds"),
        window_end.isoformat(timespec="seconds"),
    )

    while next_url:
        if next_url in seen_urls:
            log.warning("Stopping Matadero pagination because next URL repeated")
            break
        seen_urls.add(next_url)

        payload = _request_json(next_url, params=params)
        params = None

        included = payload.get("included") or []
        lookup = _build_lookup(included)
        for resource in payload.get("data") or []:
            activities.append({"resource": resource, "lookup": lookup})

        log.info("Fetched Matadero page %d: %d activities", page, len(payload.get("data") or []))
        next_url = payload.get("links", {}).get("next", {}).get("href")
        if page >= MAX_PAGES and next_url:
            log.warning("Stopping Matadero after %d pages as a safety guard", MAX_PAGES)
            break
        page += 1

    return activities


def scrape_matadero() -> list[dict[str, Any]]:
    log.info("Fetching Matadero Madrid activities via JSON:API …")
    raw_items = _fetch_all_activities()
    log.info("Raw Matadero activities: %d", len(raw_items))

    events: list[dict[str, Any]] = []
    for item in raw_items:
        resource = item["resource"]
        lookup = item["lookup"]
        attributes = resource.get("attributes", {})

        # The JSON:API also returns the English translation of each activity
        # (alias under /schedule/); keep only the Spanish edition.
        alias = (attributes.get("path") or {}).get("alias") or ""
        langcode = attributes.get("langcode")
        if langcode == "en" or alias.startswith("/schedule/"):
            continue

        institution = _extract_institution(resource, lookup)
        purchase_url = _extract_purchase_url(attributes)
        info_url = _extract_info_url(attributes)
        place_data = attributes.get("field_place") or {}
        price_data = attributes.get("field_price") or {}
        place = _first_non_empty(
            _processed_html_text(place_data),
            institution,
            "Matadero Madrid",
        )
        use_matadero_coords = _should_assign_matadero_coords(institution, purchase_url or info_url, place)

        description = _first_non_empty(
            _processed_html_text(attributes.get("body")),
            _processed_html_text(attributes.get("field_teaser")),
            _processed_html_text(attributes.get("field_timetable")),
            _clean_text(attributes.get("field_friendly_date")),
        ) or ""

        price_text = _processed_html_text(price_data)
        price, currency = _parse_price(price_text)

        technical_data = _processed_html_text(attributes.get("field_technicaldata"))
        if technical_data:
            description = f"{description} {technical_data}".strip()

        metadata = {
            "activity_type": _clean_text(attributes.get("field_activity_type")) or None,
            "friendly_date": _clean_text(attributes.get("field_friendly_date")) or None,
            "institution": institution,
            "original_url": info_url,
            "price_text": price_text or None,
            "ticketing_visible": attributes.get("field_ticketing_visible"),
            "send_madrid_es": attributes.get("field_send_madrid_es"),
        }

        events.append(
            {
                "id": str(attributes.get("drupal_internal__nid") or resource.get("id") or ""),
                "titulo": _clean_text(attributes.get("title")),
                "subtitulo": _clean_text(attributes.get("field_subtitle")),
                "descripcion": description,
                "contenido": description,
                "precio": price,
                "moneda": currency,
                "lugar": place,
                "direccion": MATADERO_ADDRESS if use_matadero_coords else None,
                "latitud": MATADERO_LAT if use_matadero_coords else None,
                "longitud": MATADERO_LON if use_matadero_coords else None,
                "fecha_inicio": _clean_text(attributes.get("field_init_date")) or None,
                "fecha_fin": _clean_text(attributes.get("field_end_date")) or None,
                "fechas_disponibles": _extract_sessions(attributes),
                "categorias": _extract_categories(resource, lookup),
                "url": _extract_event_url(attributes),
                "url_articulo": _extract_event_url(attributes),
                "url_compra": purchase_url,
                "imagen": _extract_image(resource, lookup),
                "fecha_publicacion": _clean_text(attributes.get("created")) or None,
                "fecha_actualizacion": _clean_text(attributes.get("changed")) or None,
                "fuente": "matadero",
                "metadata": metadata,
            }
        )

    events = normalize_plan_records(events, source="matadero")

    OUTPUT_FILE.write_text(
        json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d Matadero events to %s", len(events), OUTPUT_FILE)
    return events


if __name__ == "__main__":
    results = scrape_matadero()
    with_price = sum(1 for event in results if event.get("precio") is not None)
    with_coords = sum(1 for event in results if event.get("latitud") is not None)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(results),
        with_coords,
        with_price,
    )