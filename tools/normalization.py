"""Shared normalization and validation helpers for Madrid feeds."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import re
import unicodedata
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

MADRID_TZ = ZoneInfo("Europe/Madrid")
PLAN_LOOKAHEAD_DAYS = 365
PLAN_UNDATED_LOOKBACK_DAYS = 45
NEWS_LOOKBACK_DAYS = 21

SOURCE_PRIORITY = {
    "matadero": -1,
    "teatros_canal": -1,
    "circulo_bellas_artes": -1,
    "ifema_madrid": -1,
    "casa_mexico": -1,
    "espacio_fundacion_telefonica": -1,
    "museo_reina_sofia": -1,
    "biblioteca_nacional": -1,
    "fundacion_canal": -1,
    "fundacion_mapfre": -1,
    "sala_el_sol": -1,
    "datos_madrid": 0,
    "esmadrid": 0,
    "fever": 1,
    "eventbrite": 2,
    "wegow": 3,
    "ticketmaster": 4,
    "madrid_secreto": 5,
    "timeout": 6,
}

GENERIC_PLAN_SOURCE_IDS = {
    "madrid-secreto",
    "madrid secreto",
    "plan",
    "evento",
    "event",
}

DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_PRESENT_RE = re.compile(r"\d{2}:\d{2}")
EXPLICIT_TIMEZONE_RE = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split())


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "madrid-item"


def _dedupe_strings(values: list[Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(text)
    return ordered


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _infer_source_id(item: dict[str, Any]) -> str:
    raw_id = item.get("id")
    if raw_id not in (None, ""):
        return _clean_text(raw_id)

    for field in ("url", "url_articulo", "url_compra"):
        value = item.get(field)
        if not value:
            continue
        path = urlparse(str(value)).path.rstrip("/")
        if path:
            return path.rsplit("/", 1)[-1]

    title = item.get("titulo") or item.get("headline") or item.get("name")
    return _slugify(_clean_text(title))


def _infer_plan_source_id(item: dict[str, Any]) -> str:
    raw_id = _clean_text(item.get("fuente_id") or item.get("id"))
    if raw_id.startswith(("plan:", "noticia:")):
        raw_id = raw_id.split(":", 2)[-1]
    if raw_id and raw_id.casefold() not in GENERIC_PLAN_SOURCE_IDS:
        return raw_id

    parts: list[str] = []
    seen: set[str] = set()

    for field in ("url_compra", "url", "url_articulo"):
        value = item.get(field)
        if not value:
            continue
        path = urlparse(str(value)).path.rstrip("/")
        if not path:
            continue
        candidate = path.rsplit("/", 1)[-1]
        key = candidate.casefold()
        if key in seen or not candidate:
            continue
        seen.add(key)
        parts.append(candidate)

    title_slug = _slugify(_clean_text(item.get("titulo")))
    if title_slug and title_slug.casefold() not in seen:
        seen.add(title_slug.casefold())
        parts.append(title_slug)

    for field in ("fecha_inicio", "fecha_fin", "fecha_publicacion"):
        value = _clean_text(item.get(field))
        if not value:
            continue
        candidate = value.split("T", 1)[0].split(" ", 1)[0]
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        parts.append(candidate)

    if raw_id and raw_id.casefold() not in seen:
        parts.insert(0, raw_id)

    return "::".join(parts) if parts else _infer_source_id(item)


def _build_compound_id(kind: str, source: str, source_id: str) -> str:
    return f"{kind}:{source}:{source_id}"


def _parse_temporal(value: Any) -> dict[str, Any] | None:
    text = _clean_text(value)
    if not text:
        return None

    has_time = bool(TIME_PRESENT_RE.search(text) or "T" in text)
    parsed: datetime | None = None

    if DATE_ONLY_RE.fullmatch(text):
        parsed = datetime.combine(date.fromisoformat(text), time.min, MADRID_TZ)
        has_time = False
    else:
        normalized = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            for fmt in (
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M",
            ):
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue

        if parsed is None:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=MADRID_TZ)
        else:
            parsed = parsed.astimezone(MADRID_TZ)

        if has_time and parsed.timetz().replace(tzinfo=None) in {
            time.min,
            time(23, 59),
            time(23, 59, 59),
        } and not EXPLICIT_TIMEZONE_RE.search(text):
            has_time = False

    return {
        "raw": text,
        "dt": parsed,
        "date": parsed.date(),
        "has_time": has_time,
        "datetime_iso": parsed.replace(microsecond=0).isoformat(),
    }


def _normalize_datetime_field(value: Any) -> str | None:
    parsed = _parse_temporal(value)
    if not parsed:
        return None
    return parsed["datetime_iso"]


def _collect_parsed_sessions(item: dict[str, Any]) -> list[dict[str, Any]]:
    raw_values: list[Any] = []
    raw_dates = item.get("fechas_disponibles") or []
    if isinstance(raw_dates, list):
        raw_values.extend(raw_dates)
    elif raw_dates:
        raw_values.append(raw_dates)

    if not raw_values:
        for fallback in (item.get("fecha_inicio"), item.get("fecha_fin")):
            if fallback:
                raw_values.append(fallback)

    grouped_by_date: dict[str, list[dict[str, Any]]] = {}
    for raw_value in raw_values:
        parsed = _parse_temporal(raw_value)
        if not parsed:
            continue
        date_key = parsed["date"].isoformat()
        grouped_by_date.setdefault(date_key, []).append(parsed)

    sessions: list[dict[str, Any]] = []
    for date_key in sorted(grouped_by_date):
        group = grouped_by_date[date_key]
        timed = [parsed for parsed in group if parsed["has_time"]]
        if timed:
            unique_by_datetime: dict[str, dict[str, Any]] = {}
            for parsed in timed:
                unique_by_datetime[parsed["datetime_iso"]] = parsed
            sessions.extend(sorted(unique_by_datetime.values(), key=lambda parsed: parsed["dt"]))
            continue

        sessions.append(group[0])

    return sessions


def _session_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "fecha": parsed["date"].isoformat(),
        "datetime": parsed["datetime_iso"] if parsed["has_time"] else None,
        "tiene_hora": parsed["has_time"],
    }


def _effective_end_iso(parsed: dict[str, Any] | None) -> str | None:
    if not parsed:
        return None

    if parsed["has_time"]:
        return parsed["datetime_iso"]

    end_of_day = datetime.combine(parsed["date"], time(23, 59, 59), MADRID_TZ)
    return end_of_day.isoformat()


def _start_of_day_iso(target_day: date) -> str:
    return datetime.combine(target_day, time.min, MADRID_TZ).isoformat()


def _parsed_temporal_from_day(target_day: date) -> dict[str, Any]:
    start_of_day = datetime.combine(target_day, time.min, MADRID_TZ)
    return {
        "raw": target_day.isoformat(),
        "dt": start_of_day,
        "date": target_day,
        "has_time": False,
        "datetime_iso": start_of_day.isoformat(),
    }


def _select_output_sessions(
    sessions: list[dict[str, Any]], *, today: date
) -> list[dict[str, Any]]:
    if len(sessions) <= 2:
        return sessions

    future_sessions = [session for session in sessions if session["date"] >= today]
    return future_sessions or sessions[-1:]


def _next_relevant_temporal(
    *,
    start: dict[str, Any] | None,
    end: dict[str, Any] | None,
    all_sessions: list[dict[str, Any]],
    today: date,
) -> dict[str, Any] | None:
    future_sessions = [session for session in all_sessions if session["date"] >= today]
    if future_sessions:
        return future_sessions[0]

    if start and end and start["date"] <= today <= end["date"]:
        return _parsed_temporal_from_day(today)

    if start and start["date"] >= today:
        return start

    if end and end["date"] >= today:
        return _parsed_temporal_from_day(today)

    return None


def _extract_category_values(item: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    categories = item.get("categorias")
    if isinstance(categories, list):
        values.extend(categories)
    elif categories:
        values.append(categories)

    category = item.get("categoria")
    if category:
        values.insert(0, category)

    return _dedupe_strings(values)


def _extract_tag_values(item: dict[str, Any]) -> list[str]:
    tags = item.get("etiquetas")
    if isinstance(tags, list):
        return _dedupe_strings(tags)
    if tags:
        return _dedupe_strings([tags])
    return []


def _build_summary(item: dict[str, Any]) -> str:
    for key in ("subtitulo", "descripcion", "contenido"):
        text = _clean_text(item.get(key))
        if text:
            return text[:320]
    return _clean_text(item.get("titulo"))[:320]


def _collect_source_metadata(item: dict[str, Any], *, kind: str) -> dict[str, Any]:
    allowed_keys = {
        "tipo_origen",
        "url_fuente_editorial",
        "valoracion",
        "num_valoraciones",
        "secciones",
    }
    metadata: dict[str, Any] = {}
    for key in allowed_keys:
        value = item.get(key)
        if value in (None, "", []):
            continue
        metadata[key] = value

    if kind == "noticia" and item.get("categoria"):
        metadata["categoria_original"] = item.get("categoria")

    return metadata


def _plan_mode(
    start: dict[str, Any] | None,
    end: dict[str, Any] | None,
    sessions: list[dict[str, Any]],
) -> str:
    if not start and not end and not sessions:
        return "sin_fecha"

    if start and end and start["date"] != end["date"]:
        if len(sessions) <= 2:
            return "rango"
        return "multiple"

    if len(sessions) > 1:
        return "multiple"

    reference = start or end or sessions[0]
    if reference["has_time"]:
        return "puntual_con_hora"
    return "puntual"


def _plan_temporal_status(
    start: dict[str, Any] | None,
    end: dict[str, Any] | None,
    *,
    today: date | None = None,
) -> str:
    today = today or date.today()
    if not start and not end:
        return "sin_fecha"

    first_day = (start or end)["date"]
    last_day = (end or start)["date"]
    if last_day < today:
        return "pasado"
    if first_day <= today <= last_day:
        return "en_curso"
    return "proximo"


def _plan_sort_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dated = [record for record in records if record.get("modo_fecha") != "sin_fecha"]
    undated = [record for record in records if record.get("modo_fecha") == "sin_fecha"]

    dated.sort(
        key=lambda record: (
            record.get("sort_datetime") or "",
            _clean_text(record.get("titulo")).casefold(),
        )
    )
    undated.sort(
        key=lambda record: (
            record.get("actualizado_en") or record.get("publicado_en") or "",
            _clean_text(record.get("titulo")).casefold(),
        ),
        reverse=True,
    )
    return dated + undated


def is_current_plan_record(
    record: dict[str, Any],
    *,
    today: date | None = None,
    max_future_days: int = PLAN_LOOKAHEAD_DAYS,
    undated_lookback_days: int = PLAN_UNDATED_LOOKBACK_DAYS,
) -> bool:
    today = today or date.today()
    horizon = today + timedelta(days=max_future_days)

    first_day = record.get("fecha_inicio") or record.get("fecha_fin")
    last_day = record.get("fecha_fin") or record.get("fecha_inicio")
    if first_day or last_day:
        try:
            first_date = date.fromisoformat(first_day)
            last_date = date.fromisoformat(last_day)
        except ValueError:
            return False
        return last_date >= today and first_date <= horizon

    editorial_iso = record.get("actualizado_en") or record.get("publicado_en")
    editorial = _parse_temporal(editorial_iso)
    if not editorial:
        return False
    return editorial["date"] >= today - timedelta(days=undated_lookback_days)


def is_recent_news_record(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
    lookback_days: int = NEWS_LOOKBACK_DAYS,
) -> bool:
    now = now or datetime.now(MADRID_TZ)
    published_iso = record.get("publicado_en") or record.get("actualizado_en")
    published = _parse_temporal(published_iso)
    if not published:
        return False
    return published["dt"] >= now - timedelta(days=lookback_days)


def normalize_plan_records(
    records: list[dict[str, Any]],
    *,
    source: str,
    keep_only_current: bool = True,
    scraped_at: str | None = None,
) -> list[dict[str, Any]]:
    scraped_at = scraped_at or utc_now_iso()
    normalized: list[dict[str, Any]] = []
    today = date.today()

    for raw_record in records:
        item = dict(raw_record)
        source_id = _infer_plan_source_id(item)
        slug = _slugify(_clean_text(item.get("titulo")) or source_id)
        categories = _extract_category_values(item)
        tags = _extract_tag_values(item)
        published_at = _normalize_datetime_field(
            item.get("fecha_publicacion") or item.get("publicado_en")
        )
        updated_at = _normalize_datetime_field(
            item.get("fecha_actualizacion") or item.get("actualizado_en")
        )

        sessions_parsed = _collect_parsed_sessions(item)
        start = _parse_temporal(item.get("fecha_inicio"))
        end = _parse_temporal(item.get("fecha_fin"))

        if start is None and sessions_parsed:
            start = sessions_parsed[0]
        if end is None and sessions_parsed:
            end = sessions_parsed[-1]

        if start and end and end["dt"] < start["dt"]:
            end = start

        output_sessions_parsed = _select_output_sessions(sessions_parsed, today=today)
        next_relevant = _next_relevant_temporal(
            start=start,
            end=end,
            all_sessions=sessions_parsed,
            today=today,
        )
        sessions = [_session_payload(parsed) for parsed in output_sessions_parsed]
        item["fuente"] = source
        item["fuente_id"] = source_id
        item["id"] = _build_compound_id("plan", source, source_id)
        item["tipo"] = "plan"
        item["slug"] = slug
        item["titulo"] = _clean_text(item.get("titulo"))
        item["subtitulo"] = _clean_text(item.get("subtitulo")) or None
        item["resumen"] = _build_summary(item)
        item["descripcion"] = _clean_text(item.get("descripcion")) or item["resumen"]
        item["contenido"] = _clean_text(item.get("contenido")) or item["descripcion"]
        item["categorias"] = categories
        item["categoria_principal"] = categories[0] if categories else None
        item["etiquetas"] = tags
        item["autor"] = _clean_text(item.get("autor")) or None
        item["url"] = _clean_text(item.get("url")) or None
        item["url_articulo"] = _clean_text(item.get("url_articulo")) or None
        item["url_compra"] = _clean_text(item.get("url_compra")) or None
        item["imagen"] = _clean_text(item.get("imagen")) or None
        item["lugar"] = _clean_text(item.get("lugar")) or None
        item["direccion"] = _clean_text(item.get("direccion")) or None
        item["latitud"] = _as_float(item.get("latitud"))
        item["longitud"] = _as_float(item.get("longitud"))
        item["precio"] = _as_float(item.get("precio"))
        item["moneda"] = _clean_text(item.get("moneda")) or None
        item["es_gratis"] = item["precio"] == 0.0 if item["precio"] is not None else None
        item["modo_fecha"] = _plan_mode(start, end, sessions_parsed)
        item["estado_temporal"] = _plan_temporal_status(start, end)
        item["fecha_inicio"] = start["date"].isoformat() if start else None
        item["fecha_fin"] = end["date"].isoformat() if end else None
        item["datetime_inicio"] = start["datetime_iso"] if start and start["has_time"] else None
        item["datetime_fin"] = end["datetime_iso"] if end and end["has_time"] else None
        item["tiene_hora_inicio"] = bool(start and start["has_time"])
        item["tiene_hora_fin"] = bool(end and end["has_time"])
        item["fechas_disponibles"] = [
            session["datetime"] or session["fecha"] for session in sessions
        ]
        item["sesiones"] = sessions
        item["proxima_fecha"] = next_relevant["date"].isoformat() if next_relevant else None
        item["proximo_datetime"] = (
            next_relevant["datetime_iso"] if next_relevant else None
        )
        item["sort_datetime"] = (
            next_relevant["datetime_iso"] if next_relevant else (updated_at or published_at)
        )
        item["vigente_hasta"] = _effective_end_iso(end or start)
        item["publicado_en"] = published_at
        item["actualizado_en"] = updated_at
        item["scraped_en"] = scraped_at
        item["timezone"] = "Europe/Madrid"
        item["valido_para_web"] = True
        item["metadata"] = _collect_source_metadata(item, kind="plan")
        if len(output_sessions_parsed) != len(sessions_parsed):
            item["metadata"]["sesiones_total_fuente"] = len(sessions_parsed)
            item["metadata"]["sesiones_publicadas"] = len(output_sessions_parsed)

        if keep_only_current and not is_current_plan_record(item):
            continue

        normalized.append(item)

    return _plan_sort_records(normalized)


def normalize_news_records(
    records: list[dict[str, Any]],
    *,
    source: str,
    keep_only_recent: bool = True,
    scraped_at: str | None = None,
) -> list[dict[str, Any]]:
    scraped_at = scraped_at or utc_now_iso()
    normalized: list[dict[str, Any]] = []

    for raw_record in records:
        item = dict(raw_record)
        source_id = _infer_source_id(item)
        slug = _slugify(_clean_text(item.get("titulo")) or source_id)
        categories = _extract_category_values(item)
        tags = _extract_tag_values(item)
        published_at = _normalize_datetime_field(
            item.get("fecha_publicacion") or item.get("publicado_en")
        )
        updated_at = _normalize_datetime_field(
            item.get("fecha_actualizacion") or item.get("actualizado_en")
        )

        item["fuente"] = source
        item["fuente_id"] = source_id
        item["id"] = _build_compound_id("noticia", source, source_id)
        item["tipo"] = "noticia"
        item["slug"] = slug
        item["titulo"] = _clean_text(item.get("titulo"))
        item["subtitulo"] = _clean_text(item.get("subtitulo")) or None
        item["resumen"] = _build_summary(item)
        item["descripcion"] = _clean_text(item.get("descripcion")) or item["resumen"]
        item["contenido"] = _clean_text(item.get("contenido")) or item["descripcion"]
        item["categorias"] = categories
        item["categoria_principal"] = categories[0] if categories else None
        item["etiquetas"] = tags
        item["autor"] = _clean_text(item.get("autor")) or None
        item["url"] = _clean_text(item.get("url")) or None
        item["imagen"] = _clean_text(item.get("imagen")) or None
        item["publicado_en"] = published_at
        item["actualizado_en"] = updated_at
        item["modo_fecha"] = "publicacion"
        item["estado_temporal"] = "reciente" if published_at or updated_at else "sin_fecha"
        item["fecha_inicio"] = None
        item["fecha_fin"] = None
        item["datetime_inicio"] = None
        item["datetime_fin"] = None
        item["tiene_hora_inicio"] = False
        item["tiene_hora_fin"] = False
        item["fechas_disponibles"] = []
        item["sesiones"] = []
        item["sort_datetime"] = published_at or updated_at or scraped_at
        item["vigente_hasta"] = None
        item["scraped_en"] = scraped_at
        item["timezone"] = "Europe/Madrid"
        item["valido_para_web"] = True
        item["metadata"] = _collect_source_metadata(item, kind="noticia")

        if keep_only_recent and not is_recent_news_record(item):
            continue

        normalized.append(item)

    return sorted(
        normalized,
        key=lambda item: (
            item.get("sort_datetime") or "",
            _clean_text(item.get("titulo")).casefold(),
        ),
        reverse=True,
    )


def _candidate_merge_url(record: dict[str, Any]) -> str | None:
    source = _clean_text(record.get("fuente")).casefold()
    for field in ("url_compra", "url"):
        value = _clean_text(record.get(field))
        if not value:
            continue
        if source == "esmadrid":
            continue
        parsed = urlparse(value)
        host = parsed.netloc.lower()
        if field == "url" and (
            "madridsecreto.co" in host or "esmadrid.com" in host
        ):
            continue
        return value.rstrip("/").lower()
    return None


def plan_merge_key(record: dict[str, Any]) -> str:
    candidate_url = _candidate_merge_url(record)
    if candidate_url:
        return candidate_url

    title = _slugify(_clean_text(record.get("titulo")))
    when = record.get("fecha_inicio") or record.get("fecha_fin") or record.get("sort_datetime") or "sin-fecha"
    place = _slugify(_clean_text(record.get("lugar") or record.get("direccion") or "madrid"))
    return f"{title}::{when}::{place}"


def _related_ids(record: dict[str, Any]) -> list[str]:
    values = record.get("ids_relacionados")
    if isinstance(values, list) and values:
        return _dedupe_strings(values)
    source = _clean_text(record.get("fuente"))
    source_id = _clean_text(record.get("fuente_id"))
    if source and source_id:
        return [f"{source}:{source_id}"]
    return []


def _merge_metadata(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(current)
    for key, value in incoming.items():
        if value in (None, "", []):
            continue
        if key not in merged or merged[key] in (None, "", []):
            merged[key] = value
            continue
        if isinstance(value, list) and isinstance(merged[key], list):
            merged[key] = _dedupe_strings(list(merged[key]) + list(value))
    return merged


def _plan_completeness_score(record: dict[str, Any]) -> tuple[int, int, int]:
    filled = sum(
        1
        for field in (
            "precio",
            "imagen",
            "lugar",
            "direccion",
            "publicado_en",
            "actualizado_en",
            "datetime_inicio",
            "fecha_inicio",
            "url_compra",
        )
        if record.get(field) not in (None, "", [])
    )
    content_length = len(_clean_text(record.get("contenido")))
    summary_length = len(_clean_text(record.get("descripcion")))
    return (filled, content_length, summary_length)


def _prefer_primary(current: dict[str, Any], incoming: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    current_priority = SOURCE_PRIORITY.get(_clean_text(current.get("fuente")), 99)
    incoming_priority = SOURCE_PRIORITY.get(_clean_text(incoming.get("fuente")), 99)
    if incoming_priority < current_priority:
        return dict(incoming), current
    if incoming_priority > current_priority:
        return dict(current), incoming

    if _plan_completeness_score(incoming) > _plan_completeness_score(current):
        return dict(incoming), current
    return dict(current), incoming


def merge_plan_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_key: dict[str, dict[str, Any]] = {}

    for record in records:
        key = plan_merge_key(record)
        current = merged_by_key.get(key)
        if current is None:
            base = dict(record)
            base["fuentes_relacionadas"] = _dedupe_strings([record.get("fuente")])
            base["ids_relacionados"] = _related_ids(record)
            merged_by_key[key] = base
            continue

        primary, secondary = _prefer_primary(current, record)
        merged = dict(primary)

        for list_field in ("categorias", "etiquetas", "fechas_disponibles", "fuentes_relacionadas"):
            merged[list_field] = _dedupe_strings(
                list(primary.get(list_field) or []) + list(secondary.get(list_field) or [])
            )

        primary_sessions = primary.get("sesiones") or []
        secondary_sessions = secondary.get("sesiones") or []
        session_map: dict[str, dict[str, Any]] = {}
        for session in primary_sessions + secondary_sessions:
            key_session = session.get("datetime") or session.get("fecha")
            if not key_session:
                continue
            session_map[key_session] = session
        merged["sesiones"] = [session_map[key] for key in sorted(session_map)]

        merged["ids_relacionados"] = _dedupe_strings(
            _related_ids(primary) + _related_ids(secondary)
        )
        merged["fuentes_relacionadas"] = _dedupe_strings(
            list(merged.get("fuentes_relacionadas") or []) + [secondary.get("fuente")]
        )
        merged["metadata"] = _merge_metadata(
            primary.get("metadata") or {}, secondary.get("metadata") or {}
        )

        for field in (
            "subtitulo",
            "resumen",
            "descripcion",
            "contenido",
            "url_articulo",
            "url_compra",
            "url",
            "imagen",
            "lugar",
            "direccion",
            "latitud",
            "longitud",
            "precio",
            "moneda",
            "es_gratis",
            "publicado_en",
            "actualizado_en",
            "fecha_inicio",
            "fecha_fin",
            "datetime_inicio",
            "datetime_fin",
            "tiene_hora_inicio",
            "tiene_hora_fin",
            "modo_fecha",
            "estado_temporal",
            "categoria_principal",
            "proxima_fecha",
            "proximo_datetime",
            "sort_datetime",
            "vigente_hasta",
        ):
            current_value = merged.get(field)
            incoming_value = secondary.get(field)
            if current_value in (None, "", [], False) and incoming_value not in (None, "", []):
                merged[field] = incoming_value

        if len(_clean_text(secondary.get("contenido"))) > len(_clean_text(merged.get("contenido"))):
            merged["contenido"] = secondary.get("contenido")
        if len(_clean_text(secondary.get("descripcion"))) > len(_clean_text(merged.get("descripcion"))):
            merged["descripcion"] = secondary.get("descripcion")
        if len(_clean_text(secondary.get("resumen"))) > len(_clean_text(merged.get("resumen"))):
            merged["resumen"] = secondary.get("resumen")

        merged["es_gratis"] = merged.get("precio") == 0.0 if merged.get("precio") is not None else merged.get("es_gratis")
        merged_by_key[key] = merged

    merged_records = list(merged_by_key.values())
    for record in merged_records:
        related_sources = _dedupe_strings(record.get("fuentes_relacionadas") or [])
        record["fuentes_relacionadas"] = related_sources
        if len(related_sources) > 1:
            source_id = _slugify(plan_merge_key(record))
            record["id"] = f"plan:merged:{source_id}"
            record["fuente"] = related_sources[0]
    return _plan_sort_records(merged_records)


def merge_news_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_key: dict[str, dict[str, Any]] = {}
    for record in records:
        key = _clean_text(record.get("url")) or _clean_text(record.get("id"))
        current = merged_by_key.get(key)
        if current is None:
            base = dict(record)
            base["fuentes_relacionadas"] = _dedupe_strings([record.get("fuente")])
            base["ids_relacionados"] = _related_ids(record)
            merged_by_key[key] = base
            continue

        merged = dict(current)
        merged["categorias"] = _dedupe_strings(
            list(current.get("categorias") or []) + list(record.get("categorias") or [])
        )
        merged["etiquetas"] = _dedupe_strings(
            list(current.get("etiquetas") or []) + list(record.get("etiquetas") or [])
        )
        merged["fuentes_relacionadas"] = _dedupe_strings(
            list(current.get("fuentes_relacionadas") or []) + [record.get("fuente")]
        )
        merged["ids_relacionados"] = _dedupe_strings(_related_ids(current) + _related_ids(record))
        merged["metadata"] = _merge_metadata(
            current.get("metadata") or {}, record.get("metadata") or {}
        )

        for text_field in ("subtitulo", "resumen", "descripcion", "contenido"):
            if len(_clean_text(record.get(text_field))) > len(_clean_text(merged.get(text_field))):
                merged[text_field] = record.get(text_field)

        for field in (
            "autor",
            "imagen",
            "publicado_en",
            "actualizado_en",
            "categoria_principal",
            "sort_datetime",
        ):
            if merged.get(field) in (None, "", []) and record.get(field) not in (None, "", []):
                merged[field] = record.get(field)

        merged_by_key[key] = merged

    merged_records = [
        record for record in merged_by_key.values() if is_recent_news_record(record)
    ]

    return sorted(
        merged_records,
        key=lambda item: (
            item.get("sort_datetime") or "",
            _clean_text(item.get("titulo")).casefold(),
        ),
        reverse=True,
    )


def validate_plan_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    mode_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    with_price = 0
    with_location = 0

    for record in records:
        source = _clean_text(record.get("fuente")) or "desconocida"
        source_counts[source] = source_counts.get(source, 0) + 1
        mode = _clean_text(record.get("modo_fecha")) or "sin_fecha"
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

        if record.get("precio") is not None:
            with_price += 1
        if record.get("lugar") or record.get("direccion"):
            with_location += 1

        if record.get("tipo") != "plan":
            issues.append(f"Tipo invalido en {record.get('id')}")
        if not record.get("titulo"):
            issues.append(f"Titulo vacio en {record.get('id')}")
        if not record.get("fuente_id"):
            issues.append(f"Falta fuente_id en {record.get('id')}")
        if mode != "sin_fecha" and not (record.get("fecha_inicio") or record.get("fecha_fin")):
            issues.append(f"Faltan fechas en {record.get('id')}")
        if record.get("fecha_inicio") and record.get("fecha_fin"):
            if record["fecha_inicio"] > record["fecha_fin"]:
                issues.append(f"Rango de fechas invalido en {record.get('id')}")
        if not is_current_plan_record(record):
            issues.append(f"Plan fuera de ventana producto en {record.get('id')}")

    return {
        "valid": not issues,
        "total": len(records),
        "with_price": with_price,
        "with_location": with_location,
        "by_source": source_counts,
        "by_mode": mode_counts,
        "errors": issues[:50],
    }


def validate_news_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    source_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}

    for record in records:
        source = _clean_text(record.get("fuente")) or "desconocida"
        source_counts[source] = source_counts.get(source, 0) + 1

        category = _clean_text(record.get("categoria_principal")) or "Sin categoria"
        category_counts[category] = category_counts.get(category, 0) + 1

        if record.get("tipo") != "noticia":
            issues.append(f"Tipo invalido en {record.get('id')}")
        if not record.get("titulo"):
            issues.append(f"Titulo vacio en {record.get('id')}")
        if not record.get("publicado_en"):
            issues.append(f"Falta publicado_en en {record.get('id')}")
        if not is_recent_news_record(record):
            issues.append(f"Noticia fuera de ventana producto en {record.get('id')}")

    return {
        "valid": not issues,
        "total": len(records),
        "by_source": source_counts,
        "by_category": category_counts,
        "errors": issues[:50],
    }