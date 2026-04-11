"""
Time Out Madrid news scraper.

Strategy:
    1. Discover article URLs from the most recent Time Out monthly sitemaps.
    2. Keep only genuinely recent news items for the daily news feed.
    3. Fetch article detail pages and parse JSON-LD NewsArticle metadata plus body text.

Output: outputs/noticias_timeout.json
"""

import concurrent.futures
import json
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.timeout.es"
SITEMAPS_INDEX_URL = f"{BASE_URL}/madrid/es/sitemaps"
REQUEST_DELAY = 0.15
MAX_WORKERS = 4
RECENT_SITEMAP_MONTHS = 3
NEWS_LOOKBACK_DAYS = 21
NEWS_CHECKPOINT_SIZE = 50
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "outputs" / "noticias_timeout.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}

PROXY_PREFIX = "https://r.jina.ai/http://"
PROXY_IMAGE_URL_RE = re.compile(r"!\[[^\]]*\]\((?P<url>[^)]+)\)")
PROXY_AUTHOR_RE = re.compile(r"Escrito por \[(?P<author>[^\]]+)\]")
PROXY_STOP_LINE_SNIPPETS = {
    "popular en time out",
    "mas de ",
    "ultimas noticias",
    "mas noticias",
    "discover time out original video",
    "volver arriba",
    "time out en tu buzon de entrada",
    "quienes somos",
}

MONTH_URL_RE = re.compile(
    r'href="(?P<url>(?:https://www\.timeout\.es)?/madrid/es/sitemaps/\d{4}/\d{2})"'
)
ARTICLE_URL_RE = re.compile(
    r'href="(?P<url>(?:https://www\.timeout\.es)?/madrid/es/noticias/[^"#?]+)"'
)

IGNORED_PARAGRAPH_SNIPPETS = {
    "gracias por suscribirte",
    "apuntate a nuestras newsletters",
    "apuntate a nuestra newsletter",
    "facilitando tu correo electronico",
    "terminos de uso",
    "politica de privacidad",
    "tu ciudad te encanta",
    "time out en tu buzon de entrada",
    "introduce tu email",
    "administrar cookies",
    "buscas mas planes",
    "publicidad",
}

IGNORED_HEADING_SNIPPETS = {
    "no te lo pierdas",
    "buscas mas planes",
    "newsletter",
}

_thread_local = threading.local()
_bootstrap_lock = threading.Lock()
_seed_cookies: list[dict] | None = None


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.replace("\xa0", " ").split())


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _news_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=NEWS_LOOKBACK_DAYS)


def _is_recent_news(item: dict, cutoff: datetime) -> bool:
    published = _parse_iso_datetime(item.get("fecha_publicacion"))
    if published is None:
        return False
    return published >= cutoff


def _extract_urls(pattern: re.Pattern[str], html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(html):
        url = urljoin(base_url, match.group("url"))
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def _extract_meta(soup: BeautifulSoup, key: str) -> str | None:
    tag = soup.find("meta", attrs={"property": key}) or soup.find(
        "meta", attrs={"name": key}
    )
    if tag:
        return tag.get("content")
    return None


def _load_news_article_json_ld(soup: BeautifulSoup) -> dict | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string)
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "NewsArticle":
                return item
    return None


def _extract_author(article: dict) -> str | None:
    author = article.get("author") or article.get("creator")
    if isinstance(author, dict):
        return author.get("name")
    if isinstance(author, list):
        names = [a.get("name") for a in author if isinstance(a, dict) and a.get("name")]
        return ", ".join(names) if names else None
    if isinstance(author, str):
        return author
    return None


def _extract_image(article: dict) -> str | None:
    image = article.get("image") or article.get("thumbnailUrl")
    if isinstance(image, list):
        return image[0] if image else None
    if isinstance(image, dict):
        return image.get("url")
    if isinstance(image, str):
        return image
    return None


def _extract_keywords(article: dict) -> list[str]:
    keywords = article.get("keywords")
    if isinstance(keywords, list):
        values = [_clean_text(value) for value in keywords]
        return [value for value in values if value]
    if isinstance(keywords, str):
        values = [_clean_text(value) for value in keywords.split(",")]
        return [value for value in values if value]
    return []


def _extract_category(article: dict, keywords: list[str]) -> str | None:
    category = _clean_text(article.get("articleSection"))
    if category and category.lower() not in {"madrid", "noticias"}:
        return category
    if keywords:
        return keywords[0].split(":", 1)[0].strip()
    return category or None


def _is_ignored_paragraph(text: str) -> bool:
    lowered = text.lower()
    return any(snippet in lowered for snippet in IGNORED_PARAGRAPH_SNIPPETS)


def _find_article_container(soup: BeautifulSoup, title: str) -> Tag:
    title_text = _clean_text(title).lower()
    candidates = soup.find_all(["article", "main", "section"])
    best_node: Tag | None = None
    best_score = -1

    for node in candidates:
        node_text = _clean_text(node.get_text(" ", strip=True)).lower()
        if title_text and title_text not in node_text:
            continue

        score = 0
        for paragraph in node.find_all("p"):
            text = _clean_text(paragraph.get_text(" ", strip=True))
            if len(text) < 40 or _is_ignored_paragraph(text):
                continue
            score += 1

        if score > best_score:
            best_node = node
            best_score = score

    if best_node is not None:
        return best_node

    main = soup.find("main")
    if isinstance(main, Tag):
        return main
    return soup


def _extract_body_data(soup: BeautifulSoup, title: str) -> tuple[str, str, list[str]]:
    container = _find_article_container(soup, title)

    paragraphs: list[str] = []
    for paragraph in container.find_all("p"):
        text = _clean_text(paragraph.get_text(" ", strip=True))
        if len(text) < 40 or _is_ignored_paragraph(text):
            continue
        if text not in paragraphs:
            paragraphs.append(text)

    sections: list[str] = []
    for heading in container.find_all(["h2", "h3"]):
        text = _clean_text(heading.get_text(" ", strip=True))
        if not text:
            continue
        lowered = text.lower()
        if any(snippet in lowered for snippet in IGNORED_HEADING_SNIPPETS):
            continue
        if text not in sections:
            sections.append(text)

    full_body = " ".join(paragraphs)
    excerpt = full_body[:500]
    return excerpt, full_body, sections


def _proxy_url(url: str) -> str:
    return f"{PROXY_PREFIX}{url}"


def _get_proxy(url: str) -> requests.Response:
    last_error: Exception | None = None
    session = getattr(_thread_local, "proxy_session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": HEADERS["User-Agent"]})
        _thread_local.proxy_session = session

    for attempt in range(5):
        try:
            response = session.get(_proxy_url(url), timeout=30)
            if response.status_code == 429:
                last_error = requests.HTTPError(
                    f"Time Out proxy rate limited for {url}", response=response
                )
                time.sleep(2.0 * (attempt + 1))
                continue
            response.raise_for_status()
            return response
        except Exception as error:
            last_error = error
            time.sleep(1.0 + attempt)

    assert last_error is not None
    raise last_error


def _strip_markdown(value: str) -> str:
    text = value
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("`", "")
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"^[*-]\s*", "", text)
    return _clean_text(text)


def _extract_proxy_meta_line(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            return _clean_text(line.split(":", 1)[1])
    return None


def _proxy_markdown_lines(text: str) -> list[str]:
    _, _, content = text.partition("Markdown Content:")
    return content.splitlines() if content else text.splitlines()


def _find_proxy_title_index(lines: list[str], title: str) -> int:
    normalized_title = _clean_text(title)
    candidates: list[int] = []
    for index, line in enumerate(lines):
        if _strip_markdown(line) == normalized_title:
            candidates.append(index)

    best_index = candidates[0] if candidates else 0
    best_score = -1
    for index in candidates:
        lookahead = " ".join(lines[index : index + 30]).lower()
        score = 0
        if "escrito por" in lookahead:
            score += 4
        if "##" in lookahead:
            score += 2
        if "publicidad" in lookahead:
            score += 1
        if score >= best_score:
            best_index = index
            best_score = score

    return best_index


def _extract_proxy_author(lines: list[str], title_index: int) -> str | None:
    for raw_line in lines[title_index : title_index + 25]:
        if "Escrito por" not in raw_line:
            continue
        match = PROXY_AUTHOR_RE.search(raw_line)
        if match:
            return _clean_text(match.group("author"))
    return None


def _extract_proxy_subtitle(lines: list[str], title_index: int) -> str:
    for raw_line in lines[title_index + 1 : title_index + 15]:
        cleaned = _strip_markdown(raw_line)
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if cleaned == "Noticias" or cleaned.startswith("Escrito por"):
            continue
        if any(snippet in lowered for snippet in IGNORED_PARAGRAPH_SNIPPETS):
            continue
        if len(cleaned) < 25:
            continue
        return cleaned
    return ""


def _extract_proxy_image(lines: list[str], title_index: int) -> str | None:
    for line in lines[title_index : title_index + 40]:
        for match in PROXY_IMAGE_URL_RE.finditer(line):
            url = match.group("url")
            lowered = url.lower()
            if any(snippet in lowered for snippet in {"loading_icon", "ib.adnxs.com", "gcprivacy", "getuid", "/170/170/"}):
                continue
            if "media.timeout.com" in lowered:
                return url
    return None


def _extract_proxy_body_data(lines: list[str], title: str, title_index: int) -> tuple[str, list[str]]:
    paragraphs: list[str] = []
    sections: list[str] = []

    for raw_line in lines[title_index + 1 :]:
        cleaned = _strip_markdown(raw_line)
        if not cleaned:
            continue

        lowered = cleaned.lower()
        if any(snippet in lowered for snippet in PROXY_STOP_LINE_SNIPPETS):
            break
        if cleaned == title or cleaned == "Noticias" or cleaned.startswith("Escrito por"):
            continue

        if raw_line.lstrip().startswith(("##", "###")):
            if any(snippet in lowered for snippet in IGNORED_HEADING_SNIPPETS):
                continue
            if cleaned not in sections:
                sections.append(cleaned)
            continue

        if len(cleaned) < 40:
            continue
        if any(snippet in lowered for snippet in IGNORED_PARAGRAPH_SNIPPETS):
            continue
        if cleaned not in paragraphs:
            paragraphs.append(cleaned)

    return " ".join(paragraphs), sections


def _scrape_article_via_proxy(url: str) -> dict | None:
    response = _get_proxy(url)
    text = response.text
    canonical_url = _extract_proxy_meta_line(text, "URL Source:") or url
    title = _extract_proxy_meta_line(text, "Title:") or ""
    published_time = _extract_proxy_meta_line(text, "Published Time:")
    if not title:
        return None

    lines = _proxy_markdown_lines(text)
    title_index = _find_proxy_title_index(lines, title)
    subtitle = _extract_proxy_subtitle(lines, title_index)
    body, sections = _extract_proxy_body_data(lines, title, title_index)
    image = _extract_proxy_image(lines, title_index)
    author = _extract_proxy_author(lines, title_index)

    path = urlparse(canonical_url).path.rstrip("/")
    item_id = path.rsplit("/", 1)[-1] if path else title

    return {
        "id": item_id,
        "titulo": title,
        "subtitulo": subtitle,
        "categoria": "Noticias",
        "etiquetas": [],
        "autor": author,
        "fecha_publicacion": published_time,
        "fecha_actualizacion": None,
        "url": canonical_url,
        "imagen": image,
        "descripcion": subtitle or body[:500],
        "contenido": body or subtitle,
        "secciones": sections,
        "fuente": "timeout",
    }


def _bootstrap_cookies(force_refresh: bool = False) -> list[dict]:
    global _seed_cookies

    with _bootstrap_lock:
        if _seed_cookies is not None and not force_refresh:
            return _seed_cookies

        log.info("Bootstrapping Time Out browser session")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="es-ES",
            )
            page = context.new_page()
            page.goto(SITEMAPS_INDEX_URL, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeoutError:
                pass

            body_text = page.text_content("body") or ""
            if "Human Verification" in body_text:
                raise RuntimeError("Time Out browser bootstrap hit human verification")

            new_cookies = context.cookies()
            browser.close()

        if not new_cookies:
            if _seed_cookies:
                log.warning("Playwright bootstrap returned no Time Out cookies; keeping previous session")
                return _seed_cookies
            raise RuntimeError("Playwright bootstrap returned no Time Out cookies")

        _seed_cookies = new_cookies

        log.info("Bootstrapped %d Time Out cookies", len(_seed_cookies))
        return _seed_cookies


def _build_session(force_cookie_refresh: bool = False) -> requests.Session:
    cookies = _bootstrap_cookies(force_refresh=force_cookie_refresh)
    session = requests.Session()
    session.headers.update(HEADERS)
    for cookie in cookies:
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path", "/"),
        )
    return session


def _get_thread_session(force_cookie_refresh: bool = False) -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None or force_cookie_refresh:
        session = _build_session(force_cookie_refresh=force_cookie_refresh)
        _thread_local.session = session
    return session


def _invalidate_thread_session() -> None:
    if hasattr(_thread_local, "session"):
        delattr(_thread_local, "session")


def _needs_browser_refresh(response: requests.Response) -> bool:
    if response.status_code in {403, 405}:
        return True
    return "Human Verification" in response.text


def _get(url: str) -> requests.Response:
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            session = _get_thread_session()
            response = session.get(url, timeout=20)
            if _needs_browser_refresh(response):
                last_error = requests.HTTPError(
                    f"Time Out verification wall for {url}", response=response
                )
                _invalidate_thread_session()
                if attempt == 0:
                    _bootstrap_cookies(force_refresh=True)
                    time.sleep(1.0)
                    continue
                raise last_error

            if response.status_code in {404, 410}:
                response.raise_for_status()

            response.raise_for_status()
            return response
        except Exception as error:
            last_error = error
            if attempt == 0:
                time.sleep(1.0)
                continue
            break

    assert last_error is not None
    raise last_error


def _write_news_output(news_items: list[dict]) -> None:
    ordered_items = sorted(
        news_items,
        key=lambda item: (
            item.get("fecha_publicacion") or "",
            item.get("id") or "",
        ),
        reverse=True,
    )
    OUTPUT_FILE.write_text(
        json.dumps(ordered_items, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _collect_month_urls() -> list[str]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=HEADERS["User-Agent"],
            locale="es-ES",
        )
        page.goto(SITEMAPS_INDEX_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        html = page.content()
        browser.close()

    all_month_urls = sorted(_extract_urls(MONTH_URL_RE, html, BASE_URL), reverse=True)
    month_urls = all_month_urls[:RECENT_SITEMAP_MONTHS]
    log.info(
        "Found %d monthly sitemap pages, scanning %d recent months",
        len(all_month_urls),
        len(month_urls),
    )
    return month_urls


def _collect_article_urls() -> list[str]:
    month_urls = _collect_month_urls()
    article_urls: list[str] = []
    seen: set[str] = set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=HEADERS["User-Agent"],
            locale="es-ES",
        )

        for index, month_url in enumerate(month_urls, start=1):
            try:
                page.goto(month_url, wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except PlaywrightTimeoutError:
                    pass
                html = page.content()
            except Exception as error:
                log.warning("Failed to fetch sitemap month %s: %s", month_url, error)
                continue

            urls = _extract_urls(ARTICLE_URL_RE, html, BASE_URL)
            new_count = 0
            for url in urls:
                if url in seen:
                    continue
                seen.add(url)
                article_urls.append(url)
                new_count += 1

            if index % 12 == 0 or index == len(month_urls):
                log.info(
                    "Processed %d/%d sitemap months, %d unique news URLs (+%d latest)",
                    index, len(month_urls), len(article_urls), new_count,
                )
            time.sleep(REQUEST_DELAY)

        browser.close()

    return article_urls


def _scrape_article(url: str) -> dict | None:
    try:
        response = _get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        article = _load_news_article_json_ld(soup)
        if not article:
            raise RuntimeError("Missing NewsArticle JSON-LD")

        canonical_url = article.get("url") or url
        title = _clean_text(article.get("headline") or article.get("name"))
        subtitle = _extract_meta(soup, "description") or _extract_meta(soup, "og:description")
        keywords = _extract_keywords(article)
        category = _extract_category(article, keywords)
        image = _extract_image(article) or _extract_meta(soup, "og:image")
        excerpt, body, sections = _extract_body_data(soup, title)

        path = urlparse(canonical_url).path.rstrip("/")
        item_id = path.rsplit("/", 1)[-1] if path else title

        return {
            "id": item_id,
            "titulo": title,
            "subtitulo": _clean_text(subtitle),
            "categoria": category,
            "etiquetas": keywords,
            "autor": _extract_author(article),
            "fecha_publicacion": article.get("datePublished"),
            "fecha_actualizacion": article.get("dateModified"),
            "url": canonical_url,
            "imagen": image,
            "descripcion": excerpt or _clean_text(subtitle),
            "contenido": body or _clean_text(subtitle),
            "secciones": sections,
            "fuente": "timeout",
        }
    except Exception:
        return _scrape_article_via_proxy(url)


def scrape_timeout_news() -> list[dict]:
    """Scrape a recent Time Out Madrid news feed suitable for daily refreshes."""
    try:
        article_urls = _collect_article_urls()
    except Exception as error:
        log.error("Failed to collect article URLs from sitemaps: %s", error)
        return []

    cutoff = _news_cutoff()
    log.info("Collected %d unique Time Out news URLs", len(article_urls))
    log.info(
        "Keeping only Time Out news from the last %d days (cutoff %s)",
        NEWS_LOOKBACK_DAYS,
        cutoff.date().isoformat(),
    )
    if not article_urls:
        return []

    news_items: list[dict] = []
    seen_urls: set[str] = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_scrape_article, url): url for url in article_urls}
        total = len(futures)

        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            url = futures[future]
            try:
                item = future.result()
            except Exception as error:
                log.warning("Failed to fetch article %s: %s", url, error)
                continue

            if not item:
                continue
            if not _is_recent_news(item, cutoff):
                continue

            canonical_url = item.get("url")
            if canonical_url in seen_urls:
                continue
            seen_urls.add(canonical_url)
            news_items.append(item)

            if len(news_items) % NEWS_CHECKPOINT_SIZE == 0:
                _write_news_output(news_items)
                log.info("Checkpoint saved %d Time Out news items", len(news_items))

            if index % 100 == 0 or index == total:
                log.info("Processed %d/%d Time Out articles", index, total)

    _write_news_output(news_items)
    log.info("Saved %d news items to %s", len(news_items), OUTPUT_FILE)
    return news_items


if __name__ == "__main__":
    results = scrape_timeout_news()
    by_category: dict[str, int] = {}
    for item in results:
        category = item.get("categoria") or "Sin categoria"
        by_category[category] = by_category.get(category, 0) + 1
    log.info("Summary: %d news items, %d categories", len(results), len(by_category))