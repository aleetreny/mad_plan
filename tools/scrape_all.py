"""Run all scrapers, merge them into web feeds and emit a daily-run manifest."""

import copy
import importlib
import json
import logging
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
except ImportError:
    from normalization import (
        merge_news_records,
        merge_plan_records,
        utc_now_iso,
        validate_news_records,
        validate_plan_records,
    )

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "eventos_madrid_all.json"
NEWS_OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "noticias_madrid_all.json"
RUN_MANIFEST_FILE = Path(__file__).resolve().parent.parent / "outputs" / "pipeline_diario.json"

BASE_SCRAPER_JOBS = [
    {
        "name": "matadero",
        "kind": "plan",
        "import": "matadero",
        "callable": "scrape_matadero",
        "output": "outputs/eventos_matadero.json",
    },
    {
        "name": "teatros_canal",
        "kind": "plan",
        "import": "teatros_canal",
        "callable": "scrape_teatros_canal",
        "output": "outputs/eventos_teatros_canal.json",
    },
    {
        "name": "circulo_bellas_artes",
        "kind": "plan",
        "import": "circulo_bellas_artes",
        "callable": "scrape_circulo_bellas_artes",
        "output": "outputs/eventos_circulo_bellas_artes.json",
    },
    {
        "name": "ifema_madrid",
        "kind": "plan",
        "import": "ifema_madrid",
        "callable": "scrape_ifema_madrid",
        "output": "outputs/eventos_ifema_madrid.json",
    },
    {
        "name": "casa_mexico",
        "kind": "plan",
        "import": "casa_mexico",
        "callable": "scrape_casa_mexico",
        "output": "outputs/eventos_casa_mexico.json",
    },
    {
        "name": "espacio_fundacion_telefonica",
        "kind": "plan",
        "import": "espacio_fundacion_telefonica",
        "callable": "scrape_espacio_fundacion_telefonica",
        "output": "outputs/eventos_espacio_fundacion_telefonica.json",
    },
    {
        "name": "museo_reina_sofia",
        "kind": "plan",
        "import": "museo_reina_sofia",
        "callable": "scrape_museo_reina_sofia",
        "output": "outputs/eventos_museo_reina_sofia.json",
    },
    {
        "name": "biblioteca_nacional",
        "kind": "plan",
        "import": "biblioteca_nacional",
        "callable": "scrape_biblioteca_nacional",
        "output": "outputs/eventos_biblioteca_nacional.json",
    },
    {
        "name": "fundacion_canal",
        "kind": "plan",
        "import": "fundacion_canal",
        "callable": "scrape_fundacion_canal",
        "output": "outputs/eventos_fundacion_canal.json",
    },
    {
        "name": "fundacion_mapfre",
        "kind": "plan",
        "import": "fundacion_mapfre",
        "callable": "scrape_fundacion_mapfre",
        "output": "outputs/eventos_fundacion_mapfre.json",
    },
    {
        "name": "sala_el_sol",
        "kind": "plan",
        "import": "sala_el_sol",
        "callable": "scrape_sala_el_sol",
        "output": "outputs/eventos_sala_el_sol.json",
    },
    {
        "name": "fever",
        "kind": "plan",
        "import": "fever",
        "callable": "main",
        "output": "outputs/eventos_fever.json",
    },
    {
        "name": "eventbrite",
        "kind": "plan",
        "import": "eventbrite",
        "callable": "scrape_eventbrite",
        "output": "outputs/eventos_eventbrite.json",
    },
    {
        "name": "wegow",
        "kind": "plan",
        "import": "wegow",
        "callable": "scrape_wegow",
        "output": "outputs/eventos_wegow.json",
    },
    {
        "name": "ticketmaster",
        "kind": "plan",
        "import": "ticketmaster",
        "callable": "scrape_ticketmaster_madrid",
        "output": "outputs/eventos_ticketmaster.json",
    },
    {
        "name": "datos_madrid",
        "kind": "plan",
        "import": "datos_madrid",
        "callable": "scrape_datos_madrid",
        "output": "outputs/eventos_datos_madrid.json",
    },
    {
        "name": "esmadrid",
        "kind": "plan",
        "import": "esmadrid",
        "callable": "scrape_esmadrid",
        "output": "outputs/eventos_esmadrid.json",
    },
    {
        "name": "madrid_secreto",
        "kind": "plan",
        "import": "madrid_secreto",
        "callable": "scrape_madrid_secreto",
        "output": "outputs/eventos_madrid_secreto.json",
    },
    {
        "name": "rockthesport",
        "kind": "plan",
        "import": "rockthesport",
        "callable": "scrape_rockthesport",
        "output": "outputs/eventos_rockthesport.json",
    },
    {
        "name": "meetup",
        "kind": "plan",
        "import": "meetup",
        "callable": "scrape_meetup",
        "output": "outputs/eventos_meetup.json",
    },
    {
        "name": "timeout",
        "kind": "news",
        "import": "timeout",
        "callable": "scrape_timeout_news",
        "output": "outputs/noticias_timeout.json",
    },
    {
        "name": "gacetin_madrid",
        "kind": "news",
        "import": "gacetin_madrid",
        "callable": "scrape_gacetin_madrid_news",
        "output": "outputs/noticias_gacetin_madrid.json",
    },
]


def _build_scraper_jobs(*, fever_mode: str) -> list[dict]:
    jobs = copy.deepcopy(BASE_SCRAPER_JOBS)
    for job in jobs:
        if job["name"] == "fever":
            job["callable"] = "main" if fever_mode == "full" else "fast_main"
            break
    return jobs


def _import_callable(module_name: str, callable_name: str):
    candidates = [module_name]
    if __package__:
        candidates.insert(0, f"{__package__}.{module_name}")

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            module = importlib.import_module(candidate)
            return getattr(module, callable_name)
        except ModuleNotFoundError as error:
            last_error = error
            if error.name != candidate:
                raise

    if last_error:
        raise last_error
    raise ModuleNotFoundError(module_name)


def _run_job(job: dict) -> dict:
    started_at = utc_now_iso()
    try:
        scraper = _import_callable(job["import"], job["callable"])
        records = scraper()
        finished_at = utc_now_iso()
        return {
            "name": job["name"],
            "kind": job["kind"],
            "status": "ok",
            "count": len(records),
            "records": records,
            "output": job["output"],
            "started_at": started_at,
            "finished_at": finished_at,
        }
    except Exception as error:
        finished_at = utc_now_iso()
        return {
            "name": job["name"],
            "kind": job["kind"],
            "status": "error",
            "count": 0,
            "records": [],
            "output": job["output"],
            "started_at": started_at,
            "finished_at": finished_at,
            "error": str(error),
        }


def run_all(
    *,
    trigger_type: str = "scheduled",
    trigger_schedule: str = "0 6 * * * Europe/Madrid",
    trigger_source: str = "simulated-cron",
    fever_mode: str = "full",
):
    if fever_mode not in {"full", "fast"}:
        raise ValueError(f"Unsupported fever mode: {fever_mode}")

    scraper_jobs = _build_scraper_jobs(fever_mode=fever_mode)
    started_at = time.time()
    log.info("=" * 60)
    log.info("PIPELINE DIARIO")
    log.info("=" * 60)
    log.info(
        "Trigger %s (%s) lanzando %d scrapers en paralelo",
        trigger_source,
        trigger_schedule,
        len(scraper_jobs),
    )
    log.info("Fever mode for this run: %s", fever_mode)

    results: list[dict] = []
    source_events: list[dict] = []
    source_news: list[dict] = []

    with ThreadPoolExecutor(max_workers=len(scraper_jobs)) as executor:
        futures = {executor.submit(_run_job, job): job for job in scraper_jobs}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result["status"] == "ok":
                if result["kind"] == "plan":
                    source_events.extend(result["records"])
                else:
                    source_news.extend(result["records"])
                log.info("%-15s: %4d items", result["name"], result["count"])
            else:
                log.error("%-15s: failed - %s", result["name"], result.get("error"))

    merged_events = merge_plan_records(source_events)
    merged_news = merge_news_records(source_news)

    OUTPUT_FILE.write_text(
        json.dumps(merged_events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    NEWS_OUTPUT_FILE.write_text(
        json.dumps(merged_news, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    plan_validation = validate_plan_records(merged_events)
    news_validation = validate_news_records(merged_news)
    duration_seconds = round(time.time() - started_at, 2)

    manifest = {
        "trigger": {
            "type": trigger_type,
            "source": trigger_source,
            "schedule": trigger_schedule,
            "simulated_at": utc_now_iso(),
            "fever_mode": fever_mode,
        },
        "started_at": results[0]["started_at"] if results else utc_now_iso(),
        "finished_at": utc_now_iso(),
        "duration_seconds": duration_seconds,
        "sources": [
            {
                "name": result["name"],
                "kind": result["kind"],
                "status": result["status"],
                "count": result["count"],
                "output": result["output"],
                "started_at": result["started_at"],
                "finished_at": result["finished_at"],
                "error": result.get("error"),
            }
            for result in sorted(results, key=lambda item: item["name"])
        ],
        "feeds": {
            "planes": {
                "output": str(OUTPUT_FILE.relative_to(OUTPUT_FILE.parent.parent)),
                "count": len(merged_events),
                "validation": plan_validation,
            },
            "noticias": {
                "output": str(NEWS_OUTPUT_FILE.relative_to(NEWS_OUTPUT_FILE.parent.parent)),
                "count": len(merged_news),
                "validation": news_validation,
            },
        },
    }
    RUN_MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    log.info("=" * 60)
    log.info("PLANES WEB")
    log.info("=" * 60)
    log.info("Items finales: %d", len(merged_events))
    log.info("Validacion: %s", "OK" if plan_validation["valid"] else "ERROR")
    log.info("Saved to %s", OUTPUT_FILE)
    log.info("=" * 60)
    log.info("NOTICIAS WEB")
    log.info("=" * 60)
    log.info("Items finales: %d", len(merged_news))
    log.info("Validacion: %s", "OK" if news_validation["valid"] else "ERROR")
    log.info("Saved to %s", NEWS_OUTPUT_FILE)
    log.info("Manifest saved to %s", RUN_MANIFEST_FILE)

    return {
        "plans": merged_events,
        "news": merged_news,
        "manifest": manifest,
    }


if __name__ == "__main__":
    run_all()
