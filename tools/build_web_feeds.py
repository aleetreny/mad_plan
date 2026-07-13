"""Build the slim, minified JSON feeds consumed by the MadPlan frontend.

The merged archive feeds (`eventos_madrid_all.json`) keep every field for
debugging, but the web only needs a fraction of them. This module produces
`eventos_web.json` and `noticias_web.json`: current records only, capped text,
capped sessions and no placeholder images — roughly 4x smaller on disk.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

try:
    from .normalization import is_current_plan_record, is_recent_news_record
except ImportError:
    from normalization import is_current_plan_record, is_recent_news_record

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT / "outputs"
EVENTS_WEB_FILE = OUTPUTS_DIR / "eventos_web.json"
NEWS_WEB_FILE = OUTPUTS_DIR / "noticias_web.json"

SUMMARY_MAX_CHARS = 260
DESCRIPTION_MAX_CHARS = 900
MAX_SESSIONS = 8
MAX_SOURCE_LINKS = 6

PLACEHOLDER_IMAGE_TOKENS = ("images.unsplash.com", "source.unsplash.com")


def strip_placeholder_images(events: list[dict]) -> int:
    """Remove legacy Unsplash placeholder images so covers stay honest."""
    stripped = 0
    for event in events:
        image = event.get("imagen") or ""
        if event.get("imagen_placeholder") or any(
            token in image for token in PLACEHOLDER_IMAGE_TOKENS
        ):
            event["imagen"] = None
            event.pop("imagen_placeholder", None)
            stripped += 1
    return stripped


def _cap(text: Any, limit: int) -> str | None:
    if not text:
        return None
    value = " ".join(str(text).split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rsplit(" ", 1)[0] + "…"


def _round_coord(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 5)
    except (TypeError, ValueError):
        return None


def _slim_sessions(event: dict, today: date) -> list[dict]:
    sessions = event.get("sesiones") or []
    future = [
        session
        for session in sessions
        if isinstance(session, dict)
        and (session.get("fecha") or "") >= today.isoformat()
    ]
    return (future or sessions[-1:])[:MAX_SESSIONS]


def _slim_source_links(event: dict) -> list[dict]:
    metadata = event.get("metadata") or {}
    links = metadata.get("source_links") or []
    slim: list[dict] = []
    for link in links[:MAX_SOURCE_LINKS]:
        if not isinstance(link, dict) or not link.get("url"):
            continue
        slim.append(
            {
                "fuente": link.get("fuente"),
                "url": link.get("url"),
                "kind": link.get("kind") or "detalle",
                "precio": link.get("precio"),
                "es_gratis": link.get("es_gratis"),
            }
        )
    return slim


def slim_event(event: dict, today: date) -> dict:
    resumen = _cap(event.get("resumen"), SUMMARY_MAX_CHARS)
    titulo = (event.get("titulo") or "").strip()
    if resumen and titulo and resumen.casefold().rstrip(".…") == titulo.casefold().rstrip("."):
        resumen = None

    contenido = event.get("contenido") or ""
    descripcion = event.get("descripcion") or ""
    body = contenido if len(contenido) > len(descripcion) else descripcion
    body_capped = _cap(body, DESCRIPTION_MAX_CHARS)
    if body_capped and titulo and body_capped.casefold().rstrip(".…") == titulo.casefold().rstrip("."):
        body_capped = None

    metadata = event.get("metadata") or {}
    related_sources = event.get("fuentes_relacionadas") or []

    slim = {
        "id": event.get("id"),
        "titulo": titulo,
        "subtitulo": _cap(event.get("subtitulo"), SUMMARY_MAX_CHARS),
        "resumen": resumen,
        "descripcion": body_capped,
        "imagen": event.get("imagen") or None,
        "fuente": event.get("fuente"),
        "fuentes_relacionadas": related_sources if len(related_sources) > 1 else None,
        "categorias_normalizadas": event.get("categorias_normalizadas") or [],
        "categoria_principal_norm": event.get("categoria_principal_norm"),
        "url": event.get("url") or None,
        "url_compra": event.get("url_compra") or None,
        "lugar": event.get("lugar") or None,
        "direccion": event.get("direccion") or None,
        "latitud": _round_coord(event.get("latitud")),
        "longitud": _round_coord(event.get("longitud")),
        "precio": event.get("precio"),
        "moneda": event.get("moneda"),
        "es_gratis": event.get("es_gratis"),
        "modo_fecha": event.get("modo_fecha"),
        "estado_temporal": event.get("estado_temporal"),
        "fecha_inicio": event.get("fecha_inicio"),
        "fecha_fin": event.get("fecha_fin"),
        "datetime_inicio": event.get("datetime_inicio"),
        "proxima_fecha": event.get("proxima_fecha"),
        "proximo_datetime": event.get("proximo_datetime"),
        "sort_datetime": event.get("sort_datetime"),
        "vigente_hasta": event.get("vigente_hasta"),
        "sesiones": _slim_sessions(event, today),
        "source_links": _slim_source_links(event),
        "valoracion": metadata.get("valoracion"),
    }
    return {key: value for key, value in slim.items() if value not in (None, [], "")}


def slim_news(item: dict) -> dict:
    slim = {
        "id": item.get("id"),
        "titulo": (item.get("titulo") or "").strip(),
        "resumen": _cap(item.get("resumen"), 280),
        "imagen": item.get("imagen") or None,
        "fuente": item.get("fuente"),
        "categoria_principal_norm": item.get("categoria_principal_norm"),
        "url": item.get("url") or None,
        "publicado_en": item.get("publicado_en"),
        "sort_datetime": item.get("sort_datetime"),
    }
    return {key: value for key, value in slim.items() if value not in (None, "")}


def build_web_feeds(events: list[dict], news: list[dict]) -> dict:
    today = date.today()

    current_events = [
        slim_event(event, today)
        for event in events
        if is_current_plan_record(event, today=today)
    ]
    recent_news = [slim_news(item) for item in news if is_recent_news_record(item)]

    EVENTS_WEB_FILE.write_text(
        json.dumps(current_events, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    NEWS_WEB_FILE.write_text(
        json.dumps(recent_news, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return {"events": len(current_events), "news": len(recent_news)}


if __name__ == "__main__":
    events_source = OUTPUTS_DIR / "eventos_madrid_all.json"
    news_source = OUTPUTS_DIR / "noticias_madrid_all.json"
    events = json.loads(events_source.read_text(encoding="utf-8")) if events_source.exists() else []
    news = json.loads(news_source.read_text(encoding="utf-8")) if news_source.exists() else []
    stats = build_web_feeds(events, news)
    print(json.dumps(stats))
