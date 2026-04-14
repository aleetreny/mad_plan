#!/usr/bin/env python3
"""
Assign placeholder images to events that don't have photos.

Uses category-based Unsplash image URLs so events look good even without
a specific image from the source. These are static, curated URLs that
are fast and reliable.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS_FILE = ROOT / "outputs" / "eventos_madrid_all.json"

# Category -> list of Unsplash random image search URLs
# Using Unsplash Source API with Madrid-related imagery
CATEGORY_IMAGES: dict[str, list[str]] = {
    "Música y Conciertos": [
        "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=600&h=400&fit=crop",
    ],
    "Arte y Exposiciones": [
        "https://images.unsplash.com/photo-1536924940846-227afb31e2a5?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1561214115-f2f134cc4912?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1541367777708-7905fe3296c0?w=600&h=400&fit=crop",
    ],
    "Teatro y Danza": [
        "https://images.unsplash.com/photo-1503095396549-807759245b35?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1460881680858-30d872d5b530?w=600&h=400&fit=crop",
    ],
    "Cine": [
        "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1440404653325-ab127d49abc1?w=600&h=400&fit=crop",
    ],
    "Gastronomía": [
        "https://images.unsplash.com/photo-1515443961218-a51367888e4b?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=400&fit=crop",
    ],
    "Deportes y Aventura": [
        "https://images.unsplash.com/photo-1461896836934-bd45ba8a1c16?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1552674605-db6ffd4facb5?w=600&h=400&fit=crop",
    ],
    "Vida Nocturna": [
        "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=600&h=400&fit=crop",
    ],
    "Familia e Infantil": [
        "https://images.unsplash.com/photo-1544776193-352d25ca82cd?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1472162072942-cd5147eb3902?w=600&h=400&fit=crop",
    ],
    "Talleres y Cursos": [
        "https://images.unsplash.com/photo-1544928147-79a2dbc1f389?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600&h=400&fit=crop",
    ],
    "Conferencias y Charlas": [
        "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1475721027785-f74eccf877e2?w=600&h=400&fit=crop",
    ],
    "Naturaleza y Aire Libre": [
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=600&h=400&fit=crop",
    ],
    "Bienestar y Salud": [
        "https://images.unsplash.com/photo-1545205597-3d9d02c29597?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=600&h=400&fit=crop",
    ],
    "Visitas y Rutas": [
        "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1543783207-ec64e4d95325?w=600&h=400&fit=crop",
    ],
    "Ciencia y Tecnología": [
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&h=400&fit=crop",
    ],
    "Mercados y Ferias": [
        "https://images.unsplash.com/photo-1533900298318-6b8da08a523e?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&h=400&fit=crop",
    ],
    "Comunidad y Social": [
        "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?w=600&h=400&fit=crop",
    ],
    "Lectura y Literatura": [
        "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=600&h=400&fit=crop",
    ],
    "Ocio y Entretenimiento": [
        "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=600&h=400&fit=crop",
        "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=600&h=400&fit=crop",
    ],
}

# Default fallback for Madrid
DEFAULT_IMAGES = [
    "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1543783207-ec64e4d95325?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=600&h=400&fit=crop",
]


def _pick_image(images: list[str], seed: str) -> str:
    """Deterministic pick so the same event always gets the same placeholder."""
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(images)
    return images[idx]


def assign_placeholders(events: list[dict]) -> int:
    count = 0
    for event in events:
        if event.get("imagen"):
            continue
        # Find category-based image
        cat = (
            event.get("categoria_principal_norm")
            or (event.get("categorias_normalizadas") or [None])[0]
            or event.get("categoria_principal")
        )
        images = CATEGORY_IMAGES.get(cat, DEFAULT_IMAGES) if cat else DEFAULT_IMAGES
        seed = event.get("id", event.get("titulo", str(count)))
        event["imagen"] = _pick_image(images, seed)
        event["imagen_placeholder"] = True  # flag it as placeholder
        count += 1
    return count


def run():
    events = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    n = assign_placeholders(events)
    EVENTS_FILE.write_text(
        json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    total_with = sum(1 for e in events if e.get("imagen"))
    print(f"Assigned {n} placeholder images")
    print(f"Total events with images: {total_with}/{len(events)}")


if __name__ == "__main__":
    run()
