"""
datos.madrid.es cultural events scraper.

Uses the official Madrid open data API for cultural/leisure events.
Extracts: title, price, coordinates, category, dates, venue, description.

Output: eventos_datos_madrid.json
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

API_URL = "https://datos.madrid.es/api/3/action/package_show?id=206974-0-agenda-eventos-culturales-100"
OUTPUT_FILE = Path(__file__).parent / "eventos_datos_madrid.json"


def _parse_price(item: dict) -> tuple[float | None, str | None]:
    """Try to extract a numeric price from the free-text 'price' field."""
    raw = item.get("price") or item.get("economy-free") or ""
    if not raw:
        # Check 'gratuito' flag
        if item.get("free") == 1 or "gratis" in str(item.get("title", "")).lower():
            return 0.0, "EUR"
        return None, None

    raw = str(raw).strip().lower()
    if "gratis" in raw or "gratuito" in raw or "free" in raw or raw == "0":
        return 0.0, "EUR"

    # Try to extract a number
    import re
    match = re.search(r"(\d+[.,]?\d*)", raw)
    if match:
        price_str = match.group(1).replace(",", ".")
        try:
            return float(price_str), "EUR"
        except ValueError:
            pass

    return None, "EUR"


def _classify_category(item: dict) -> list[str]:
    """Extract category from the @type URI (e.g. '.../actividades/DanzaBaile')."""
    raw = item.get("@type", "")
    if "/" in raw:
        # Extract last segment: 'DanzaBaile' from '.../actividades/DanzaBaile'
        segment = raw.rstrip("/").rsplit("/", 1)[-1]
        if segment:
            # Split CamelCase into readable form: 'DanzaBaile' → 'Danza Baile'
            import re
            readable = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", segment)
            return [readable]
    return ["Cultura"]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _build_available_datetimes(item: dict) -> list[str]:
    start_dt = _parse_dt(item.get("dtstart"))
    end_dt = _parse_dt(item.get("dtend"))
    if not start_dt:
        return []

    recurrence = item.get("recurrence") or {}
    recurrence_days = recurrence.get("days")
    recurrence_freq = recurrence.get("frequency")
    recurrence_interval = recurrence.get("interval", 1)

    excluded_days_raw = (item.get("excluded-days") or "").strip()
    excluded_dates: set[str] = set()
    if excluded_days_raw:
        for token in excluded_days_raw.split(","):
            token = token.strip()
            if token:
                excluded_dates.add(token)

    if not (end_dt and recurrence_days and recurrence_freq == "WEEKLY"):
        return [start_dt.isoformat()]

    day_code_to_weekday = {
        "MO": 0,
        "TU": 1,
        "WE": 2,
        "TH": 3,
        "FR": 4,
        "SA": 5,
        "SU": 6,
    }
    target_weekdays = {
        day_code_to_weekday[d.strip()]
        for d in recurrence_days.split(",")
        if d.strip() in day_code_to_weekday
    }
    if not target_weekdays:
        return [start_dt.isoformat()]

    if not isinstance(recurrence_interval, int) or recurrence_interval < 1:
        recurrence_interval = 1

    expanded: list[str] = []
    current_day = start_dt.date()
    final_day = end_dt.date()
    start_week_anchor = start_dt.date() - timedelta(days=start_dt.weekday())

    while current_day <= final_day:
        if current_day.weekday() in target_weekdays:
            current_week_anchor = current_day - timedelta(days=current_day.weekday())
            week_distance = (current_week_anchor - start_week_anchor).days // 7
            if week_distance % recurrence_interval == 0:
                current_day_str = current_day.isoformat()
                if current_day_str not in excluded_dates:
                    candidate = datetime.combine(current_day, start_dt.time())
                    expanded.append(candidate.isoformat())
        current_day += timedelta(days=1)

    if not expanded:
        return [start_dt.isoformat()]
    return expanded


def scrape_datos_madrid() -> list[dict]:
    """Fetch and parse Madrid open data cultural events."""
    log.info("Fetching API metadata …")
    try:
        meta = requests.get(API_URL, timeout=15).json()
    except Exception as e:
        log.error("Failed to fetch API metadata: %s", e)
        return []

    resources = meta.get("result", {}).get("resources", [])
    if not resources:
        log.error("No resources found in API response")
        return []

    # Pick the JSON resource (first one is usually JSON)
    data_url = resources[0].get("url")
    if not data_url:
        log.error("No data URL in resources")
        return []

    log.info("Fetching event data from %s …", data_url[:80])
    try:
        data = requests.get(data_url, timeout=30).json()
    except Exception as e:
        log.error("Failed to fetch event data: %s", e)
        return []

    graph = data.get("@graph", [])
    log.info("Raw items: %d", len(graph))

    events = []
    for item in graph:
        loc = item.get("location", {})
        price, currency = _parse_price(item)

        # Address from nested structure
        address_obj = item.get("address", {})
        area = address_obj.get("area", {})
        street = area.get("street-address", "")
        district_id = address_obj.get("district", {}).get("@id", "")
        district = district_id.rstrip("/").rsplit("/", 1)[-1] if "/" in district_id else ""

        addr_parts = [p for p in [street, district] if p]
        venue = item.get("event-location", "")

        events.append({
            "id": str(item.get("id", item.get("@id", ""))),
            "titulo": item.get("title", ""),
            "precio": price,
            "moneda": currency,
            "lugar": venue,
            "direccion": ", ".join(addr_parts) if addr_parts else "Madrid",
            "latitud": loc.get("latitude"),
            "longitud": loc.get("longitude"),
            "fecha_inicio": item.get("dtstart"),
            "fecha_fin": item.get("dtend"),
            "fechas_disponibles": _build_available_datetimes(item),
            "categorias": _classify_category(item),
            "url": item.get("link"),
            "imagen": None,
            "descripcion": (item.get("description") or "")[:500],
            "fuente": "datos_madrid",
        })

    # Save
    OUTPUT_FILE.write_text(
        json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d events to %s", len(events), OUTPUT_FILE)
    return events


if __name__ == "__main__":
    results = scrape_datos_madrid()
    with_price = sum(1 for e in results if e["precio"] is not None)
    with_coords = sum(1 for e in results if e["latitud"] is not None)
    cats = set()
    for e in results:
        cats.update(e["categorias"])
    log.info(
        "Summary: %d events, %d with coords, %d with price, %d categories",
        len(results), with_coords, with_price, len(cats),
    )