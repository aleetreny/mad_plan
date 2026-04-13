"""
Fever Madrid scraper.

Strategy:
  1. Parse serverApp-state from category pages to get plan listings + categories.
  2. Fetch /m/{plan_id} detail pages to resolve coordinates via LD+JSON.
  3. Cache coordinates by venue name so we don't re-fetch for shared venues.

Output: eventos_fever.json
"""

import json
import time
import re
import logging
from pathlib import Path

import cloudscraper
from bs4 import BeautifulSoup

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE = "https://feverup.com"
LANG = "es"
CITY = "madrid"
LISTING_URL = f"{BASE}/{LANG}/{CITY}"
REQUEST_DELAY = 1.0  # seconds between requests
MAX_PAGES_PER_CATEGORY = 6  # each page = 48 plans
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "eventos_fever.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_scraper():
    return cloudscraper.create_scraper()


def _parse_state(soup: BeautifulSoup) -> dict | None:
    """Extract the Angular Transfer State from a Fever page."""
    tag = soup.find("script", id="serverApp-state")
    if tag and tag.string:
        try:
            return json.loads(tag.string)
        except json.JSONDecodeError:
            log.warning("Failed to parse serverApp-state JSON")
    return None


def _clean_text(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split())


def _response_soup(response) -> BeautifulSoup:
    apparent = (getattr(response, "apparent_encoding", "") or "").lower().replace("_", "-")
    current = (getattr(response, "encoding", "") or "").lower().replace("_", "-")
    if apparent == "utf-8" and current in {"iso-8859-1", "latin-1", "windows-1252"}:
        response.encoding = "utf-8"
    return BeautifulSoup(response.text, "html.parser")


def _build_address(address: dict | None) -> str | None:
    if not isinstance(address, dict):
        return None

    parts = [
        _clean_text(address.get("streetAddress")),
        _clean_text(address.get("addressLocality")),
        _clean_text(address.get("postalCode")),
    ]
    values = [part for part in parts if part]
    if values:
        return ", ".join(values)
    return None


def _clean_inline_location(value: str | None) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    text = re.split(r"[📱👉⌛👤📅⏳]", text, maxsplit=1)[0]
    text = re.split(r"\b(?:Información|Informacion|Descripción|Descripcion|Menú|Menu)\b", text, maxsplit=1)[0]
    text = text.strip(" .,;:-")
    return text or None


def _extract_visible_location(soup: BeautifulSoup) -> dict | None:
    lines = [
        _clean_text(line)
        for line in soup.get_text("\n").splitlines()
        if _clean_text(line)
    ]
    if not lines:
        return None

    info_location = None
    route_venue = None
    route_address = None

    stop_tokens = (
        "información",
        "informacion",
        "descripción",
        "descripcion",
        "menú",
        "menu",
        "¿cómo llegar?",
        "como llegar?",
    )

    for index, line in enumerate(lines):
        lowered = line.casefold()
        if "lugar:" in lowered:
            inline_location = _clean_inline_location(line.split(":", 1)[1] if ":" in line else "")
            if inline_location:
                info_location = inline_location
                break

            collected_lines = []
            for candidate in lines[index + 1 :]:
                candidate_lowered = candidate.casefold()
                if any(token in candidate_lowered for token in stop_tokens):
                    break
                collected_lines.append(candidate)

            if collected_lines:
                info_location = _clean_inline_location(" ".join(collected_lines))
            continue
        if "¿cómo llegar?" in lowered or "como llegar?" in lowered:
            continue

    for index, line in enumerate(lines):
        lowered = line.casefold()
        if "¿cómo llegar?" not in lowered and "como llegar?" not in lowered:
            continue

        for candidate in lines[index + 1 :]:
            if not route_venue:
                route_venue = _clean_inline_location(candidate)
                continue
            route_address = _clean_inline_location(candidate)
            break
        break

    venue_name = route_venue or info_location
    if venue_name and venue_name.casefold() in {"madrid", "varias localizaciones"}:
        venue_name = info_location if info_location and info_location != venue_name else None

    address = route_address
    if not address and info_location and "," in info_location:
        address = info_location

    if not any((venue_name, address)):
        return None

    return {
        "venue_name": venue_name,
        "address": address,
        "latitude": None,
        "longitude": None,
    }


def _extract_plans_from_state(state: dict) -> tuple[list[dict], int]:
    """Return (plans_list, total_plans) from a WPF skeleton in the state."""
    for key in state:
        if "WPFSkeleton" not in key:
            continue
        skeleton = state[key].get("skeleton", [])
        for section in skeleton:
            content = section.get("content", {})
            plans = content.get("plans")
            if plans is not None:
                return plans, content.get("total_plans", len(plans))
    return [], 0


def _extract_wpf_categories(state: dict) -> list[dict]:
    """Return the list of WPF category definitions (id, slug, title, children)."""
    for key in state:
        if "whatplanfilters" in key.lower():
            return state[key].get("wpfs", [])
    return []


# ---------------------------------------------------------------------------
# Phase 1: collect plans + assign categories
# ---------------------------------------------------------------------------

def collect_plans(scraper) -> dict[int, dict]:
    """
    Scrape the main page + each category page.
    Returns {plan_id: plan_dict} where plan_dict has an extra 'categories' list.
    """
    plans: dict[int, dict] = {}

    # --- Main page (que-hacer) to discover categories ---
    log.info("Fetching main listing page …")
    resp = scraper.get(f"{LISTING_URL}/que-hacer")
    if resp.status_code != 200:
        log.error("Main page returned %d", resp.status_code)
        return plans

    soup = _response_soup(resp)
    state = _parse_state(soup)
    if not state:
        log.error("No state data on main page")
        return plans

    categories = _extract_wpf_categories(state)
    log.info("Found %d category pages", len(categories))

    # We'll scrape the main page + each category page.
    # Skip seasonal/niche categories that add little value.
    SKIP_SLUGS = {
        "black-friday", "san-valentin", "halloween", "navidad",
        "dia-del-padre", "back-in-action",
    }

    pages_to_scrape: list[tuple[str, str]] = []  # (slug, category_title)
    for cat in categories:
        slug = cat.get("slug", "")
        title = cat.get("title", slug)
        if slug in SKIP_SLUGS:
            continue
        pages_to_scrape.append((slug, title))
        # Also include child sub-categories as labels
        for child in cat.get("children", []):
            # children are dicts with 'title' (and sometimes 'slug')
            if isinstance(child, str):
                pass  # just a name, we'll use the parent slug
            # child sub-slugs are not separate pages, tags come from parent

    def _ingest_plans(plan_list: list[dict], category: str):
        """Add plans to the master dict, accumulating categories."""
        for p in plan_list:
            pid = p.get("id")
            if pid is None:
                continue
            if pid not in plans:
                plans[pid] = {
                    "id": pid,
                    "name": p.get("name", ""),
                    "cover_image": p.get("cover_image", ""),
                    "price_amount": None,
                    "price_currency": None,
                    "venue_name": "",
                    "venue_hidden": False,
                    "date_start": p.get("first_active_session_date"),
                    "date_end": p.get("last_active_session_date"),
                    "rating": p.get("rating", {}).get("average"),
                    "num_ratings": p.get("rating", {}).get("num_ratings"),
                    "categories": set(),
                    "latitude": None,
                    "longitude": None,
                    "address": None,
                    "url": f"{BASE}/m/{pid}",
                }
                # Price
                pi = p.get("price_info", {})
                if pi and not pi.get("hide"):
                    plans[pid]["price_amount"] = pi.get("amount")
                    plans[pid]["price_currency"] = pi.get("currency", "EUR")
                # Venue
                loc = p.get("location", {})
                plans[pid]["venue_name"] = loc.get("name", "")
                plans[pid]["venue_hidden"] = loc.get("is_hidden", False)

            plans[pid]["categories"].add(category)

    # --- Scrape main page plans first ---
    page_plans, total = _extract_plans_from_state(state)
    _ingest_plans(page_plans, "General")
    log.info("que-hacer: %d plans (total=%d)", len(page_plans), total)

    # Paginate main page
    for page_num in range(1, MAX_PAGES_PER_CATEGORY):
        if len(page_plans) >= total:
            break
        time.sleep(REQUEST_DELAY)
        r = scraper.get(f"{LISTING_URL}/que-hacer?page={page_num}")
        if r.status_code != 200:
            break
        st = _parse_state(_response_soup(r))
        if not st:
            break
        pp, _ = _extract_plans_from_state(st)
        if not pp:
            break
        new_count = sum(1 for p in pp if p.get("id") not in plans)
        _ingest_plans(pp, "General")
        log.info("  que-hacer?page=%d: %d plans (%d new)", page_num, len(pp), new_count)
        if new_count == 0:
            break

    # --- Scrape category pages ---
    for slug, title in pages_to_scrape:
        if slug == "que-hacer":
            continue  # already done
        time.sleep(REQUEST_DELAY)
        r = scraper.get(f"{LISTING_URL}/{slug}")
        if r.status_code != 200:
            log.warning("Category %s returned %d", slug, r.status_code)
            continue
        st = _parse_state(_response_soup(r))
        if not st:
            continue
        pp, total = _extract_plans_from_state(st)
        new_count = sum(1 for p in pp if p.get("id") not in plans)
        _ingest_plans(pp, title)
        log.info("%-35s: %3d plans (total=%4s), %3d new, cumul=%d",
                 slug, len(pp), total, new_count, len(plans))

    log.info("Phase 1 done: %d unique plans collected", len(plans))
    return plans


# ---------------------------------------------------------------------------
# Phase 2: resolve coordinates via /m/{plan_id} detail pages
# ---------------------------------------------------------------------------

def _fetch_coords_from_detail(scraper, plan_id: int) -> dict | None:
    """
    Fetch /m/{plan_id} and extract location from LD+JSON @type=Event.
    Returns dict with lat, lon, venue_name, address or None.
    """
    url = f"{BASE}/m/{plan_id}"
    try:
        r = scraper.get(url, timeout=15)
        if r.status_code != 200:
            return None
    except Exception:
        return None

    soup = _response_soup(r)
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(tag.string)
        except (json.JSONDecodeError, TypeError):
            continue
        if ld.get("@type") != "Event":
            continue
        loc = ld.get("location", {})
        geo = loc.get("geo", {})
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        address = _build_address(loc.get("address"))
        venue_name = _clean_text(loc.get("name")) or None
        if any((lat is not None and lon is not None, venue_name, address)):
            return {
                "latitude": lat,
                "longitude": lon,
                "venue_name": venue_name,
                "address": address,
            }

    return _extract_visible_location(soup)


def enrich_coordinates(scraper, plans: dict[int, dict]):
    """
    For each unique venue, fetch one plan's detail page to get coords,
    then apply to all plans sharing that venue.
    """
    # Group plans by venue name
    venue_plans: dict[str, list[int]] = {}
    unknown_plans: list[int] = []
    for pid, p in plans.items():
        if p["venue_name"]:
            venue_plans.setdefault(p["venue_name"], []).append(pid)
        else:
            unknown_plans.append(pid)

    log.info(
        "Phase 2: %d unique venues to resolve, %d plans without venue name",
        len(venue_plans),
        len(unknown_plans),
    )

    coords_cache: dict[str, dict] = {}
    resolved = 0
    failed = 0

    for vname, pids in venue_plans.items():
        # Check cache
        if vname in coords_cache:
            for pid in pids:
                plans[pid].update(coords_cache[vname])
            resolved += len(pids)
            continue

        # Fetch detail for the first plan with this venue
        time.sleep(REQUEST_DELAY)
        result = _fetch_coords_from_detail(scraper, pids[0])
        if result:
            coords_cache[vname] = {
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "address": result["address"],
                "venue_name": result.get("venue_name") or vname,
            }
            for pid in pids:
                plans[pid].update(coords_cache[vname])
            resolved += len(pids)
            if result["latitude"] is not None and result["longitude"] is not None:
                log.info("  ✓ %s → (%.4f, %.4f) [%d plans]",
                         vname[:40], result["latitude"], result["longitude"], len(pids))
            else:
                log.info("  ✓ %s → venue/address resolved [%d plans]", vname[:40], len(pids))
        else:
            failed += len(pids)
            log.debug("  ✗ %s (no coords)", vname[:40])

    for pid in unknown_plans:
        time.sleep(REQUEST_DELAY)
        result = _fetch_coords_from_detail(scraper, pid)
        if result:
            plans[pid].update(result)
            resolved += 1
            log.info("  ✓ plan %s → venue/address recovered", pid)
        else:
            failed += 1

    log.info("Coordinates resolved for %d plans, %d without coords", resolved, failed)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_results(plans: dict[int, dict]):
    """Convert to a serialisable list and save."""
    output = []
    for p in plans.values():
        output.append({
            "id": p["id"],
            "titulo": p["name"],
            "precio": p["price_amount"],
            "moneda": p["price_currency"],
            "lugar": p["venue_name"],
            "direccion": p["address"],
            "latitud": p["latitude"],
            "longitud": p["longitude"],
            "fecha_inicio": p["date_start"],
            "fecha_fin": p["date_end"],
            "fechas_disponibles": sorted({
                dt for dt in [p["date_start"], p["date_end"]] if dt
            }),
            "categorias": sorted(p["categories"]),
            "valoracion": p["rating"],
            "num_valoraciones": p["num_ratings"],
            "url": p["url"],
            "imagen": p["cover_image"],
            "fuente": "fever",
        })

    output = normalize_plan_records(output, source="fever")

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Saved %d events to %s", len(output), OUTPUT_FILE)
    return output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(resolve_coordinates: bool = True):
    scraper = _create_scraper()

    # Phase 1: collect plan listings + categories
    plans = collect_plans(scraper)
    if not plans:
        log.error("No plans collected — aborting")
        return []

    # Phase 2: resolve venue coordinates
    if resolve_coordinates:
        enrich_coordinates(scraper, plans)
    else:
        log.info("Skipping Fever coordinate enrichment for fast pipeline mode")

    # Save
    return save_results(plans)


def fast_main():
    return main(resolve_coordinates=False)


if __name__ == "__main__":
    events = main()
    if events:
        # Quick summary
        with_coords = sum(1 for e in events if e["latitud"] is not None)
        with_price = sum(1 for e in events if e["precio"] is not None)
        cats = set()
        for e in events:
            cats.update(e["categorias"])
        log.info(
            "Summary: %d events, %d with coords, %d with price, %d categories",
            len(events), with_coords, with_price, len(cats),
        )