"""Círculo de Bellas Artes agenda scraper.

Uses the public agenda listing for discovery and individual detail pages for
dates, description, venue, price, and purchase links.

Output: outputs/eventos_circulo_bellas_artes.json
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.circulobellasartes.com"
AGENDA_URL = f"{BASE_URL}/agenda/"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "outputs"
    / "eventos_circulo_bellas_artes.json"
)
SOURCE_NAME = "circulo_bellas_artes"
REQUEST_TIMEOUT = 30
CBA_ADDRESS = "Calle de Alcalá, 42, Madrid"
CINE_ESTUDIO_ADDRESS = "Calle del Marqués de Casa Riera, 4, Madrid"
ALLOWED_PREFIXES = (
    "/eventos/",
    "/exposiciones/",
    "/espectaculos/",
    "/ciclos-cine/",
    "/talleres/",
    "/humanidades/",
)
SECTION_STOP_HEADINGS = {
    "programa",
    "sesiones",
    "ficha técnica",
    "ficha tecnica",
    "festivales y premios",
    "abonos",
    "precios",
    "taquilla",
    "información y matrículas",
    "informacion y matriculas",
    "colabora",
    "dirigido por",
    "orientado a",
    "público joven",
    "publico joven",
    "suscríbete a nuestro boletín",
    "suscribete a nuestro boletin",
}
FOOTER_MARKERS = {
    "suscríbete a nuestro boletín",
    "suscribete a nuestro boletin",
    "consultar horarios",
    "alquiler de espacios",
    "sala de prensa",
    "síguenos",
    "siguenos",
}
DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
SESSION_RE = re.compile(
    r"(?:Lun|Mar|Mié|Mie|Jue|Vie|Sáb|Sab|Dom)\s+(\d{2}/\d{2}),\s*(\d{1,2}:\d{2})",
    flags=re.IGNORECASE,
)
WORKSHOP_SESSION_RE = re.compile(
    r"Sesión\s+\d+\s*[\-–]\s*(\d{1,2})\s+de\s+([a-záéíóú]+)",
    flags=re.IGNORECASE,
)
GENERAL_PRICE_PATTERNS = (
    re.compile(r"entrada\s+general\s*:\s*(\d+(?:[.,]\d+)?)\s*€", flags=re.IGNORECASE),
    re.compile(r"entrada\s+general\s*(\d+(?:[.,]\d+)?)\s*€", flags=re.IGNORECASE),
    re.compile(r"general\s*:\s*(\d+(?:[.,]\d+)?)\s*€", flags=re.IGNORECASE),
    re.compile(r"\bgeneral\s*(\d+(?:[.,]\d+)?)\s*€", flags=re.IGNORECASE),
    re.compile(r"localidades\s+sueltas\s*:\s*desde\s*(\d+(?:[.,]\d+)?)\s*€", flags=re.IGNORECASE),
    re.compile(r"matrícula\s*.*?precio\s*:\s*(\d+(?:[.,]\d+)?)\s*€", flags=re.IGNORECASE),
    re.compile(r"precio\s*:\s*general\s*(\d+(?:[.,]\d+)?)\s*€", flags=re.IGNORECASE),
)
MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}
GENERIC_PURCHASE_TOKENS = {
    "circulo",
    "camara",
    "conciertos",
    "temporada",
    "eventos",
    "evento",
    "espectaculos",
    "espectaculo",
    "cine",
    "estudio",
    "taller",
    "talleres",
    "actividad",
    "actividades",
    "exposicion",
    "exposiciones",
    "madrid",
    "info",
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(unescape(str(value)).replace("\xa0", " ").split())


def _normalize_url(url: str) -> str:
    absolute = urljoin(BASE_URL, url)
    parsed = urlparse(absolute)
    path = parsed.path.rstrip("/")
    if path:
        path = f"{path}/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _request_html(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _is_detail_path(path: str) -> bool:
    normalized = path.rstrip("/")
    if normalized in {prefix.rstrip("/") for prefix in ALLOWED_PREFIXES}:
        return False
    return any(normalized.startswith(prefix.rstrip("/")) for prefix in ALLOWED_PREFIXES)


def _category_from_url(url: str) -> list[str]:
    path = urlparse(url).path
    if path.startswith("/ciclos-cine/peliculas/"):
        return ["Películas", "Cine"]
    mapping = {
        "/eventos/": ["Eventos"],
        "/exposiciones/": ["Exposiciones"],
        "/espectaculos/": ["Escénicas"],
        "/ciclos-cine/": ["Cine"],
        "/talleres/": ["Cursos y talleres"],
        "/humanidades/": ["Actividades"],
    }
    for prefix, categories in mapping.items():
        if path.startswith(prefix):
            return categories
    return ["Cultura"]


def _find_card_container(anchor: Tag) -> Tag | None:
    title = _clean_text(anchor.get_text(" ", strip=True))
    current: Tag | None = anchor
    for _ in range(7):
        if not isinstance(current, Tag):
            break
        text = _clean_text(current.get_text(" ", strip=True))
        if title and title in text and DATE_RE.search(text) and len(text) <= 500:
            return current
        current = current.parent if isinstance(current.parent, Tag) else None
    return None


def _parse_dmy(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _extract_dates_from_text(text: str) -> tuple[str | None, str | None]:
    matches: list[str] = []
    for match in DATE_RE.findall(text):
        if match not in matches:
            matches.append(match)

    if not matches:
        return None, None
    if len(matches) == 1:
        parsed = _parse_dmy(matches[0])
        return parsed, parsed
    return _parse_dmy(matches[0]), _parse_dmy(matches[1])


def _extract_listing_items(session: requests.Session) -> list[dict[str, Any]]:
    soup = _request_html(session, AGENDA_URL)
    discovered: dict[str, dict[str, Any]] = {}

    for anchor in soup.select("a[href]"):
        href = _normalize_url(anchor.get("href", ""))
        parsed = urlparse(href)
        if parsed.netloc != urlparse(BASE_URL).netloc:
            continue
        if not _is_detail_path(parsed.path):
            continue

        title = _clean_text(anchor.get_text(" ", strip=True))
        if not title or len(title) < 3:
            continue

        container = _find_card_container(anchor)
        container_text = _clean_text(container.get_text(" ", strip=True)) if container else title
        fecha_inicio, fecha_fin = _extract_dates_from_text(container_text)

        candidate = {
            "url": href,
            "titulo": title,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "categorias": _category_from_url(href),
            "listing_text": container_text,
        }
        existing = discovered.get(href)
        if existing is None:
            discovered[href] = candidate
            continue
        if not existing.get("fecha_inicio") and fecha_inicio:
            discovered[href] = candidate
            continue
        if len(title) > len(existing.get("titulo") or ""):
            discovered[href] = candidate

    return list(discovered.values())


def _extract_lines(soup: BeautifulSoup) -> list[str]:
    body = soup.body or soup
    lines: list[str] = []
    for raw_line in body.get_text("\n").splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        if lines and line == lines[-1]:
            continue
        lines.append(line)
    return lines


def _extract_title(soup: BeautifulSoup, listing_title: str) -> str:
    titles = [_clean_text(node.get_text(" ", strip=True)) for node in soup.find_all("h1")]
    for candidate in titles:
        if not candidate:
            continue
        if candidate.casefold() == listing_title.casefold():
            return candidate
        if candidate.casefold() in listing_title.casefold() or listing_title.casefold() in candidate.casefold():
            return candidate

    for candidate in titles:
        if candidate.casefold() not in {
            "círculo de bellas artes de madrid",
            "circulo de bellas artes de madrid",
            "casa europa",
        }:
            return candidate

    return listing_title or (titles[-1] if titles else "")


def _trim_core_lines(lines: list[str], title: str) -> list[str]:
    title_index = 0
    for index, line in enumerate(lines):
        if _clean_text(line) == _clean_text(title):
            title_index = index
            break
    core = lines[title_index + 1 :]
    for index, line in enumerate(core):
        normalized = line.casefold()
        if normalized in FOOTER_MARKERS:
            return core[:index]
        if normalized.startswith("círculo de bellas artesalcalá"):
            return core[:index]
    return core


def _find_section(lines: list[str], heading: str) -> list[str]:
    heading_normalized = heading.casefold()
    for index, line in enumerate(lines):
        if line.casefold() != heading_normalized:
            continue
        collected: list[str] = []
        for candidate in lines[index + 1 :]:
            normalized = candidate.casefold()
            if normalized in SECTION_STOP_HEADINGS:
                break
            if normalized.startswith("círculo de bellas artesalcalá"):
                break
            collected.append(candidate)
        return collected
    return []


def _extract_description(title: str, core_lines: list[str]) -> str:
    movie_section = _find_section(core_lines, "Acerca de la película")
    if movie_section:
        return _clean_text(" ".join(movie_section))

    description_lines: list[str] = []
    for line in core_lines:
        normalized = line.casefold()
        if normalized in SECTION_STOP_HEADINGS:
            break
        description_lines.append(line)

    description = _clean_text(" ".join(description_lines))
    if description:
        return description
    return title


def _extract_content(core_lines: list[str]) -> str:
    return _clean_text(" ".join(core_lines))


def _extract_image(soup: BeautifulSoup) -> str | None:
    for selector in (
        'meta[property="og:image"]',
        'meta[name="twitter:image"]',
    ):
        node = soup.select_one(selector)
        if not node:
            continue
        content = _clean_text(node.get("content"))
        if content:
            return content
    return None


def _purchase_url_is_specific(absolute: str, page_url: str) -> bool:
    parsed_purchase = urlparse(absolute)
    if parsed_purchase.netloc == "tickets.circulobellasartes.com" and parsed_purchase.path.rstrip("/") in {"", "/"}:
        return False

    page_slug = urlparse(page_url).path.rstrip("/").split("/")[-1]
    purchase_path = parsed_purchase.path.casefold()
    slug_tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", page_slug.casefold())
        if len(token) >= 4 and not token.isdigit() and token not in GENERIC_PURCHASE_TOKENS
    ]
    if not slug_tokens:
        return False
    return any(token in purchase_path for token in slug_tokens)


def _extract_purchase_url(soup: BeautifulSoup, page_url: str) -> str | None:
    preferred_hosts = ("tickets.circulobellasartes.com", "reservaentradas.com")
    for anchor in soup.select("a[href]"):
        href = _clean_text(anchor.get("href"))
        if not href:
            continue
        absolute = urljoin(page_url, href)
        if absolute.lower().endswith(".pdf"):
            continue
        link_text = _clean_text(anchor.get_text(" ", strip=True)).casefold()
        if any(host in absolute for host in preferred_hosts):
            if _purchase_url_is_specific(absolute, page_url):
                return absolute
        if any(token in link_text for token in ("entrada", "entradas", "comprar", "matrícula", "matricula")):
            if _purchase_url_is_specific(absolute, page_url):
                return absolute
    return None


def _extract_space_name(soup: BeautifulSoup, flat_text: str) -> str | None:
    for anchor in soup.select('a[href*="/espacio/"]'):
        text = _clean_text(anchor.get_text(" ", strip=True))
        if text:
            return text
    match = re.search(r"Sala:\s*(.+?)(?:Precio:|Fecha:|Horario:|Colabora:|Dirigido por:|Orientado a|Suscríbete|$)", flat_text, flags=re.IGNORECASE)
    if match:
        return _clean_text(match.group(1))
    if "cine estudio" in flat_text.casefold():
        return "Cine Estudio"
    return "Círculo de Bellas Artes"


def _extract_address_and_coords(soup: BeautifulSoup, flat_text: str) -> tuple[str | None, float | None, float | None]:
    for anchor in soup.select("a[href]"):
        href = _clean_text(anchor.get("href"))
        if "google." not in href or "/maps/place/" not in href:
            continue
        latlon_match = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", href)
        lat = float(latlon_match.group(1)) if latlon_match else None
        lon = float(latlon_match.group(2)) if latlon_match else None
        visible = _clean_text(anchor.get_text(" ", strip=True))
        decoded = unquote(urlparse(href).path)
        if "Marqués" in visible or "Marqu" in decoded:
            return CINE_ESTUDIO_ADDRESS, lat, lon

    if "marqués de casa riera" in flat_text.casefold() or "marques de casa riera" in flat_text.casefold():
        return CINE_ESTUDIO_ADDRESS, None, None
    return CBA_ADDRESS, None, None


def _extract_price_candidate_text(core_lines: list[str], flat_text: str) -> str:
    direct_line_match = re.search(
        r"Precio:\s*(.+?)(?:Fecha:|Horario:|Sala:|Colabora:|Dirigido por:|Orientado a|Suscríbete|$)",
        flat_text,
        flags=re.IGNORECASE,
    )
    if direct_line_match:
        return _clean_text(direct_line_match.group(1))

    price_section = _find_section(core_lines, "Precios")
    if price_section:
        return _clean_text(" ".join(price_section))
    return flat_text


def _parse_price(candidate_text: str, flat_text: str) -> tuple[float | None, str | None]:
    if "estreno" in flat_text.casefold():
        match = re.search(r"estrenos\s+general\s*:?\s*(\d+(?:[.,]\d+)?)\s*€", candidate_text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ".")), "EUR"

    for pattern in GENERAL_PRICE_PATTERNS:
        match = pattern.search(candidate_text)
        if match:
            return float(match.group(1).replace(",", ".")), "EUR"

    match = re.search(r"desde\s*(\d+(?:[.,]\d+)?)\s*€", candidate_text, flags=re.IGNORECASE)
    if match:
        return float(match.group(1).replace(",", ".")), "EUR"

    values: list[float] = []
    for raw_value in re.findall(r"\d+(?:[.,]\d+)?(?=\s*€)", candidate_text):
        try:
            values.append(float(raw_value.replace(",", ".")))
        except ValueError:
            continue
    if values:
        return min(values), "EUR"
    return None, None


def _extract_sessions(core_lines: list[str], start_iso: str | None) -> list[str]:
    sessions_section = _find_section(core_lines, "Sesiones")
    if sessions_section:
        year = datetime.fromisoformat(start_iso).year if start_iso else datetime.now().year
        sessions_text = _clean_text(" ".join(sessions_section))
        sessions: list[str] = []
        for day_month, hour_text in SESSION_RE.findall(sessions_text):
            try:
                parsed = datetime.strptime(f"{day_month}/{year} {hour_text}", "%d/%m/%Y %H:%M")
            except ValueError:
                continue
            sessions.append(parsed.strftime("%Y-%m-%d %H:%M:%S"))
        if sessions:
            return sessions

    program_section = _find_section(core_lines, "Programa")
    if program_section:
        year = datetime.fromisoformat(start_iso).year if start_iso else datetime.now().year
        program_text = _clean_text(" ".join(program_section))
        sessions: list[str] = []
        for day_text, month_name in WORKSHOP_SESSION_RE.findall(program_text):
            month = MONTHS.get(month_name.casefold())
            if not month:
                continue
            try:
                parsed = datetime(year=year, month=month, day=int(day_text))
            except ValueError:
                continue
            sessions.append(parsed.date().isoformat())
        if sessions:
            ordered: list[str] = []
            for value in sessions:
                if value not in ordered:
                    ordered.append(value)
            return ordered
    return []


def _extract_detail_fields(session: requests.Session, url: str, listing: dict[str, Any]) -> dict[str, Any]:
    soup = _request_html(session, url)
    title = _extract_title(soup, listing["titulo"])
    lines = _extract_lines(soup)
    core_lines = _trim_core_lines(lines, title)
    flat_text = _clean_text(" ".join(core_lines))
    description = _extract_description(title, core_lines)
    content = _extract_content(core_lines)
    lugar = _extract_space_name(soup, flat_text)
    direccion, latitud, longitud = _extract_address_and_coords(soup, flat_text)
    price_text = _extract_price_candidate_text(core_lines, flat_text)
    precio, moneda = _parse_price(price_text, flat_text)
    sesiones = _extract_sessions(core_lines, listing.get("fecha_inicio"))

    if not listing.get("fecha_inicio") or not listing.get("fecha_fin"):
        start_fallback, end_fallback = _extract_dates_from_text(flat_text)
        listing["fecha_inicio"] = listing.get("fecha_inicio") or start_fallback
        listing["fecha_fin"] = listing.get("fecha_fin") or end_fallback

    return {
        "titulo": title,
        "descripcion": description,
        "contenido": content or description,
        "precio": precio,
        "moneda": moneda,
        "lugar": lugar,
        "direccion": direccion,
        "latitud": latitud,
        "longitud": longitud,
        "fechas_disponibles": sesiones,
        "url_compra": _extract_purchase_url(soup, url),
        "imagen": _extract_image(soup),
        "metadata": {
            "listing_text": listing.get("listing_text"),
            "price_text": price_text or None,
        },
    }


def scrape_circulo_bellas_artes() -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    log.info("Fetching Círculo de Bellas Artes agenda …")
    listings = _extract_listing_items(session)
    log.info("Discovered %d agenda detail URLs", len(listings))

    records: list[dict[str, Any]] = []
    for index, listing in enumerate(listings, start=1):
        log.info("Fetching CBA detail %d/%d: %s", index, len(listings), listing["url"])
        detail = _extract_detail_fields(session, listing["url"], listing)
        records.append(
            {
                "id": urlparse(listing["url"]).path.rstrip("/").split("/")[-1],
                "titulo": detail["titulo"],
                "subtitulo": None,
                "descripcion": detail["descripcion"],
                "contenido": detail["contenido"],
                "precio": detail["precio"],
                "moneda": detail["moneda"],
                "lugar": detail["lugar"],
                "direccion": detail["direccion"],
                "latitud": detail["latitud"],
                "longitud": detail["longitud"],
                "fecha_inicio": listing.get("fecha_inicio"),
                "fecha_fin": listing.get("fecha_fin"),
                "fechas_disponibles": detail["fechas_disponibles"],
                "categorias": listing.get("categorias") or ["Cultura"],
                "url": listing["url"],
                "url_articulo": listing["url"],
                "url_compra": detail["url_compra"],
                "imagen": detail["imagen"],
                "fecha_publicacion": None,
                "fecha_actualizacion": None,
                "fuente": SOURCE_NAME,
                "metadata": detail["metadata"],
            }
        )

    records = normalize_plan_records(records, source=SOURCE_NAME)

    OUTPUT_FILE.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Saved %d Círculo de Bellas Artes events to %s", len(records), OUTPUT_FILE)
    return records


if __name__ == "__main__":
    results = scrape_circulo_bellas_artes()
    with_price = sum(1 for event in results if event.get("precio") is not None)
    with_coords = sum(1 for event in results if event.get("latitud") is not None)
    log.info(
        "Summary: %d events, %d with coords, %d with price",
        len(results),
        with_coords,
        with_price,
    )