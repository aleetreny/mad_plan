"""Helpers for extracting representative images from external pages."""

from __future__ import annotations

import json
import logging
from html import unescape
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:
    PlaywrightTimeoutError = Exception
    sync_playwright = None

log = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
DEFAULT_IGNORED_IMAGE_TOKENS = (
    "data:image",
    "maps.googleapis.com/maps",
    "maps.gstatic.com",
    "spotlight-poi",
    "transparent.png",
    "cookielaw.org",
    "powered_by_logo",
    "onetrust",
    "favicon",
    "apple-touch-icon",
)
IMAGE_ATTRS = ("src", "data-src", "data-lazy-src", "data-original")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(unescape(str(value)).replace("\xa0", " ").split())


def _build_headers(headers: dict[str, str] | None) -> dict[str, str]:
    merged = dict(DEFAULT_HEADERS)
    if headers:
        merged.update(headers)
    return merged


def _normalize_image_url(value: Any, base_url: str) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return urljoin(base_url, text)


def _iter_image_values(value: Any):
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, list):
        for item in value:
            yield from _iter_image_values(item)
        return

    if isinstance(value, dict):
        for key in ("url", "contentUrl", "thumbnailUrl", "src", "image", "images"):
            if key not in value:
                continue
            yield from _iter_image_values(value.get(key))


def _iter_json_ld_candidates(soup: BeautifulSoup, base_url: str):
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        stack = [payload]
        while stack:
            current = stack.pop()
            if isinstance(current, list):
                stack.extend(current)
                continue
            if not isinstance(current, dict):
                continue

            image = current.get("image")
            if image is not None:
                for candidate in _iter_image_values(image):
                    url = _normalize_image_url(candidate, base_url)
                    if url:
                        yield {
                            "url": url,
                            "source": "jsonld",
                            "index": 0,
                            "width": 0,
                            "height": 0,
                            "alt": "",
                            "class_name": "",
                        }

            graph = current.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)


def _iter_meta_candidates(soup: BeautifulSoup, base_url: str):
    selectors = (
        ('meta[property="og:image"]', "meta"),
        ('meta[name="twitter:image"]', "meta"),
        ('meta[property="twitter:image"]', "meta"),
    )
    for selector, source in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        url = _normalize_image_url(node.get("content"), base_url)
        if not url:
            continue
        yield {
            "url": url,
            "source": source,
            "index": 0,
            "width": 0,
            "height": 0,
            "alt": "",
            "class_name": "",
        }


def _iter_img_candidates(soup: BeautifulSoup, base_url: str):
    for index, image in enumerate(soup.find_all("img")):
        candidate_url = None
        for attr in IMAGE_ATTRS:
            candidate_url = _normalize_image_url(image.get(attr), base_url)
            if candidate_url:
                break
        if not candidate_url:
            continue

        width = image.get("width")
        height = image.get("height")
        try:
            width_value = int(width) if width else 0
        except (TypeError, ValueError):
            width_value = 0
        try:
            height_value = int(height) if height else 0
        except (TypeError, ValueError):
            height_value = 0

        yield {
            "url": candidate_url,
            "source": "img",
            "index": index,
            "width": width_value,
            "height": height_value,
            "alt": _clean_text(image.get("alt")),
            "class_name": _clean_text(image.get("class")),
        }


def _candidate_allowed(url: str, ignored_tokens: tuple[str, ...]) -> bool:
    lowered = url.casefold()
    return all(token not in lowered for token in ignored_tokens)


def _score_candidate(candidate: dict[str, Any], preferred_url_tokens: tuple[str, ...]) -> tuple[int, int, int, int]:
    url_blob = candidate["url"].casefold()
    aux_blob = f"{candidate.get('alt', '')} {candidate.get('class_name', '')}".casefold()
    preferred_score = 0
    for token in preferred_url_tokens:
        lowered = token.casefold()
        if lowered in url_blob:
            preferred_score += 6
        if lowered in aux_blob:
            preferred_score += 3

    source_weight = {
        "meta": 4,
        "jsonld": 3,
        "rendered_img": 2,
        "img": 1,
    }.get(candidate.get("source"), 0)
    area = int(candidate.get("width") or 0) * int(candidate.get("height") or 0)
    return (preferred_score, source_weight, area, -int(candidate.get("index") or 0))


def _select_best_candidate(
    candidates: list[dict[str, Any]],
    *,
    preferred_url_tokens: tuple[str, ...],
    ignored_tokens: tuple[str, ...],
) -> str | None:
    seen: set[str] = set()
    filtered: list[dict[str, Any]] = []
    for candidate in candidates:
        url = candidate.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        if not _candidate_allowed(url, ignored_tokens):
            continue
        filtered.append(candidate)

    if not filtered:
        return None
    return max(
        filtered,
        key=lambda candidate: _score_candidate(candidate, preferred_url_tokens),
    )["url"]


def extract_rendered_page_image(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    preferred_url_tokens: tuple[str, ...] = (),
    ignored_tokens: tuple[str, ...] = (),
    timeout_ms: int = 60000,
) -> str | None:
    if sync_playwright is None:
        return None

    merged_headers = _build_headers(headers)
    candidate_list: list[dict[str, Any]] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=merged_headers["User-Agent"],
                locale="es-ES",
            )
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            candidate_list.extend(_iter_meta_candidates(soup, page.url))
            candidate_list.extend(_iter_json_ld_candidates(soup, page.url))

            rendered = page.locator("img").evaluate_all(
                """
els => els.map((el, index) => ({
  url: el.currentSrc || el.src || '',
  source: 'rendered_img',
  index,
  width: el.naturalWidth || 0,
  height: el.naturalHeight || 0,
  alt: el.alt || '',
  class_name: el.className || ''
}))
"""
            )
            for candidate in rendered:
                candidate_url = _normalize_image_url(candidate.get("url"), page.url)
                if not candidate_url:
                    continue
                candidate_list.append({
                    **candidate,
                    "url": candidate_url,
                })
            browser.close()
    except Exception as error:
        log.debug("Rendered image extraction failed for %s: %s", url, error)
        return None

    return _select_best_candidate(
        candidate_list,
        preferred_url_tokens=preferred_url_tokens,
        ignored_tokens=DEFAULT_IGNORED_IMAGE_TOKENS + tuple(token.casefold() for token in ignored_tokens),
    )


def extract_page_image(
    url: str,
    *,
    session: requests.Session | None = None,
    headers: dict[str, str] | None = None,
    preferred_url_tokens: tuple[str, ...] = (),
    ignored_tokens: tuple[str, ...] = (),
    use_render: bool = False,
) -> str | None:
    merged_headers = _build_headers(headers)
    ignored = DEFAULT_IGNORED_IMAGE_TOKENS + tuple(token.casefold() for token in ignored_tokens)

    response = None
    try:
        if session is not None:
            response = session.get(url, headers=merged_headers, timeout=REQUEST_TIMEOUT)
        else:
            response = requests.get(url, headers=merged_headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as error:
        log.debug("Static image extraction failed for %s: %s", url, error)
        response = None

    if response is not None:
        soup = BeautifulSoup(response.text, "html.parser")
        candidates = list(_iter_meta_candidates(soup, response.url))
        candidates.extend(_iter_json_ld_candidates(soup, response.url))
        candidates.extend(_iter_img_candidates(soup, response.url))
        image = _select_best_candidate(
            candidates,
            preferred_url_tokens=preferred_url_tokens,
            ignored_tokens=ignored,
        )
        if image:
            return image

    if use_render:
        return extract_rendered_page_image(
            url,
            headers=merged_headers,
            preferred_url_tokens=preferred_url_tokens,
            ignored_tokens=ignored_tokens,
        )
    return None