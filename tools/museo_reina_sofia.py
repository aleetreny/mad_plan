"""Museo Reina Sofia activities scraper.

Uses the public search API behind the museum's site for discovery and Gatsby
page-data JSON for each activity detail page.

Output: outputs/eventos_museo_reina_sofia.json
"""

from __future__ import annotations

import html
import json
import logging
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.museoreinasofia.es"
RESOURCES_BASE_URL = "https://recursos.museoreinasofia.es"
SEARCH_API_URL = "https://buscador.museoreinasofia.es/api/search"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "outputs"
    / "eventos_museo_reina_sofia.json"
)
SOURCE_NAME = "museo_reina_sofia"
REQUEST_TIMEOUT = 30
SEARCH_RESULTS_PER_PAGE = 12
MAX_SEARCH_PAGES = 250
MIN_PAGES_BEFORE_STOP = 20
MAX_CONSECUTIVE_EMPTY_FUTURE_PAGES = 15
VENUE_NAME = "Museo Reina Sofia"
VENUE_ADDRESS = "C. Santa Isabel, 52, 28012 Madrid"
PRICE_RE = re.compile(r"(?:€\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*€)")
MAILTO_RE = re.compile(r"mailto:[^\s\"'>]+")
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


def _strip_html(value: Any) -> str:
    text = html.unescape(str(value or ""))
    return _clean_text(BeautifulSoup(text, "html.parser").get_text(" ", strip=True))


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


def _clean_category_value(value: Any) -> str | None:
    text = _clean_text(value)
    if not text or text.isdigit():
        return None
    return text


def _request_json(session: requests.Session, url: str) -> Any:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _timestamp_to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    return (
        datetime.fromtimestamp(timestamp, timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _page_data_url(path: str) -> str:
    clean_path = "/" + path.strip("/")
    return f"{BASE_URL}/page-data{clean_path}/page-data.json"


def _extract_future_candidate_dates(search_item: dict[str, Any]) -> list[str]:
    dates: list[str] = []
    for entry in search_item.get("processedDates") or []:
        value = _clean_text(entry.get("value"))
        if value:
            dates.append(value)
    return _dedupe_strings(dates)


def _is_future_search_item(search_item: dict[str, Any], *, today: date) -> bool:
    for value in _extract_future_candidate_dates(search_item):
        try:
            if datetime.fromisoformat(value).date() >= today:
                return True
        except ValueError:
            continue
    return _clean_text(search_item.get("template")) == "future"


def _extract_search_candidates(session: requests.Session) -> list[dict[str, Any]]:
    today = date.today()
    candidates_by_path: dict[str, dict[str, Any]] = {}
    consecutive_without_future = 0
    last_future_page = 0

    for page in range(1, MAX_SEARCH_PAGES + 1):
        url = f"{SEARCH_API_URL}?bundle=activity&type=activity&page={page}"
        payload = _request_json(session, url)
        results = payload.get("results") or []
        if not results:
            break

        page_has_future = False
        for item in results:
            path = _clean_text((item.get("url") or {}).get("path"))
            if not path or not path.startswith("/actividad/"):
                continue
            if not _is_future_search_item(item, today=today):
                continue
            page_has_future = True
            last_future_page = page
            candidates_by_path[path] = item

        if page_has_future:
            consecutive_without_future = 0
        else:
            consecutive_without_future += 1

        if (
            page >= MIN_PAGES_BEFORE_STOP
            and consecutive_without_future >= MAX_CONSECUTIVE_EMPTY_FUTURE_PAGES
        ):
            break

    log.info(
        "Museo Reina Sofia discovery scanned %d pages and found %d future candidate activities",
        max(last_future_page + consecutive_without_future, len(candidates_by_path) // SEARCH_RESULTS_PER_PAGE + 1),
        len(candidates_by_path),
    )
    return list(candidates_by_path.values())


def _extract_categories(content: dict[str, Any], search_item: dict[str, Any]) -> list[str]:
    categories: list[str] = []
    for entry in content.get("categories") or []:
        category = _clean_category_value(
            _clean_text((((entry or {}).get("entity") or {}).get("title")))
            or _clean_text((((entry or {}).get("entity") or {}).get("name")))
        )
        if category:
            categories.append(category)

    parent = (content.get("parent") or {}).get("entity") or {}
    for entry in parent.get("categories") or []:
        category = _clean_category_value(
            _clean_text((((entry or {}).get("entity") or {}).get("title")))
            or _clean_text((((entry or {}).get("entity") or {}).get("name")))
        )
        if category:
            categories.append(category)

    for value in search_item.get("processedCategories") or []:
        category = _clean_category_value(value)
        if category:
            categories.append(category)

    if categories:
        return _dedupe_strings(categories)
    return _infer_categories(content)


def _infer_categories(content: dict[str, Any]) -> list[str]:
    title = _strip_html((content.get("title") or {}).get("value"))
    subtitle = _strip_html((content.get("subtitle") or {}).get("value"))
    description = _strip_html((content.get("description") or {}).get("value"))
    more_information = _strip_html((content.get("moreInformation") or {}).get("value"))
    useful_information = _strip_html((content.get("usefulInformation") or {}).get("value"))
    location = _extract_location(content) or ""
    tags = " ".join(_extract_tags(content))
    blob = " ".join(
        part
        for part in (
            title,
            subtitle,
            description,
            more_information,
            useful_information,
            location,
            tags,
        )
        if part
    )
    normalized = blob.casefold()

    inferred: list[str] = []
    if any(token in normalized for token in ("visita guiada", "visita a la biblioteca")):
        inferred.append("Visita comentada")
    elif any(token in normalized for token in ("recorrido", "punto de encuentro")) and any(
        token in normalized for token in ("educación", "educacion", "infantil", "visita")
    ):
        inferred.append("Visita comentada")

    if any(
        token in normalized
        for token in (
            "biblioteca",
            "bookcrossing",
            "día internacional del libro",
            "dia internacional del libro",
            "libro",
            "libros e ideas",
        )
    ):
        inferred.append("Investigación")

    return _dedupe_strings(inferred)


def _extract_tags(content: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field in ("audiences", "targetedAudiences", "characteristics"):
        for entry in content.get(field) or []:
            entity = (entry or {}).get("entity") or {}
            values.append(_clean_text(entity.get("title")) or _clean_text(entity.get("name")))
    return _dedupe_strings(values)


def _extract_image_url(content: dict[str, Any]) -> str | None:
    entity = ((content.get("mainMedia") or {}).get("entity") or {})
    image = entity.get("image") or {}
    original_src = _clean_text(image.get("originalSrc"))
    if not original_src:
        return None
    return urljoin(RESOURCES_BASE_URL, original_src)


def _extract_dates(content: dict[str, Any], search_item: dict[str, Any]) -> list[str]:
    dates: list[str] = []

    for event in content.get("events") or []:
        entity = (event or {}).get("entity") or {}
        for entry in entity.get("dates") or []:
            event_entity = (entry or {}).get("entity") or {}
            value = event_entity.get("date")
            if value in (None, ""):
                continue
            try:
                dates.append(datetime.fromtimestamp(int(value)).isoformat())
            except (TypeError, ValueError, OSError):
                continue

    if not dates:
        for entry in content.get("schedule") or []:
            entity = (entry or {}).get("entity") or {}
            value = entity.get("date")
            if value in (None, ""):
                continue
            try:
                dates.append(datetime.fromtimestamp(int(value)).isoformat())
            except (TypeError, ValueError, OSError):
                continue

    if not dates:
        dates.extend(_extract_future_candidate_dates(search_item))

    return _dedupe_strings(sorted(dates))


def _extract_location(content: dict[str, Any]) -> str | None:
    for event in content.get("events") or []:
        entity = (event or {}).get("entity") or {}
        location = ((entity.get("location") or {}).get("entity") or {})
        value = _clean_text(location.get("title")) or _clean_text(location.get("name"))
        if value:
            return value
    return VENUE_NAME


def _extract_address(location: str | None) -> str | None:
    if not location:
        return VENUE_ADDRESS
    if any(token in location.casefold() for token in ("sabatini", "nouvel", "biblioteca")):
        return VENUE_ADDRESS
    return VENUE_ADDRESS


def _extract_ticket_records(content: dict[str, Any]) -> list[dict[str, Any]]:
    tickets: list[dict[str, Any]] = []
    for entry in content.get("tickets") or []:
        entity = (entry or {}).get("entity") or {}
        tickets.append(entity)
    return tickets


def _extract_booking_url(content: dict[str, Any], detail_fragments: list[str]) -> str | None:
    for ticket in _extract_ticket_records(content):
        path = _clean_text((((ticket.get("url") or {}).get("url") or {}).get("path")))
        if path.startswith("http") or path.startswith("mailto:"):
            return path

    for fragment in detail_fragments:
        soup = BeautifulSoup(str(fragment or ""), "html.parser")
        anchor = soup.select_one('a[href]')
        if anchor:
            href = _clean_text(anchor.get("href"))
            if href.startswith(("http", "mailto:")):
                return href
        mail_match = MAILTO_RE.search(str(fragment or ""))
        if mail_match:
            return mail_match.group(0)
    return None


def _extract_price(content: dict[str, Any], detail_fragments: list[str]) -> float | None:
    combined_text = "\n".join(_strip_html(fragment) for fragment in detail_fragments if fragment)

    values: list[float] = []
    for match in PRICE_RE.finditer(combined_text):
        raw_value = match.group(1) or match.group(2)
        if not raw_value:
            continue
        try:
            values.append(float(raw_value.replace(",", ".")))
        except ValueError:
            continue

    if values:
        return min(values)

    free_markers = [
        _clean_text(ticket.get("urlTitle")) + " " + _strip_html((ticket.get("help") or {}).get("value"))
        for ticket in _extract_ticket_records(content)
    ]
    if any(token in marker.casefold() for marker in free_markers for token in ("gratuit", "libre hasta completar aforo", "entrada libre")):
        return 0.0
    return None


def _extract_capacity(content: dict[str, Any]) -> str | None:
    for event in content.get("events") or []:
        entity = (event or {}).get("entity") or {}
        value = _clean_text(entity.get("capacity"))
        if value:
            return value
    return None


def _extract_record(session: requests.Session, search_item: dict[str, Any]) -> dict[str, Any] | None:
    path = _clean_text((search_item.get("url") or {}).get("path"))
    if not path:
        return None

    payload = _request_json(session, _page_data_url(path))
    content = (((payload.get("result") or {}).get("pageContext") or {}).get("node") or {}).get("data", {}).get("content", {})
    if not content:
        return None

    description_html = ((content.get("description") or {}).get("value"))
    more_information_html = ((content.get("moreInformation") or {}).get("value"))
    useful_information_html = ((content.get("usefulInformation") or {}).get("value"))
    notice_html = ((content.get("notice") or {}).get("value"))
    detail_fragments = [
        description_html,
        more_information_html,
        useful_information_html,
        notice_html,
        *[((ticket.get("help") or {}).get("value")) for ticket in _extract_ticket_records(content)],
    ]

    title = _strip_html((content.get("title") or {}).get("value"))
    subtitle = _strip_html((content.get("subtitle") or {}).get("value")) or None
    description = _strip_html(description_html) or subtitle
    content_text = "\n\n".join(
        part for part in (_strip_html(description_html), _strip_html(useful_information_html), _strip_html(more_information_html)) if part
    ) or description
    dates = _extract_dates(content, search_item)
    location = _extract_location(content)
    address = _extract_address(location)
    booking_url = _extract_booking_url(content, detail_fragments)
    categories = _extract_categories(content, search_item)
    tags = _extract_tags(content)

    return {
        "id": _clean_text(content.get("id")) or path.strip("/").split("/")[-1],
        "titulo": title,
        "subtitulo": subtitle,
        "descripcion": description,
        "contenido": content_text,
        "precio": _extract_price(content, detail_fragments),
        "moneda": "EUR",
        "lugar": location,
        "direccion": address,
        "fecha_inicio": dates[0] if dates else None,
        "fecha_fin": dates[-1] if dates else None,
        "fechas_disponibles": dates,
        "categorias": categories,
        "etiquetas": tags,
        "url": urljoin(BASE_URL, path),
        "url_compra": booking_url,
        "imagen": _extract_image_url(content),
        "fecha_publicacion": _timestamp_to_iso(content.get("created")),
        "fecha_actualizacion": _timestamp_to_iso(content.get("changed")),
        "metadata": {
            "search_template": _clean_text(search_item.get("template")) or None,
            "is_accessible": bool(content.get("isAccessible")),
            "organizer": _strip_html((content.get("organizer") or {}).get("value")) or None,
            "capacity": _extract_capacity(content),
            "ticket_count": len(_extract_ticket_records(content)),
        },
    }


def _drop_shared_booking_urls(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(record.get("url_compra") for record in records if record.get("url_compra"))
    for record in records:
        booking_url = record.get("url_compra")
        if not booking_url or counts[booking_url] <= 1:
            continue
        record.setdefault("metadata", {})["shared_booking_url"] = booking_url
        record["url_compra"] = None
    return records


def scrape_museo_reina_sofia() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    candidates = _extract_search_candidates(session)
    records: list[dict[str, Any]] = []

    for index, item in enumerate(candidates, start=1):
        path = _clean_text((item.get("url") or {}).get("path"))
        try:
            log.info(
                "Fetching Museo Reina Sofia detail %d/%d: %s",
                index,
                len(candidates),
                path,
            )
            record = _extract_record(session, item)
        except Exception as error:
            log.warning("Skipping Museo Reina Sofia item %s: %s", path, error)
            continue
        if record:
            records.append(record)

    records = _drop_shared_booking_urls(records)
    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d Museo Reina Sofia events to %s", len(normalized), OUTPUT_FILE)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(normalized),
        sum(1 for item in normalized if item.get("latitud") is not None),
        sum(1 for item in normalized if item.get("precio") is not None),
    )
    return normalized


if __name__ == "__main__":
    scrape_museo_reina_sofia()