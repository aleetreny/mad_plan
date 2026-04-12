"""
Madrid Secreto plans scraper.

Strategy:
  1. Fetch the full `que-hacer` category archive through the WordPress REST API.
  2. Build a generic plan record for every post.
  3. Extract extra plans from module sections and embedded `data-fever-plan-*` blocks.
    4. Keep only plans that are active now, upcoming soon, or recently published if undated.
    5. Merge overlapping records to keep the richest data per plan/article.

Output: outputs/eventos_madrid_secreto.json
"""

import json
import logging
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

try:
    from .normalization import normalize_plan_records
except ImportError:
    from normalization import normalize_plan_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://madridsecreto.co"
POSTS_API_URL = f"{BASE_URL}/wp-json/wp/v2/posts"
CATEGORIES_API_URL = f"{BASE_URL}/wp-json/wp/v2/categories"
REQUEST_DELAY = 0.15
POSTS_PER_PAGE = 50
ACTIVE_PLAN_MAX_FUTURE_DAYS = 365
UNDATED_PLAN_LOOKBACK_DAYS = 45
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "eventos_madrid_secreto.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}

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

MONTH_PATTERN = "|".join(MONTHS)
RANGE_DATE_RE = re.compile(
    rf"(?P<d1>\d{{1,2}})\s+de\s+(?P<m1>{MONTH_PATTERN})\s+de\s+(?P<y1>\d{{4}})"
    rf"\s*[–-]\s*"
    rf"(?P<d2>\d{{1,2}})\s+de\s+(?P<m2>{MONTH_PATTERN})\s+de\s+(?P<y2>\d{{4}})",
    re.IGNORECASE,
)
MULTI_DAY_RE = re.compile(
    rf"(?P<days>\d{{1,2}}(?:\s*,\s*\d{{1,2}})*(?:\s+y\s+\d{{1,2}})?)"
    rf"\s+de\s+(?P<month>{MONTH_PATTERN})\s+de\s+(?P<year>\d{{4}})",
    re.IGNORECASE,
)
SINGLE_DATE_RE = re.compile(
    rf"(?P<day>\d{{1,2}})\s+de\s+(?P<month>{MONTH_PATTERN})\s+de\s+(?P<year>\d{{4}})",
    re.IGNORECASE,
)
MODULE_SECTION_RE = re.compile(
    r'(?P<section><h2[^>]*class="[^"]*module-title[^"]*".*?</h2>.*?)(?=<h2[^>]*class="[^"]*module-title[^"]*"|$)',
    re.IGNORECASE | re.DOTALL,
)
ROUNDUP_SLUG_RE = re.compile(
    rf"^planes-(?:{MONTH_PATTERN})(?:-\d{{4}})?$", re.IGNORECASE
)
LOCATION_INLINE_RE = re.compile(r"([A-ZÁÉÍÓÚÜÑ][^.!?\n]{1,80}\|[^.!?\n]{3,140})")

IGNORED_PARAGRAPH_SNIPPETS = {
    "mantente al tanto",
    "nuestros mejores secretos",
    "escribe lo que estas buscando",
    "buscar",
    "facebook",
    "instagram",
    "tiktok",
    "youtube",
    "telegram",
    "whatsapp",
    "configuracion de la privacidad",
    "promueve tu evento",
}

LIST_FIELDS = {"categorias", "etiquetas", "fechas_disponibles"}
LONG_TEXT_FIELDS = {"descripcion", "contenido"}


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(unescape(value).replace("\xa0", " ").split())


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    if "T" in value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "madrid-secreto"


def _get_response(url: str, params: dict | None = None) -> requests.Response:
    last_error: requests.RequestException | None = None
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            last_error = error
            time.sleep(1.0 + attempt)

    assert last_error is not None
    raise last_error


def _fetch_json(url: str, params: dict | None = None) -> dict | list:
    return _get_response(url, params=params).json()


def _get_que_hacer_category_id() -> int | None:
    try:
        categories = _fetch_json(CATEGORIES_API_URL, {"search": "que hacer", "per_page": 20})
    except requests.RequestException as error:
        log.error("Failed to fetch categories: %s", error)
        return None

    if not isinstance(categories, list):
        return None

    for category in categories:
        if category.get("slug") == "que-hacer":
            return category.get("id")
    return None


def _fetch_all_posts(category_id: int) -> list[dict]:
    params = {
        "categories": category_id,
        "per_page": POSTS_PER_PAGE,
        "page": 1,
        "_embed": 1,
    }

    first_response = _get_response(POSTS_API_URL, params=params)
    posts = first_response.json()
    total_pages = int(first_response.headers.get("X-WP-TotalPages", "1"))
    total_posts = int(first_response.headers.get("X-WP-Total", str(len(posts))))
    log.info("Madrid Secreto `que-hacer`: %d posts across %d pages", total_posts, total_pages)

    failed_pages: list[int] = []

    for page in range(2, total_pages + 1):
        params["page"] = page
        try:
            response = _get_response(POSTS_API_URL, params=params)
        except requests.RequestException as error:
            log.warning("Failed to fetch Madrid Secreto page %d: %s", page, error)
            failed_pages.append(page)
            continue

        batch = response.json()
        if not isinstance(batch, list) or not batch:
            continue
        posts.extend(batch)

        if page % 5 == 0 or page == total_pages:
            log.info("Fetched %d/%d pages from Madrid Secreto", page, total_pages)
        time.sleep(REQUEST_DELAY)

    for page in failed_pages:
        params["page"] = page
        try:
            response = _get_response(POSTS_API_URL, params=params)
        except requests.RequestException as error:
            log.warning("Retry failed for Madrid Secreto page %d: %s", page, error)
            continue

        batch = response.json()
        if isinstance(batch, list) and batch:
            posts.extend(batch)
            log.info("Recovered Madrid Secreto page %d on retry", page)
        time.sleep(REQUEST_DELAY)

    return posts


def _extract_terms(post: dict, taxonomy: str) -> list[str]:
    values: list[str] = []
    for group in post.get("_embedded", {}).get("wp:term", []):
        for term in group:
            if term.get("taxonomy") != taxonomy:
                continue
            if taxonomy == "category" and term.get("slug") == "que-hacer":
                continue
            name = _clean_text(term.get("name"))
            if name:
                values.append(name)
    return sorted(dict.fromkeys(values))


def _extract_post_categories(post: dict) -> list[str]:
    categories = _extract_terms(post, "category")
    return categories or ["Que hacer"]


def _extract_post_tags(post: dict) -> list[str]:
    return _extract_terms(post, "post_tag")


def _extract_post_author(post: dict) -> str | None:
    authors = post.get("_embedded", {}).get("author", [])
    if authors:
        return _clean_text(authors[0].get("name"))
    return None


def _extract_featured_image(post: dict) -> str | None:
    media_items = post.get("_embedded", {}).get("wp:featuredmedia", [])
    for media in media_items:
        source_url = media.get("source_url")
        if source_url:
            return source_url
    return None


def _extract_first_image(container: BeautifulSoup | Tag) -> str | None:
    for image in container.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            value = image.get(attr)
            if value and not value.startswith("data:image"):
                return value
    return None


def _extract_paragraphs(container: BeautifulSoup | Tag) -> list[str]:
    paragraphs: list[str] = []
    for paragraph in container.find_all("p"):
        text = _clean_text(paragraph.get_text(" ", strip=True))
        if len(text) < 50:
            continue
        lowered = text.lower()
        if any(snippet in lowered for snippet in IGNORED_PARAGRAPH_SNIPPETS):
            continue
        if text not in paragraphs:
            paragraphs.append(text)
    return paragraphs


def _extract_post_content(container: BeautifulSoup | Tag, max_length: int | None = None) -> str:
    text = " ".join(_extract_paragraphs(container))
    if max_length is not None:
        return text[:max_length]
    return text


def _extract_excerpt(post: dict) -> str:
    html = post.get("excerpt", {}).get("rendered") or ""
    if not html:
        return ""
    return _clean_text(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))


def _parse_price(raw: str | None) -> tuple[float | None, str | None]:
    text = _clean_text(raw).lower()
    if not text:
        return None, None
    if "entrada libre" in text or "gratis" in text or "desde 0" in text:
        return 0.0, "EUR"

    values: list[float] = []
    for match in re.findall(r"\d+(?:[.,]\d+)?", text):
        try:
            values.append(float(match.replace(",", ".")))
        except ValueError:
            continue

    if values:
        return min(values), "EUR"
    return None, "EUR" if "€" in text else None


def _parse_iso_date(day: str, month: str, year: str) -> str:
    parsed = date(int(year), MONTHS[month.lower()], int(day))
    return parsed.isoformat()


def _parse_spanish_dates(raw: str | None) -> tuple[str | None, str | None, list[str]]:
    text = _clean_text(raw)
    if not text:
        return None, None, []

    range_match = RANGE_DATE_RE.search(text)
    if range_match:
        start = _parse_iso_date(
            range_match.group("d1"), range_match.group("m1"), range_match.group("y1")
        )
        end = _parse_iso_date(
            range_match.group("d2"), range_match.group("m2"), range_match.group("y2")
        )
        return start, end, [start, end]

    multi_match = MULTI_DAY_RE.search(text)
    if multi_match:
        month = multi_match.group("month")
        year = multi_match.group("year")
        days = re.findall(r"\d{1,2}", multi_match.group("days"))
        datetimes = [_parse_iso_date(day, month, year) for day in days]
        return datetimes[0], datetimes[-1], datetimes

    singles = [
        _parse_iso_date(match.group("day"), match.group("month"), match.group("year"))
        for match in SINGLE_DATE_RE.finditer(text)
    ]
    unique = list(dict.fromkeys(singles))
    if unique:
        return unique[0], unique[-1], unique

    return None, None, []


def _extract_price_text(container: BeautifulSoup | Tag) -> str:
    for node in container.find_all(class_=re.compile("price", re.IGNORECASE)):
        text = _clean_text(node.get_text(" ", strip=True))
        if text and ("€" in text or "entrada libre" in text.lower() or "gratis" in text.lower()):
            return text

    text = _clean_text(container.get_text(" ", strip=True))
    match = re.search(
        r"(Desde\s+\d+(?:[.,]\d+)?\s*€|Between\s+\d+(?:[.,]\d+)?\s*€\s+and\s+\d+(?:[.,]\d+)?\s*€|Entrada libre|Gratis|\d+(?:[.,]\d+)?\s*€)",
        text,
        re.IGNORECASE,
    )
    return _clean_text(match.group(0)) if match else ""


def _extract_location_text(container: BeautifulSoup | Tag) -> str:
    selectors = [
        ".module-direction-location",
        ".fever-plan__location-link",
        ".module-location",
    ]
    for selector in selectors:
        node = container.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                return text

    for node in container.find_all(class_=re.compile("location|direction", re.IGNORECASE)):
        text = _clean_text(node.get_text(" ", strip=True))
        if text and 5 <= len(text) <= 180 and "enter location" not in text.lower():
            return text

    text = _clean_text(container.get_text(" ", strip=True))
    match = LOCATION_INLINE_RE.search(text)
    return _clean_text(match.group(1)) if match else ""


def _extract_dates_text(container: BeautifulSoup | Tag) -> str:
    selectors = [
        ".module-dates",
        ".fever-plan__date",
    ]
    for selector in selectors:
        node = container.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if _parse_spanish_dates(text)[2]:
                return text

    for node in container.find_all(class_=re.compile("date", re.IGNORECASE)):
        text = _clean_text(node.get_text(" ", strip=True))
        if _parse_spanish_dates(text)[2]:
            return text

    text = _clean_text(container.get_text(" ", strip=True))
    for pattern in (RANGE_DATE_RE, MULTI_DAY_RE, SINGLE_DATE_RE):
        match = pattern.search(text)
        if match:
            return _clean_text(match.group(0))
    return ""


def _extract_action_url(container: BeautifulSoup | Tag) -> str | None:
    preferred = [
        'a[href*="feverup.com"]',
        'a[href*="eventbrite."]',
        'a[href*="ticket"]',
        'a[href*="entradas"]',
    ]
    for selector in preferred:
        node = container.select_one(selector)
        if node and node.get("href"):
            return node.get("href")

    for node in container.find_all("a", href=True):
        href = node.get("href")
        if href and href.startswith("http") and "madridsecreto.co" not in href:
            return href
    return None


def _base_event(post: dict, *, tipo_origen: str) -> dict:
    return {
        "categorias": _extract_post_categories(post),
        "etiquetas": _extract_post_tags(post),
        "autor": _extract_post_author(post),
        "fecha_publicacion": post.get("date"),
        "fecha_actualizacion": post.get("modified"),
        "tipo_origen": tipo_origen,
        "fuente": "madrid_secreto",
        "url_fuente_editorial": post.get("link"),
    }


def _build_post_event(post: dict, content_soup: BeautifulSoup) -> dict:
    title = _clean_text(post.get("title", {}).get("rendered"))
    excerpt = _extract_excerpt(post)
    description = excerpt or _extract_post_content(content_soup, max_length=700)
    content = _extract_post_content(content_soup, max_length=4000)

    price_text = _extract_price_text(content_soup)
    price, currency = _parse_price(price_text)
    location = _extract_location_text(content_soup)
    dates_text = _extract_dates_text(content_soup)
    start, end, available = _parse_spanish_dates(dates_text or content)
    image = _extract_featured_image(post) or _extract_first_image(content_soup)
    action_url = _extract_action_url(content_soup)

    event = {
        "id": post.get("slug") or _slugify(title),
        "titulo": title,
        "precio": price,
        "moneda": currency,
        "lugar": location.split("|", 1)[0].strip() if "|" in location else location,
        "direccion": location,
        "latitud": None,
        "longitud": None,
        "fecha_inicio": start,
        "fecha_fin": end,
        "fechas_disponibles": available,
        "url": post.get("link"),
        "url_articulo": post.get("link"),
        "url_compra": action_url,
        "imagen": image,
        "descripcion": description,
        "contenido": content,
    }
    event.update(_base_event(post, tipo_origen="post"))
    return event


def _build_module_event(post: dict, heading: Tag, section: BeautifulSoup) -> dict | None:
    title_link = heading.find("a")
    title = _clean_text(
        title_link.get_text(" ", strip=True) if title_link else heading.get_text(" ", strip=True)
    )
    if not title:
        return None

    location = _extract_location_text(section)
    dates_text = _extract_dates_text(section)
    price_text = _extract_price_text(section)
    action_url = _extract_action_url(section)

    if not any([location, dates_text, price_text, action_url]):
        return None

    price, currency = _parse_price(price_text)
    start, end, available = _parse_spanish_dates(dates_text)
    description = _extract_post_content(section, max_length=700)
    content = _extract_post_content(section, max_length=2500)
    article_url = title_link.get("href") if title_link and title_link.get("href") else post.get("link")
    image = _extract_first_image(section) or _extract_featured_image(post)

    event = {
        "id": _slugify(urlparse(article_url).path.rsplit("/", 1)[-1] if article_url else title),
        "titulo": title,
        "precio": price,
        "moneda": currency,
        "lugar": location.split("|", 1)[0].strip() if "|" in location else location,
        "direccion": location,
        "latitud": None,
        "longitud": None,
        "fecha_inicio": start,
        "fecha_fin": end,
        "fechas_disponibles": available,
        "url": article_url,
        "url_articulo": article_url,
        "url_compra": action_url if action_url and "madridsecreto.co" not in action_url else None,
        "imagen": image,
        "descripcion": description,
        "contenido": content,
    }
    event.update(_base_event(post, tipo_origen="roundup"))
    return event


def _extract_module_events(post: dict, content_html: str) -> list[dict]:
    events: list[dict] = []
    for match in MODULE_SECTION_RE.finditer(content_html):
        section = BeautifulSoup(match.group("section"), "html.parser")
        heading = section.find("h2")
        if not isinstance(heading, Tag):
            continue
        event = _build_module_event(post, heading, section)
        if event:
            events.append(event)
    return events


def _extract_embedded_plan_events(post: dict, content_soup: BeautifulSoup) -> list[dict]:
    description = _extract_post_content(content_soup, max_length=700)
    content = _extract_post_content(content_soup, max_length=3000)
    events: list[dict] = []

    for node in content_soup.select("[data-fever-plan-id]"):
        plan_id = node.get("data-fever-plan-id")
        title = _clean_text(node.get("data-fever-plan-name"))
        if not plan_id or not title:
            continue

        date_start = node.get("data-fever-plan-date")
        location = _extract_location_text(node)
        address = _clean_text(node.get("data-fever-plan-brand")) or location
        price_raw = node.get("data-fever-plan-price")
        price = float(price_raw) if price_raw else None
        currency = node.get("data-fever-plan-currency") or ("EUR" if price is not None else None)
        plan_url = _extract_action_url(node) or post.get("link")
        image = _extract_first_image(node) or _extract_featured_image(post)

        event = {
            "id": f"ms-fever-{plan_id}",
            "titulo": title,
            "precio": price,
            "moneda": currency,
            "lugar": location,
            "direccion": address,
            "latitud": None,
            "longitud": None,
            "fecha_inicio": date_start,
            "fecha_fin": None,
            "fechas_disponibles": [date_start] if date_start else [],
            "url": plan_url,
            "url_articulo": post.get("link"),
            "url_compra": plan_url if plan_url and "madridsecreto.co" not in plan_url else None,
            "imagen": image,
            "descripcion": description,
            "contenido": content,
        }
        event.update(_base_event(post, tipo_origen="embedded_fever"))
        events.append(event)

    return events


def _event_key(event: dict) -> str:
    if event.get("tipo_origen") == "embedded_fever" and event.get("url"):
        return event["url"]

    article_url = event.get("url_articulo")
    source_url = event.get("url_fuente_editorial") or article_url
    if event.get("tipo_origen") == "post" and article_url:
        return article_url
    if article_url and article_url != source_url:
        return article_url
    if source_url:
        return f"{source_url}::{_slugify(event.get('titulo') or '')}"
    return f"{_slugify(event.get('titulo') or '')}::{event.get('fecha_inicio') or event.get('fecha_publicacion')}"


def _merge_events(current: dict, incoming: dict) -> dict:
    merged = dict(current)

    for key, value in incoming.items():
        if value in (None, "", []):
            continue

        if key in LIST_FIELDS:
            existing = merged.get(key) or []
            merged[key] = sorted(dict.fromkeys(existing + value))
            continue

        if key in LONG_TEXT_FIELDS:
            if len(str(value)) > len(str(merged.get(key) or "")):
                merged[key] = value
            continue

        if merged.get(key) in (None, "", []):
            merged[key] = value

    return merged


def _is_current_plan(event: dict, today: date) -> bool:
    max_future = today + timedelta(days=ACTIVE_PLAN_MAX_FUTURE_DAYS)
    start = _parse_datetime(event.get("fecha_inicio"))
    end = _parse_datetime(event.get("fecha_fin"))

    if start or end:
        first = (start or end).date()
        last = (end or start).date()
        return last >= today and first <= max_future

    editorial = _parse_datetime(event.get("fecha_actualizacion")) or _parse_datetime(
        event.get("fecha_publicacion")
    )
    if editorial is None:
        return False

    return editorial.date() >= today - timedelta(days=UNDATED_PLAN_LOOKBACK_DAYS)


def _current_plan_key(event: dict) -> str:
    title = _slugify(event.get("titulo") or "")
    location = _slugify(event.get("lugar") or event.get("direccion") or "")
    when = (
        event.get("fecha_inicio")
        or event.get("fecha_fin")
        or event.get("fecha_actualizacion")
        or event.get("fecha_publicacion")
        or ""
    )

    if title and when:
        return f"{title}::{when}::{location}"

    if event.get("url_compra"):
        return event["url_compra"]

    event_url = event.get("url")
    if event_url and "madridsecreto.co" not in event_url:
        return event_url

    return f"{title}::{when}::{location}"


def _filter_current_events(events: list[dict]) -> list[dict]:
    today = date.today()
    filtered_by_key: dict[str, dict] = {}

    for event in events:
        if not _is_current_plan(event, today):
            continue

        key = _current_plan_key(event)
        current = filtered_by_key.get(key)
        filtered_by_key[key] = _merge_events(current, event) if current else event

    output = list(filtered_by_key.values())
    output.sort(
        key=lambda event: (
            event.get("fecha_inicio") or event.get("fecha_publicacion") or "",
            event.get("titulo") or "",
        ),
        reverse=True,
    )
    return output


def scrape_madrid_secreto() -> list[dict]:
    """Scrape a current/future Madrid Secreto plans feed."""
    category_id = _get_que_hacer_category_id()
    if category_id is None:
        log.error("Could not resolve `que-hacer` category")
        return []

    try:
        posts = _fetch_all_posts(category_id)
    except requests.RequestException as error:
        log.error("Failed to fetch Madrid Secreto archive: %s", error)
        return []

    if not posts:
        log.error("No posts fetched from Madrid Secreto")
        return []

    events_by_key: dict[str, dict] = {}
    generic_count = 0
    module_count = 0
    embedded_count = 0

    for index, post in enumerate(posts, start=1):
        content_html = post.get("content", {}).get("rendered") or ""
        content_soup = BeautifulSoup(content_html, "html.parser")

        records: list[dict] = [_build_post_event(post, content_soup)]
        generic_count += 1

        if "module-title" in content_html:
            module_events = _extract_module_events(post, content_html)
            records.extend(module_events)
            module_count += len(module_events)

        if "data-fever-plan-id" in content_html:
            embedded_events = _extract_embedded_plan_events(post, content_soup)
            records.extend(embedded_events)
            embedded_count += len(embedded_events)

        for event in records:
            key = _event_key(event)
            current = events_by_key.get(key)
            events_by_key[key] = _merge_events(current, event) if current else event

        if index % 250 == 0 or index == len(posts):
            log.info(
                "Processed %d/%d Madrid Secreto posts, %d unique plan records",
                index, len(posts), len(events_by_key),
            )

    raw_output = list(events_by_key.values())
    output = _filter_current_events(raw_output)
    output = normalize_plan_records(output, source="madrid_secreto")

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Generic post records: %d", generic_count)
    log.info("Module-derived records: %d", module_count)
    log.info("Embedded Fever records: %d", embedded_count)
    log.info(
        "Filtered Madrid Secreto feed to %d current/future plans (%d raw merged records)",
        len(output),
        len(raw_output),
    )
    log.info("Saved %d plan records to %s", len(output), OUTPUT_FILE)
    return output


if __name__ == "__main__":
    results = scrape_madrid_secreto()
    with_price = sum(1 for event in results if event.get("precio") is not None)
    with_dates = sum(1 for event in results if event.get("fecha_inicio"))
    log.info(
        "Summary: %d plans, %d with price, %d with dates",
        len(results), with_price, with_dates,
    )