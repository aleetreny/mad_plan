"""Rebuild merged web feeds from existing source outputs."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from .normalization import (
        merge_news_records,
        merge_plan_records,
        utc_now_iso,
        validate_news_records,
        validate_plan_records,
    )
    from .scrape_all import (
        BASE_SCRAPER_JOBS,
        NEWS_OUTPUT_FILE,
        OUTPUT_FILE,
        RUN_MANIFEST_FILE,
    )
except ImportError:
    from normalization import (
        merge_news_records,
        merge_plan_records,
        utc_now_iso,
        validate_news_records,
        validate_plan_records,
    )
    from scrape_all import (
        BASE_SCRAPER_JOBS,
        NEWS_OUTPUT_FILE,
        OUTPUT_FILE,
        RUN_MANIFEST_FILE,
    )


ROOT = Path(__file__).resolve().parent.parent


def _load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def rebuild_feeds() -> dict:
    started_at = utc_now_iso()
    plan_records: list[dict] = []
    news_records: list[dict] = []
    sources: list[dict] = []

    for job in BASE_SCRAPER_JOBS:
        output_path = ROOT / job["output"]
        records = _load_records(output_path)
        if job["kind"] == "plan":
            plan_records.extend(records)
        else:
            news_records.extend(records)

        sources.append(
            {
                "name": job["name"],
                "kind": job["kind"],
                "status": "ok" if output_path.exists() else "missing",
                "count": len(records),
                "output": job["output"],
            }
        )

    merged_events = merge_plan_records(plan_records)
    merged_news = merge_news_records(news_records)

    OUTPUT_FILE.write_text(
        json.dumps(merged_events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    NEWS_OUTPUT_FILE.write_text(
        json.dumps(merged_news, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    manifest = {
        "trigger": {
            "type": "manual-rebuild",
            "source": "existing-outputs",
            "schedule": None,
            "simulated_at": utc_now_iso(),
            "fever_mode": None,
        },
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "sources": sources,
        "feeds": {
            "planes": {
                "output": str(OUTPUT_FILE.relative_to(ROOT)),
                "count": len(merged_events),
                "validation": validate_plan_records(merged_events),
            },
            "noticias": {
                "output": str(NEWS_OUTPUT_FILE.relative_to(ROOT)),
                "count": len(merged_news),
                "validation": validate_news_records(merged_news),
            },
        },
    }
    RUN_MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    result = rebuild_feeds()
    print(
        json.dumps(
            {
                "planes": result["feeds"]["planes"]["count"],
                "noticias": result["feeds"]["noticias"]["count"],
                "valid_planes": result["feeds"]["planes"]["validation"]["valid"],
                "valid_news": result["feeds"]["noticias"]["validation"]["valid"],
            },
            ensure_ascii=False,
        )
    )