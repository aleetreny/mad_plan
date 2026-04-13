"""RockTheSport Madrid sports-event scraper.

Uses RockTheSport's public REST API to discover sporting events in Madrid
(running, trail, cycling, triathlon, etc.) and enrich each item from its
detail endpoint.

Output: outputs/eventos_rockthesport.json
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

API_BASE = "https://publicservice.rockthesport.com"
API_KEY = "rts_public_web_2024_a8f3d9e1c4b7"
COUNTRY_ID_SPAIN = 65
PROVINCE_ID_MADRID = 61
PAGE_SIZE = 200
MAX_PAGES = 20
REQUEST_TIMEOUT = 20
SOURCE_NAME = "rockthesport"
MADRID_TZ = ZoneInfo("Europe/Madrid")
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "outputs" / "eventos_rockthesport.json"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "es-ES,es;q=0.9",
    "X-API-Key": API_KEY,
}
WEB_BASE = "https://web.rockthesport.com"

# ── sport → category mapping ────────────────────────────────────────────
SPORT_CATEGORIES: dict[str, list[str]] = {
    "running": ["Deportes", "Running"],
    "trail running": ["Deportes", "Trail Running"],
    "trail": ["Deportes", "Trail Running"],
    "ciclismo": ["Deportes", "Ciclismo"],
    "cycling": ["Deportes", "Ciclismo"],
    "triatlón": ["Deportes", "Triatlón"],
    "triathlon": ["Deportes", "Triatlón"],
    "duathlon": ["Deportes", "Duatlón"],
    "duatlón": ["Deportes", "Duatlón"],
    "acuatlon": ["Deportes", "Acuatlón"],
    "acuatlón": ["Deportes", "Acuatlón"],
    "natación": ["Deportes", "Natación"],
    "swimming": ["Deportes", "Natación"],
    "marcha nórdica": ["Deportes", "Marcha Nórdica"],
    "senderismo": ["Deportes", "Senderismo"],
    "hiking": ["Deportes", "Senderismo"],
    "obstáculos": ["Deportes", "Carreras de Obstáculos"],
    "ocr": ["Deportes", "Carreras de Obstáculos"],
    "crossfit": ["Deportes", "Cross Training"],
    "tennis": ["Deportes", "Tenis"],
    "pickleball": ["Deportes", "Pickleball"],
    "chess": ["Deportes", "Ajedrez"],
    "other": ["Deportes"],
}
ONLINE_EVENT_HINTS = (
    "online",
    "on line",
    "on-line",
    "streaming",
    "zoom",
    "virtual",
)
NON_PLAN_TITLE_HINTS = (
    "juez ",
    "jueza ",
    "árbitro",
    "arbitro",
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


def _request_json(
    session: requests.Session, url: str, *, params: dict[str, Any] | None = None
) -> Any:
    response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _build_event_url(event_id: int | str) -> str:
    return f"{WEB_BASE}/event/{event_id}"


def _sport_categories(sport_raw: str | None) -> list[str]:
    if not sport_raw:
        return ["Deportes"]
    key = _clean_text(sport_raw).casefold()
    return SPORT_CATEGORIES.get(key, ["Deportes", _clean_text(sport_raw).title()])


def _build_location(detail: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return (venue_name, address_string)."""
    parts_name: list[str] = []
    parts_address: list[str] = []

    place = _clean_text(detail.get("place"))
    address = _clean_text(detail.get("address"))
    city = _clean_text(detail.get("city"))
    province = _clean_text(detail.get("province"))

    if place:
        parts_name.append(place)
    if city and city.casefold() != (place or "").casefold():
        parts_name.append(city)

    if address:
        parts_address.append(address)
    if city:
        parts_address.append(city)
    if province and province.casefold() != (city or "").casefold():
        parts_address.append(province)

    venue = ", ".join(parts_name) or None
    full_address = ", ".join(parts_address) or venue
    return venue, full_address


def _parse_iso(raw: Any) -> str | None:
    text = _clean_text(raw)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.astimezone(MADRID_TZ).isoformat()
    except ValueError:
        return text


def _extract_price(detail: dict[str, Any]) -> float | None:
    for key in ("price", "minPrice", "registrationPrice"):
        val = detail.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def _extract_image(detail: dict[str, Any], summary: dict[str, Any]) -> str | None:
    for source in (detail, summary):
        for key in ("bannerUrl", "imageUrl", "image", "banner"):
            url = _clean_text(source.get(key))
            if url and url.startswith("http"):
                return url
    return None


def _is_online_event(title: str, venue: str | None, address: str | None, detail: dict[str, Any]) -> bool:
    combined = " ".join(
        _clean_text(value)
        for value in (
            title,
            venue,
            address,
            detail.get("subtitle"),
            detail.get("description"),
            detail.get("place"),
            detail.get("address"),
            detail.get("city"),
        )
        if value
    ).casefold()
    return any(token in combined for token in ONLINE_EVENT_HINTS)


def _is_non_consumer_event(
    title: str, venue: str | None, address: str | None, detail: dict[str, Any]
) -> bool:
    title_text = _clean_text(title).casefold()
    if any(token in title_text for token in NON_PLAN_TITLE_HINTS):
        return True

    combined = " ".join(
        _clean_text(value)
        for value in (
            title,
            venue,
            address,
            detail.get("subtitle"),
            detail.get("description"),
            detail.get("regulations"),
        )
        if value
    ).casefold()
    return "curso de juez" in combined or "formacion de jueces" in combined or "formación de jueces" in combined


def _clean_purchase_url(raw_url: Any) -> str | None:
    text = _clean_text(raw_url)
    if not text:
        return None

    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return text


# ── discovery ────────────────────────────────────────────────────────────

def _discover_madrid_events(session: requests.Session) -> list[dict[str, Any]]:
    """Paginate the event list and keep only Madrid (provinceId=61) items."""
    all_items: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for page in range(1, MAX_PAGES + 1):
        payload = _request_json(
            session,
            f"{API_BASE}/api/Event/list",
            params={
                "pageNumber": page,
                "pageSize": PAGE_SIZE,
                "countryId": COUNTRY_ID_SPAIN,
            },
        )
        items = (payload.get("data") or {}).get("items") or []
        if not items:
            break

        for item in items:
            if item.get("provinceId") != PROVINCE_ID_MADRID:
                continue
            event_id = item.get("eventId")
            if event_id and event_id not in seen_ids:
                seen_ids.add(event_id)
                all_items.append(item)

        log.info(
            "RockTheSport page %d: %d total items, %d Madrid cumul",
            page,
            len(items),
            len(all_items),
        )

    return all_items


# ── detail enrichment ────────────────────────────────────────────────────

def _fetch_detail(
    session: requests.Session, event_id: int
) -> dict[str, Any] | None:
    try:
        payload = _request_json(
            session, f"{API_BASE}/api/Event/es/general/{event_id}"
        )
        return payload.get("data") or payload
    except Exception as exc:
        log.warning("RockTheSport detail %s failed: %s", event_id, exc)
        return None


def _extract_record(
    summary: dict[str, Any], detail: dict[str, Any]
) -> dict[str, Any] | None:
    event_id = detail.get("eventId") or summary.get("eventId")
    title = _clean_text(detail.get("name") or summary.get("title"))
    if not title:
        return None

    sport = _clean_text(detail.get("sport") or summary.get("sport"))
    categories = _sport_categories(sport)
    venue, address = _build_location(detail)
    if _is_online_event(title, venue, address, detail):
        return None
    if _is_non_consumer_event(title, venue, address, detail):
        return None

    start_iso = _parse_iso(
        detail.get("eventStartDate")
        or detail.get("startedDateIso")
        or summary.get("startedDateIso")
    )
    end_iso = _parse_iso(
        detail.get("eventEndDate")
        or detail.get("finishedDateIso")
        or summary.get("finishedDateIso")
    )
    registration_start = _parse_iso(detail.get("registrationStartDate"))
    registration_end = _parse_iso(detail.get("registrationEndDate"))
    raw_registration_url = _clean_text(detail.get("registrationUrl")) or None
    purchase_url = _clean_purchase_url(raw_registration_url)

    price = _extract_price(detail)
    image = _extract_image(detail, summary)
    event_url = _build_event_url(event_id)

    # Build tags from sport + modality + distance info
    tags: list[str] = []
    if sport:
        tags.append(sport)
    for key in ("modality", "distance", "distanceUnit"):
        val = _clean_text(detail.get(key))
        if val:
            tags.append(val)

    description_parts: list[str] = []
    desc = _clean_text(detail.get("description"))
    if desc:
        description_parts.append(desc)
    regulations = _clean_text(detail.get("regulations"))
    if regulations and regulations != desc:
        description_parts.append(regulations)
    description = " ".join(description_parts) or title

    return {
        "id": str(event_id),
        "titulo": title,
        "subtitulo": _clean_text(detail.get("subtitle")) or sport or None,
        "descripcion": description,
        "contenido": description,
        "categorias": categories,
        "etiquetas": _dedupe_strings(tags),
        "lugar": venue,
        "direccion": address,
        "latitud": detail.get("latitude") or summary.get("latitude"),
        "longitud": detail.get("longitude") or summary.get("longitude"),
        "precio": price,
        "moneda": "EUR" if price is not None else None,
        "fecha_inicio": start_iso,
        "fecha_fin": end_iso or start_iso,
        "fechas_disponibles": _dedupe_strings([start_iso, end_iso]),
        "url": event_url,
        "url_articulo": event_url,
        "url_compra": purchase_url,
        "imagen": image,
        "fecha_publicacion": _parse_iso(detail.get("createdDate")),
        "fecha_actualizacion": _parse_iso(detail.get("modifiedDate")),
        "fuente": SOURCE_NAME,
        "metadata": {
            "rts_event_id": event_id,
            "sport": sport,
            "province_id": detail.get("provinceId") or summary.get("provinceId"),
            "registration_start": registration_start,
            "registration_end": registration_end,
            "max_participants": detail.get("maxParticipants"),
            "current_participants": detail.get("currentParticipants"),
            "registration_url_invalid": raw_registration_url if raw_registration_url and not purchase_url else None,
            "status": _clean_text(detail.get("status")) or None,
        },
    }


# ── main ─────────────────────────────────────────────────────────────────

def scrape_rockthesport() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    summaries = _discover_madrid_events(session)
    log.info("Discovered %d RockTheSport Madrid events", len(summaries))

    records: list[dict[str, Any]] = []
    for idx, summary in enumerate(summaries, 1):
        event_id = summary.get("eventId")
        if not event_id:
            continue
        log.info(
            "Fetching RockTheSport detail %d/%d: %s",
            idx,
            len(summaries),
            summary.get("title", event_id),
        )
        detail = _fetch_detail(session, event_id)
        if not detail:
            continue
        record = _extract_record(summary, detail)
        if record:
            records.append(record)

    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info(
        "Saved %d RockTheSport Madrid events to %s", len(normalized), OUTPUT_FILE
    )
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(normalized),
        sum(1 for r in normalized if r.get("latitud") is not None),
        sum(1 for r in normalized if r.get("precio") is not None),
    )
    return normalized


if __name__ == "__main__":
    scrape_rockthesport()
