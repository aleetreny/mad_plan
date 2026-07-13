"""Scheduled entry point for the Madrid scraping pipeline."""

from __future__ import annotations

import argparse
import os

try:
    from .scrape_all import run_all
except ImportError:
    from scrape_all import run_all


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the scheduled Madrid scrape")
    parser.add_argument(
        "--trigger-type",
        default=os.getenv("MAD_PLAN_TRIGGER_TYPE", "scheduled"),
        help="Trigger type stored in the run manifest",
    )
    parser.add_argument(
        "--trigger-source",
        default=os.getenv("MAD_PLAN_TRIGGER_SOURCE", "local"),
        help="Trigger source stored in the run manifest",
    )
    parser.add_argument(
        "--trigger-schedule",
        default=os.getenv("MAD_PLAN_TRIGGER_SCHEDULE", "15 4 * * * UTC"),
        help="Schedule label stored in the run manifest",
    )
    parser.add_argument(
        "--fever-mode",
        choices=("full", "fast"),
        default=os.getenv("MAD_PLAN_FEVER_MODE", "full"),
        help="Whether Fever runs in full or fast mode",
    )
    parser.add_argument(
        "--no-geocode",
        action="store_true",
        help="Skip the geocoding pass",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_all(
        trigger_type=args.trigger_type,
        trigger_schedule=args.trigger_schedule,
        trigger_source=args.trigger_source,
        fever_mode=args.fever_mode,
        geocode=not args.no_geocode,
    )
