"""Meetup Madrid community-events scraper.

Uses Meetup's GraphQL (gql2) endpoint to discover community events near Madrid
and paginates through all available results.

Output: outputs/eventos_meetup.json
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

GQL_URL = "https://www.meetup.com/gql2"
FIND_PAGE = "https://www.meetup.com/find/?location=es--Madrid&source=EVENTS"
MADRID_LAT = 40.42
MADRID_LON = -3.71
PAGE_SIZE = 50
MAX_PAGES = 10
REQUEST_TIMEOUT = 20
SOURCE_NAME = "meetup"
MADRID_TZ = ZoneInfo("Europe/Madrid")
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "outputs" / "eventos_meetup.json"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
    "Content-Type": "application/json",
}
ONLINE_EVENT_HINTS = (
    "online event",
    "online-only",
    "virtual event",
    "virtual",
    "livestream",
    "streamyard",
    "zoom",
    "google meet",
    "meet.google",
    "microsoft teams",
)

# ── GraphQL query ────────────────────────────────────────────────────────

RECOMMENDED_EVENTS_QUERY_TPL = """
query($first: Int, $after: String) {{
  recommendedEvents(filter: {{
    lat: {lat}
    lon: {lon}
    startDateRange: "{start_date}"
  }}, first: $first, after: $after) {{
    totalCount
    pageInfo {{
      hasNextPage
      endCursor
    }}
    edges {{
      node {{
        id
        title
        dateTime
        eventUrl
        eventType
        description
        venue {{
          name
          address
          city
          country
          lat
          lon
        }}
        group {{
          name
          urlname
        }}
        featuredEventPhoto {{
          highResUrl
          baseUrl
        }}
        feeSettings {{
          amount
          currency
        }}
        rsvps {{
          totalCount
        }}
        maxTickets
        rsvpState
      }}
    }}
  }}
}}
"""


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


def _strip_html(html: str) -> str:
    """Remove HTML tags for plain-text description."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"')
    return " ".join(text.split())


def _parse_iso(raw: Any) -> str | None:
    text = _clean_text(raw)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.astimezone(MADRID_TZ).isoformat()
    except ValueError:
        return text


def _is_madrid_area(node: dict[str, Any]) -> bool:
    """Filter out online-only events not related to Madrid."""
    venue = node.get("venue") or {}
    lat = venue.get("lat")

    # Online events with lat far from Madrid (e.g. -8.x) → skip
    if lat is not None:
        try:
            if abs(float(lat) - MADRID_LAT) > 2.0:
                return False
        except (TypeError, ValueError):
            pass

    city = _clean_text(venue.get("city")).casefold()
    if city and "madrid" not in city and lat is None:
        return False

    return True


def _is_online_event(node: dict[str, Any]) -> bool:
    venue = node.get("venue") or {}
    combined = " ".join(
        _clean_text(value)
        for value in (
            node.get("eventType"),
            venue.get("name"),
            venue.get("address"),
            venue.get("city"),
        )
        if value
    ).casefold()
    if combined and any(token in combined for token in ONLINE_EVENT_HINTS):
        return True

    if combined:
        return False

    fallback = " ".join(
        _clean_text(value)
        for value in (node.get("title"), node.get("description"))
        if value
    ).casefold()
    return any(token in fallback for token in ONLINE_EVENT_HINTS if token != "virtual")


def _infer_categories(node: dict[str, Any]) -> list[str]:
    """Infer categories from event type and group context."""
    title = _clean_text(node.get("title")).casefold()
    group_name = _clean_text((node.get("group") or {}).get("name")).casefold()

    categories: list[str] = ["Comunidad"]

    keyword_map = {
        "tech": "Tecnología",
        "coding": "Tecnología",
        "programm": "Tecnología",
        "develop": "Tecnología",
        "software": "Tecnología",
        "data": "Tecnología",
        "ai ": "Tecnología",
        "machine learning": "Tecnología",
        "network": "Networking",
        "business": "Networking",
        "entrepreneur": "Networking",
        "startup": "Networking",
        "language": "Idiomas",
        "intercambio": "Idiomas",
        "english": "Idiomas",
        "french": "Idiomas",
        "hiking": "Deportes",
        "running": "Deportes",
        "yoga": "Deportes",
        "senderismo": "Deportes",
        "dance": "Baile",
        "salsa": "Baile",
        "bachata": "Baile",
        "music": "Música",
        "open mic": "Música",
        "poetry": "Arte y Cultura",
        "art": "Arte y Cultura",
        "storytelling": "Arte y Cultura",
        "meditation": "Bienestar",
        "mindful": "Bienestar",
        "board game": "Ocio",
        "juegos": "Ocio",
        "social": "Social",
        "drinks": "Social",
        "party": "Social",
    }

    combined = f"{title} {group_name}"
    matched: set[str] = set()
    for keyword, category in keyword_map.items():
        if keyword in combined and category not in matched:
            matched.add(category)
            categories.append(category)

    return _dedupe_strings(categories)


def _extract_record(node: dict[str, Any]) -> dict[str, Any] | None:
    title = _clean_text(node.get("title"))
    if not title:
        return None

    if _is_online_event(node):
        return None

    if not _is_madrid_area(node):
        return None

    venue = node.get("venue") or {}
    group = node.get("group") or {}
    fee = node.get("feeSettings") or {}
    photo = node.get("featuredEventPhoto") or {}
    rsvps = (node.get("rsvps") or {}).get("totalCount", 0)

    event_url = _clean_text(node.get("eventUrl"))
    start_iso = _parse_iso(node.get("dateTime"))

    # Description cleanup
    raw_desc = _clean_text(node.get("description"))
    description = _strip_html(raw_desc) if raw_desc else title

    # Price
    price_amount = fee.get("amount")
    price: float | None = None
    currency: str | None = None
    if price_amount is not None:
        try:
            price = float(price_amount)
            currency = _clean_text(fee.get("currency")) or "EUR"
        except (TypeError, ValueError):
            pass

    # Image
    image = _clean_text(photo.get("highResUrl") or photo.get("baseUrl")) or None

    # Venue info
    venue_name = _clean_text(venue.get("name")) or None
    venue_city = _clean_text(venue.get("city")) or None
    venue_address = _clean_text(venue.get("address")) or None
    full_address_parts = [p for p in (venue_address, venue_city) if p]
    full_address = ", ".join(full_address_parts) or venue_name

    # Tags from group
    tags: list[str] = []
    group_name = _clean_text(group.get("name"))
    if group_name:
        tags.append(group_name)

    categories = _infer_categories(node)

    return {
        "id": _clean_text(node.get("id")),
        "titulo": title,
        "subtitulo": group_name or None,
        "descripcion": description[:2000],
        "contenido": description,
        "categorias": categories,
        "etiquetas": _dedupe_strings(tags),
        "lugar": venue_name,
        "direccion": full_address,
        "latitud": venue.get("lat"),
        "longitud": venue.get("lon"),
        "precio": price,
        "moneda": currency,
        "es_gratis": price == 0.0 if price is not None else None,
        "fecha_inicio": start_iso,
        "fecha_fin": start_iso,
        "fechas_disponibles": _dedupe_strings([start_iso]),
        "url": event_url,
        "url_articulo": event_url,
        "url_compra": event_url,
        "imagen": image,
        "fuente": SOURCE_NAME,
        "metadata": {
            "meetup_id": node.get("id"),
            "event_type": _clean_text(node.get("eventType")) or None,
            "group_urlname": _clean_text(group.get("urlname")) or None,
            "group_name": group_name or None,
            "rsvps": rsvps,
            "max_tickets": node.get("maxTickets"),
            "rsvp_state": _clean_text(node.get("rsvpState")) or None,
        },
    }


# ── GraphQL fetch ────────────────────────────────────────────────────────

def _fetch_events(session: requests.Session) -> list[dict[str, Any]]:
    """Paginate through recommendedEvents and collect all nodes."""
    today = date.today()
    start_date = datetime.combine(today, datetime.min.time(), MADRID_TZ).isoformat()
    query = RECOMMENDED_EVENTS_QUERY_TPL.format(
        lat=MADRID_LAT, lon=MADRID_LON, start_date=start_date
    )

    all_nodes: list[dict[str, Any]] = []
    cursor: str | None = None

    for page_num in range(1, MAX_PAGES + 1):
        variables: dict[str, Any] = {
            "first": PAGE_SIZE,
            "after": cursor,
        }
        resp = session.post(
            GQL_URL,
            json={"query": query, "variables": variables},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            log.warning(
                "Meetup GQL errors on page %d: %s",
                page_num,
                [e.get("message") for e in data["errors"][:3]],
            )
            if "data" not in data or not data["data"]:
                break

        rec = (data.get("data") or {}).get("recommendedEvents") or {}
        edges = rec.get("edges") or []
        page_info = rec.get("pageInfo") or {}
        total = rec.get("totalCount", "?")

        for edge in edges:
            node = edge.get("node")
            if node:
                all_nodes.append(node)

        log.info(
            "Meetup page %d: %d edges (total=%s), cumul=%d",
            page_num,
            len(edges),
            total,
            len(all_nodes),
        )

        if not page_info.get("hasNextPage") or not page_info.get("endCursor"):
            break
        cursor = page_info["endCursor"]

    return all_nodes


# ── main ─────────────────────────────────────────────────────────────────

def scrape_meetup() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    # Warm up session cookies
    log.info("Meetup: warming up session via find page")
    session.get(FIND_PAGE, timeout=REQUEST_TIMEOUT)

    nodes = _fetch_events(session)
    log.info("Fetched %d Meetup event nodes", len(nodes))

    records: list[dict[str, Any]] = []
    skipped = 0
    for node in nodes:
        record = _extract_record(node)
        if record:
            records.append(record)
        else:
            skipped += 1

    log.info(
        "Meetup: %d records accepted, %d skipped (non-Madrid/online)",
        len(records),
        skipped,
    )

    normalized = normalize_plan_records(records, source=SOURCE_NAME)
    OUTPUT_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d Meetup Madrid events to %s", len(normalized), OUTPUT_FILE)
    log.info(
        "Summary: %d events, %d with coords, %d with price, %d free",
        len(normalized),
        sum(1 for r in normalized if r.get("latitud") is not None),
        sum(1 for r in normalized if r.get("precio") is not None),
        sum(1 for r in normalized if r.get("es_gratis") is True),
    )
    return normalized


if __name__ == "__main__":
    scrape_meetup()
