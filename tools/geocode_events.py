#!/usr/bin/env python3
"""
Geocode events that have an address but no coordinates.

Uses Nominatim (free, no API key) with a local JSON cache so that
the same address is never geocoded twice across runs.

Usage:
    python tools/geocode_events.py           # process only events missing coords
    python tools/geocode_events.py --force   # re-geocode everything
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

ROOT = Path(__file__).resolve().parent.parent
EVENTS_FILE = ROOT / "outputs" / "eventos_madrid_all.json"
CACHE_FILE = ROOT / "outputs" / "geocode_cache.json"

# Madrid bounding box for viewbox hint
MADRID_VIEWBOX = ((40.30, -3.85), (40.55, -3.55))
# If geocoded coords are outside metro Madrid, reject
MADRID_BOUNDS = {"lat": (40.30, 40.55), "lon": (-3.85, -3.55)}

# Nominatim rate limit: 1 request/second
RATE_LIMIT_SECONDS = 1.1


def _load_cache() -> dict[str, dict]:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict[str, dict]):
    CACHE_FILE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _clean_address(addr: str) -> str:
    """Normalize an address string for geocoding."""
    addr = addr.strip()
    # Remove common noise
    addr = re.sub(r"\b(España|Spain)\b", "", addr, flags=re.IGNORECASE)
    # Ensure Madrid is in the query for better hit rate
    if "madrid" not in addr.lower():
        addr = addr.rstrip(",. ") + ", Madrid, España"
    elif "españa" not in addr.lower() and "spain" not in addr.lower():
        addr = addr.rstrip(",. ") + ", España"
    return addr.strip()


def _in_madrid_area(lat: float, lon: float) -> bool:
    return (
        MADRID_BOUNDS["lat"][0] <= lat <= MADRID_BOUNDS["lat"][1]
        and MADRID_BOUNDS["lon"][0] <= lon <= MADRID_BOUNDS["lon"][1]
    )


def geocode_events(events: list[dict], *, force: bool = False) -> tuple[int, int]:
    """
    Geocode events in-place. Returns (geocoded_count, failed_count).
    """
    cache = _load_cache()
    geolocator = Nominatim(
        user_agent="madplan_geocoder/1.0",
        timeout=10,
    )

    to_geocode = []
    for event in events:
        lat = event.get("latitud")
        lon = event.get("longitud")
        addr = event.get("direccion", "")
        lugar = event.get("lugar", "")

        if not force and lat and lon:
            continue

        query = addr or lugar
        if not query or len(query.strip()) < 5:
            continue

        to_geocode.append((event, query))

    print(f"Events needing geocoding: {len(to_geocode)}")

    geocoded = 0
    failed = 0

    for i, (event, raw_query) in enumerate(to_geocode):
        clean_q = _clean_address(raw_query)
        cache_key = clean_q.lower().strip()

        # Check cache first
        if cache_key in cache:
            cached = cache[cache_key]
            if cached.get("lat") is not None:
                event["latitud"] = cached["lat"]
                event["longitud"] = cached["lon"]
                geocoded += 1
            else:
                failed += 1
            continue

        # Rate limit
        time.sleep(RATE_LIMIT_SECONDS)

        try:
            location = geolocator.geocode(
                clean_q,
                viewbox=[MADRID_VIEWBOX[0], MADRID_VIEWBOX[1]],
                bounded=False,
                language="es",
            )
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            print(f"  [{i+1}/{len(to_geocode)}] ERROR: {exc} for '{raw_query[:50]}'")
            cache[cache_key] = {"lat": None, "lon": None, "query": raw_query}
            failed += 1
            # Save cache periodically
            if (i + 1) % 50 == 0:
                _save_cache(cache)
            continue

        if location and _in_madrid_area(location.latitude, location.longitude):
            event["latitud"] = round(location.latitude, 6)
            event["longitud"] = round(location.longitude, 6)
            cache[cache_key] = {
                "lat": round(location.latitude, 6),
                "lon": round(location.longitude, 6),
                "query": raw_query,
            }
            geocoded += 1
            if (i + 1) % 100 == 0:
                print(f"  [{i+1}/{len(to_geocode)}] Geocoded: {geocoded}, Failed: {failed}")
        else:
            cache[cache_key] = {"lat": None, "lon": None, "query": raw_query}
            failed += 1

        # Save cache periodically
        if (i + 1) % 50 == 0:
            _save_cache(cache)

    _save_cache(cache)
    return geocoded, failed


def run(force: bool = False):
    events = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    geocoded, failed = geocode_events(events, force=force)
    EVENTS_FILE.write_text(
        json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    total_with_coords = sum(1 for e in events if e.get("latitud") and e.get("longitud"))
    print(f"\nResults: +{geocoded} geocoded, {failed} failed")
    print(f"Total events with coordinates: {total_with_coords}/{len(events)}")


if __name__ == "__main__":
    import sys
    run(force="--force" in sys.argv)
