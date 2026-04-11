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

import requests
from bs4 import BeautifulSoup

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


def scrape_eventbrite() -> list[dict]:
    """Scrape Eventbrite Madrid events across all categories."""
    seen_urls: set[str] = set()
    events: list[dict] = []

    for nombre, slug in CATEGORIAS.items():
        base_url = f"https://www.eventbrite.es/d/spain--madrid/{slug}--events/?sort_by=date"
        cat_count = 0

        for page in range(1, PAGES_PER_CATEGORY + 1):
            url = f"{base_url}&page={page}"
            try:
                res = requests.get(url, headers=HEADERS, timeout=15)
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
                        "imagen": info.get("image"),
                        "descripcion": (info.get("description") or "")[:500],
                        "fuente": "eventbrite",
                    })
                    page_count += 1

            cat_count += page_count
            time.sleep(REQUEST_DELAY)

        if cat_count > 0:
            log.info("%-20s: %3d events", nombre, cat_count)

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