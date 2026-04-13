"""
Eventbrite Madrid scraper.

Scrapes LD+JSON structured data from Eventbrite category listings.
Extracts: title, price, coordinates, category, dates, venue, description.

Output: eventos_eventbrite.json
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

PAGES_PER_CATEGORY = 3
REQUEST_DELAY = 1.0
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "eventos_eventbrite.json"

CATEGORIAS = {
    "Negocios": "business",
    "Gastronomía": "food-and-drink",
    "Salud": "health",
    "Música": "music",
    "Motores": "auto-boat-and-air",
    "Solidaridad": "charity-and-causes",
    "Comunidad": "community",
    "Familia": "family-and-education",
    "Moda": "fashion",
    "Cine": "film-and-media",
    "Aficiones": "hobbies",
    "Hogar": "home-and-lifestyle",
    "Artes": "arts",
    "Gobierno": "government",
    "Espiritualidad": "spirituality",
    "Escolares": "school-activities",
    "Ciencia": "science-and-tech",
    "Vacaciones": "holiday",
    "Deportes": "sports-and-fitness",
    "Viajes": "travel-and-outdoor",
    "Otro": "other",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}
GENERIC_IMAGE_TOKENS = (
    "eb_orange_on_white_1200x630",
    "/django/images/logos/",
    "/static/media/map.",
    "map.84ed7a7f",
)
DETAIL_IMAGE_CACHE: dict[str, str | None] = {}


def _extract_price(info: dict) -> tuple[float | None, str | None]:
    """Extract lowest price and currency from LD+JSON offers."""
    offers = info.get("offers")
    if not offers:
        return None, None

    # offers can be a single dict or a list
    if isinstance(offers, dict):
        offers = [offers]
    if not isinstance(offers, list):
        return None, None

    prices = []
    currency = None
    for offer in offers:
        p = offer.get("price")
        if p is not None:
            try:
                prices.append(float(p))
            except (ValueError, TypeError):
                pass
        if not currency:
            currency = offer.get("priceCurrency")

    if prices:
        return min(prices), currency or "EUR"
    return None, currency


def _extract_eventbrite_image(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, list):
        for item in value:
            image = _extract_eventbrite_image(item)
            if image:
                return image
        return None

    if isinstance(value, dict):
        for key in ("url", "src", "original", "image"):
            if key not in value:
                continue
            image = _extract_eventbrite_image(value.get(key))
            if image:
                return image
    return None


def _is_generic_image(url: str | None) -> bool:
    text = (url or "").strip().casefold()
    if not text:
        return True
    return any(token in text for token in GENERIC_IMAGE_TOKENS)


def _pick_first_real_image(candidates: list[str | None]) -> str | None:
    for candidate in candidates:
        if candidate and not _is_generic_image(candidate):
            return candidate
    return None


def _walk_eventbrite_values(value: Any):
    if isinstance(value, str):
        text = value.strip()
        if text:
            yield text
        return

    if isinstance(value, list):
        for item in value:
            yield from _walk_eventbrite_values(item)
        return

    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_eventbrite_values(item)


def _extract_eventbrite_page_props_image(page_props: Any) -> str | None:
    seen: set[str] = set()
    for candidate in _walk_eventbrite_values(page_props):
        if candidate in seen or not candidate.startswith("http"):
            continue
        seen.add(candidate)

        lowered = candidate.casefold()
        if _is_generic_image(candidate):
            continue
        if (
            "img.evbuc.com" in lowered
            or "cdn.evbuc.com/images/" in lowered
            or lowered.endswith((".jpg", ".jpeg", ".png", ".webp"))
            or any(token in lowered for token in (".jpg?", ".jpeg?", ".png?", ".webp?"))
        ):
            return candidate
    return None


def _extract_eventbrite_detail_image(session: requests.Session, url: str | None) -> str | None:
    link = (url or "").strip()
    if not link:
        return None
    if link in DETAIL_IMAGE_CACHE:
        return DETAIL_IMAGE_CACHE[link]

    image = None
    try:
        response = session.get(link, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        next_tag = soup.find("script", id="__NEXT_DATA__")
        if next_tag and next_tag.string:
            data = json.loads(next_tag.string)
            page_props = data.get("props", {}).get("pageProps", {})
            context = page_props.get("context", {})
            basic_info = context.get("basicInfo") or {}
            gallery = context.get("gallery") or {}
            organizer = basic_info.get("organizer") or {}
            candidates = [
                _extract_eventbrite_image(basic_info.get("image")),
                *[
                    _extract_eventbrite_image(item)
                    for item in gallery.get("images") or []
                ],
                _extract_eventbrite_image(organizer.get("image")),
            ]
            image = _pick_first_real_image(candidates)
            if not image:
                image = _extract_eventbrite_page_props_image(page_props)
    except (requests.RequestException, json.JSONDecodeError, TypeError, ValueError):
        image = None

    DETAIL_IMAGE_CACHE[link] = image
    return image


def scrape_eventbrite() -> list[dict]:
    """Scrape Eventbrite Madrid events across all categories."""
    session = requests.Session()
    session.headers.update(HEADERS)
    seen_urls: set[str] = set()
    events: list[dict] = []

    for nombre, slug in CATEGORIAS.items():
        base_url = f"https://www.eventbrite.es/d/spain--madrid/{slug}--events/?sort_by=date"
        cat_count = 0

        for page in range(1, PAGES_PER_CATEGORY + 1):
            url = f"{base_url}&page={page}"
            try:
                res = session.get(url, timeout=15)
                if res.status_code != 200:
                    break
            except requests.RequestException as e:
                log.warning("Request failed for %s page %d: %s", slug, page, e)
                break

            soup = BeautifulSoup(res.text, "html.parser")
            scripts = soup.find_all("script", type="application/ld+json")

            page_count = 0
            for s in scripts:
                try:
                    data = json.loads(s.string)
                except (json.JSONDecodeError, TypeError):
                    continue

                items = data.get("itemListElement", []) if isinstance(data, dict) else []
                for entry in items:
                    info = entry.get("item", {})
                    link = info.get("url")
                    if not link or link in seen_urls:
                        continue
                    seen_urls.add(link)

                    loc = info.get("location", {})
                    geo = loc.get("geo", {})
                    addr = loc.get("address", {})
                    price, currency = _extract_price(info)
                    image = info.get("image") or _extract_eventbrite_detail_image(session, link)

                    events.append({
                        "id": link.split("-")[-1] if link else None,
                        "titulo": info.get("name"),
                        "precio": price,
                        "moneda": currency,
                        "lugar": loc.get("name"),
                        "direccion": addr.get("streetAddress")
                            or addr.get("addressLocality")
                            or "Madrid",
                        "latitud": geo.get("latitude"),
                        "longitud": geo.get("longitude"),
                        "fecha_inicio": info.get("startDate"),
                        "fecha_fin": info.get("endDate"),
                        "fechas_disponibles": sorted({
                            dt for dt in [info.get("startDate"), info.get("endDate")] if dt
                        }),
                        "categorias": [nombre],
                        "url": link,
                        "imagen": image,
                        "descripcion": (info.get("description") or "")[:500],
                        "fuente": "eventbrite",
                    })
                    page_count += 1

            cat_count += page_count
            time.sleep(REQUEST_DELAY)

        if cat_count > 0:
            log.info("%-20s: %3d events", nombre, cat_count)

    events = normalize_plan_records(events, source="eventbrite")

    # Save
    OUTPUT_FILE.write_text(
        json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Saved %d events to %s", len(events), OUTPUT_FILE)
    return events


if __name__ == "__main__":
    results = scrape_eventbrite()
    with_price = sum(1 for e in results if e["precio"] is not None)
    with_coords = sum(1 for e in results if e["latitud"] is not None)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(results), with_coords, with_price,
    )