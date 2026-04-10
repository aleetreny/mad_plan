"""
Madrid Events Aggregator — run all scrapers and produce a unified output.

Combines events from:
  - Fever (fever.py)
  - Eventbrite (eventbrite.py)
  - Datos Abiertos Madrid (datos_madrid.py)

All sources use the same schema:
  id, titulo, precio, moneda, lugar, direccion, latitud, longitud,
  fecha_inicio, fecha_fin, categorias, url, imagen, descripcion, fuente

Output: eventos_madrid_all.json
"""

import json
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

OUTPUT_FILE = Path(__file__).parent / "eventos_madrid_all.json"


def explode_by_datetime(events: list[dict]) -> list[dict]:
    """
    Expand each event into one row per available datetime.

    Priority:
      1) fechas_disponibles (list from source)
      2) fecha_inicio
      3) keep one row with fecha_evento=None
    """
    expanded: list[dict] = []
    for event in events:
        datetimes = event.get("fechas_disponibles") or []
        if not datetimes:
            fallback = event.get("fecha_inicio")
            datetimes = [fallback] if fallback else [None]

        seen = set()
        ordered_datetimes = []
        for dt in datetimes:
            if dt in seen:
                continue
            seen.add(dt)
            ordered_datetimes.append(dt)

        source = event.get("fuente", "src")
        base_id = str(event.get("id"))
        for idx, dt in enumerate(ordered_datetimes, start=1):
            row = dict(event)
            row["evento_id_base"] = base_id
            row["fecha_evento"] = dt
            row["sesion_index"] = idx
            row["id"] = f"{source}::{base_id}::s{idx}"
            expanded.append(row)
    return expanded


def run_all():
    source_events: list[dict] = []

    # --- Fever ---
    log.info("=" * 60)
    log.info("FEVER")
    log.info("=" * 60)
    try:
        from fever import main as fever_main
        fever_events = fever_main()
        source_events.extend(fever_events)
        log.info("Fever: %d events", len(fever_events))
    except Exception as e:
        log.error("Fever scraper failed: %s", e)

    # --- Eventbrite ---
    log.info("=" * 60)
    log.info("EVENTBRITE")
    log.info("=" * 60)
    try:
        from eventbrite import scrape_eventbrite
        eb_events = scrape_eventbrite()
        source_events.extend(eb_events)
        log.info("Eventbrite: %d events", len(eb_events))
    except Exception as e:
        log.error("Eventbrite scraper failed: %s", e)

    # --- Datos Madrid ---
    log.info("=" * 60)
    log.info("DATOS MADRID")
    log.info("=" * 60)
    try:
        from datos_madrid import scrape_datos_madrid
        dm_events = scrape_datos_madrid()
        source_events.extend(dm_events)
        log.info("Datos Madrid: %d events", len(dm_events))
    except Exception as e:
        log.error("Datos Madrid scraper failed: %s", e)

    # --- Save combined ---
    all_events = explode_by_datetime(source_events)
    OUTPUT_FILE.write_text(
        json.dumps(all_events, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- Summary ---
    log.info("=" * 60)
    log.info("COMBINED SUMMARY")
    log.info("=" * 60)
    by_source = {}
    for e in source_events:
        src = e.get("fuente", "unknown")
        by_source.setdefault(src, {"total": 0, "coords": 0, "price": 0})
        by_source[src]["total"] += 1
        if e.get("latitud"):
            by_source[src]["coords"] += 1
        if e.get("precio") is not None:
            by_source[src]["price"] += 1

    for src, stats in by_source.items():
        log.info(
            "  %-15s: %4d total, %4d coords, %4d price",
            src, stats["total"], stats["coords"], stats["price"],
        )
    log.info("  %-15s: %4d total", "SOURCE ROWS", len(source_events))
    log.info("  %-15s: %4d total", "SESSION ROWS", len(all_events))
    log.info("Saved to %s", OUTPUT_FILE)


if __name__ == "__main__":
    run_all()
