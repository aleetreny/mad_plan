"""Keep the freshest non-empty snapshot for CI-blocked sources.

Some sources (Eventbrite, Ticketmaster, BNE) block datacenter IPs, so GitHub
Actions relies on versioned fallback outputs. This script compares the file
on disk (possibly restored from actions/cache) against the committed version
and keeps whichever has the most recent `scraped_en` — never an empty one.

Runs in CI after the cache restore and again before the data commit.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FALLBACK_FILES = [
    "outputs/eventos_eventbrite.json",
    "outputs/eventos_ticketmaster.json",
    "outputs/eventos_biblioteca_nacional.json",
]


def freshness(raw: str | None) -> str | None:
    """Newest scraped_en in a JSON list, or None if empty/invalid."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    return max((record.get("scraped_en") or "" for record in data), default="") or None


def reconcile() -> None:
    for path in FALLBACK_FILES:
        file = ROOT / path
        current = freshness(file.read_text(encoding="utf-8")) if file.exists() else None
        show = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        committed = freshness(show.stdout) if show.returncode == 0 else None

        if committed and (current is None or committed > current):
            subprocess.run(["git", "checkout", "HEAD", "--", path], check=True, cwd=ROOT)
            print(f"{path}: restaurado desde git (git {committed} > disco {current})")
        else:
            print(f"{path}: se mantiene el de disco (disco {current}, git {committed})")


if __name__ == "__main__":
    reconcile()
