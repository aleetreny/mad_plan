"""Run every scraper in an isolated subprocess, merge feeds and build the web outputs.

Design goals:
  - One flaky source can never break the pipeline: each scraper runs in its own
    subprocess with a hard timeout and a single retry.
  - A failed or empty scrape never destroys data: the previous per-source output
    is restored, so the merge always works with the last good snapshot.
  - The merge step re-applies category normalization, geocoding (rate limited and
    capped) and finally emits the slim web feeds consumed by the frontend.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    from .normalization import (
        merge_news_records,
        merge_plan_records,
        utc_now_iso,
        validate_news_records,
        validate_plan_records,
    )
    from .normalize_categories import normalize_categories
    from .geocode_events import geocode_events
    from .build_web_feeds import build_web_feeds, strip_placeholder_images
except ImportError:
    from normalization import (
        merge_news_records,
        merge_plan_records,
        utc_now_iso,
        validate_news_records,
        validate_plan_records,
    )
    from normalize_categories import normalize_categories
    from geocode_events import geocode_events
    from build_web_feeds import build_web_feeds, strip_placeholder_images

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = ROOT / "outputs"

OUTPUT_FILE = OUTPUTS_DIR / "eventos_madrid_all.json"
NEWS_OUTPUT_FILE = OUTPUTS_DIR / "noticias_madrid_all.json"
RUN_MANIFEST_FILE = OUTPUTS_DIR / "pipeline_diario.json"

MAX_PARALLEL_SCRAPERS = 4
GEOCODE_MAX_NEW_LOOKUPS = 150

# timeout: hard per-subprocess limit in seconds (generous multiples of the
# durations observed in real runs, so slow days do not read as failures).
SCRAPER_JOBS: list[dict] = [
    {"name": "matadero", "kind": "plan", "timeout": 240},
    {"name": "teatros_canal", "kind": "plan", "timeout": 240},
    {"name": "circulo_bellas_artes", "kind": "plan", "timeout": 240},
    {"name": "ifema_madrid", "kind": "plan", "timeout": 300},
    {"name": "casa_mexico", "kind": "plan", "timeout": 420},
    {"name": "espacio_fundacion_telefonica", "kind": "plan", "timeout": 240},
    {"name": "museo_reina_sofia", "kind": "plan", "timeout": 300},
    {"name": "biblioteca_nacional", "kind": "plan", "timeout": 240},
    {"name": "fundacion_canal", "kind": "plan", "timeout": 300},
    {"name": "fundacion_mapfre", "kind": "plan", "timeout": 240},
    {"name": "sala_el_sol", "kind": "plan", "timeout": 240},
    {"name": "fever", "kind": "plan", "timeout": 1200},
    {"name": "eventbrite", "kind": "plan", "timeout": 600},
    {"name": "wegow", "kind": "plan", "timeout": 300},
    {"name": "ticketmaster", "kind": "plan", "timeout": 420},
    {"name": "datos_madrid", "kind": "plan", "timeout": 180},
    {"name": "esmadrid", "kind": "plan", "timeout": 900},
    {"name": "madrid_secreto", "kind": "plan", "timeout": 900},
    {"name": "rockthesport", "kind": "plan", "timeout": 300},
    {"name": "meetup", "kind": "plan", "timeout": 600},
    {"name": "timeout", "kind": "news", "timeout": 900},
    {"name": "gacetin_madrid", "kind": "news", "timeout": 240},
]

OUTPUT_BY_KIND = {"plan": "eventos_{name}.json", "news": "noticias_{name}.json"}


def _job_output_path(job: dict) -> Path:
    return OUTPUTS_DIR / OUTPUT_BY_KIND[job["kind"]].format(name=job["name"])


def _load_records(path: Path) -> list[dict] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, list) else None


def _run_scraper_subprocess(job: dict, *, fever_mode: str) -> dict:
    """Run one scraper as `python tools/<name>.py` with a hard timeout."""
    script = TOOLS_DIR / f"{job['name']}.py"
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["MAD_PLAN_FEVER_MODE"] = fever_mode

    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=job["timeout"],
            cwd=str(ROOT),
            env=env,
        )
        duration = round(time.time() - started, 1)
        if proc.returncode != 0:
            tail = "\n".join((proc.stderr or "").strip().splitlines()[-4:])
            return {"ok": False, "error": f"exit {proc.returncode}: {tail[-500:]}", "duration": duration}
        return {"ok": True, "duration": duration}
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": f"timeout after {job['timeout']}s",
            "duration": round(time.time() - started, 1),
        }
    except Exception as error:  # pragma: no cover - defensive
        return {
            "ok": False,
            "error": str(error),
            "duration": round(time.time() - started, 1),
        }


def _execute_job(job: dict, *, fever_mode: str, retries: int = 1) -> dict:
    """Run a scraper, keep the previous output when the fresh run is unusable."""
    output_path = _job_output_path(job)
    previous_bytes = output_path.read_bytes() if output_path.exists() else None
    previous_records = _load_records(output_path) or []

    attempt = 0
    result: dict = {"ok": False, "error": "not run", "duration": 0.0}
    while attempt <= retries:
        if attempt > 0:
            log.warning("Retrying %s (attempt %d)…", job["name"], attempt + 1)
            time.sleep(5)
        result = _run_scraper_subprocess(job, fever_mode=fever_mode)
        if result["ok"]:
            fresh = _load_records(output_path)
            if fresh:
                return {
                    "name": job["name"],
                    "kind": job["kind"],
                    "status": "ok",
                    "count": len(fresh),
                    "duration_seconds": result["duration"],
                    "error": None,
                    "stale": False,
                }
            result = {**result, "ok": False, "error": "scraper finished but produced no records"}
        attempt += 1

    # Restore the last good output so the merge never loses a source.
    if previous_bytes is not None:
        output_path.write_bytes(previous_bytes)
    stale_since = None
    if previous_records:
        stale_since = previous_records[0].get("scraped_en")

    log.error("%s failed: %s (using last good output: %d records)",
              job["name"], result.get("error"), len(previous_records))
    return {
        "name": job["name"],
        "kind": job["kind"],
        "status": "failed",
        "count": len(previous_records),
        "duration_seconds": result["duration"],
        "error": result.get("error"),
        "stale": bool(previous_records),
        "stale_since": stale_since,
    }


def merge_and_publish(source_results: list[dict] | None = None, *, geocode: bool = True) -> dict:
    """Merge per-source outputs, post-process and emit the web feeds."""
    plan_records: list[dict] = []
    news_records: list[dict] = []
    for job in SCRAPER_JOBS:
        records = _load_records(_job_output_path(job)) or []
        if job["kind"] == "plan":
            plan_records.extend(records)
        else:
            news_records.extend(records)

    merged_events = merge_plan_records(plan_records)
    merged_news = merge_news_records(news_records)

    # Post-processing on the merged feed.
    strip_placeholder_images(merged_events)
    normalize_categories(merged_events, force_all=True)
    normalize_categories(merged_news, force_all=True)
    if geocode:
        try:
            geocoded, failed = geocode_events(
                merged_events, max_new_lookups=GEOCODE_MAX_NEW_LOOKUPS
            )
            log.info("Geocoding: +%d resolved, %d failed", geocoded, failed)
        except Exception as error:
            log.warning("Geocoding skipped: %s", error)

    OUTPUT_FILE.write_text(
        json.dumps(merged_events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    NEWS_OUTPUT_FILE.write_text(
        json.dumps(merged_news, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    plan_validation = validate_plan_records(merged_events)
    news_validation = validate_news_records(merged_news)

    web_stats = build_web_feeds(merged_events, merged_news)

    manifest_sources = source_results or [
        {
            "name": job["name"],
            "kind": job["kind"],
            "status": "ok" if _job_output_path(job).exists() else "missing",
            "count": len(_load_records(_job_output_path(job)) or []),
        }
        for job in SCRAPER_JOBS
    ]

    return {
        "sources": manifest_sources,
        "feeds": {
            "planes": {
                "output": "outputs/eventos_madrid_all.json",
                "web_output": "outputs/eventos_web.json",
                "count": len(merged_events),
                "web_count": web_stats["events"],
                "validation": plan_validation,
            },
            "noticias": {
                "output": "outputs/noticias_madrid_all.json",
                "web_output": "outputs/noticias_web.json",
                "count": len(merged_news),
                "web_count": web_stats["news"],
                "validation": news_validation,
            },
        },
    }


def run_all(
    *,
    trigger_type: str = "scheduled",
    trigger_schedule: str = "15 4 * * * UTC",
    trigger_source: str = "local",
    fever_mode: str = "full",
    merge_only: bool = False,
    geocode: bool = True,
) -> dict:
    if fever_mode not in {"full", "fast"}:
        raise ValueError(f"Unsupported fever mode: {fever_mode}")

    started_at = utc_now_iso()
    started_clock = time.time()
    results: list[dict] = []

    if not merge_only:
        log.info("=" * 60)
        log.info("PIPELINE MADPLAN — %d scrapers (%d en paralelo, fever=%s)",
                 len(SCRAPER_JOBS), MAX_PARALLEL_SCRAPERS, fever_mode)
        log.info("=" * 60)
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SCRAPERS) as executor:
            futures = {
                executor.submit(_execute_job, job, fever_mode=fever_mode): job
                for job in SCRAPER_JOBS
            }
            for future in as_completed(futures):
                outcome = future.result()
                results.append(outcome)
                marker = "OK " if outcome["status"] == "ok" else "FAIL"
                log.info("%s %-30s %4d items (%.0fs)", marker, outcome["name"],
                         outcome["count"], outcome["duration_seconds"])
        results.sort(key=lambda item: item["name"])

    feeds = merge_and_publish(results or None, geocode=geocode)

    manifest = {
        "trigger": {
            "type": trigger_type if not merge_only else "merge-only",
            "source": trigger_source,
            "schedule": trigger_schedule if not merge_only else None,
            "fever_mode": fever_mode if not merge_only else None,
        },
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "duration_seconds": round(time.time() - started_clock, 1),
        "sources": feeds["sources"],
        "feeds": feeds["feeds"],
    }
    RUN_MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    ok_sources = sum(1 for s in feeds["sources"] if s.get("status") == "ok")
    log.info("=" * 60)
    log.info("Fuentes OK: %d/%d | Planes web: %d | Noticias web: %d",
             ok_sources, len(feeds["sources"]),
             manifest["feeds"]["planes"]["web_count"],
             manifest["feeds"]["noticias"]["web_count"])
    log.info("Manifest: %s", RUN_MANIFEST_FILE)
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MadPlan scraping pipeline")
    parser.add_argument("--merge-only", action="store_true",
                        help="Skip scraping; rebuild feeds from existing per-source outputs")
    parser.add_argument("--no-geocode", action="store_true",
                        help="Skip the geocoding pass")
    parser.add_argument("--fever-mode", choices=("full", "fast"),
                        default=os.getenv("MAD_PLAN_FEVER_MODE", "full"))
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_all(
        trigger_type="manual",
        trigger_source="cli",
        fever_mode=args.fever_mode,
        merge_only=args.merge_only,
        geocode=not args.no_geocode,
    )
