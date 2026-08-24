"""Live website fetching for the offline crawl and the fetch_website agent
tool - the same per-page fetch/parse logic backs both, so a page is only ever
parsed one way. Callers are responsible for domain whitelist validation
(config/whitelist.py) both before calling and on the returned final_url,
since Crawl4AI drives a real browser that can follow redirects off-domain.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from config.seed_urls import BASE_URL, CRAWL_SEED_URLS

CRAWLED_PAGES_DIR = Path("data/crawled_pages")
FETCH_TIMEOUT_SECONDS = 10
_RUN_CONFIG = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
_BROWSER_CONFIG = BrowserConfig(headless=True)


@dataclass
class FetchedPage:
    requested_url: str
    final_url: str
    markdown: str
    fetched_at: str
    success: bool
    error: str | None = None


def _slugify_url_for_filename(url_path: str) -> str:
    """Windows-safe filename from a URL path (query params contain ?, &, :,
    which are invalid or awkward in Windows filenames)."""
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", url_path)
    return safe.strip("_")[:150] or "page"


async def _run_single_fetch(crawler: AsyncWebCrawler, url: str) -> FetchedPage:
    """Fetch one URL using an already-open crawler/browser instance."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        result = await asyncio.wait_for(
            crawler.arun(url=url, config=_RUN_CONFIG), timeout=FETCH_TIMEOUT_SECONDS
        )
    except TimeoutError:
        return FetchedPage(
            requested_url=url, final_url=url, markdown="", fetched_at=fetched_at,
            success=False, error="timeout",
        )
    except Exception as exc:  # crawl4ai/Playwright can raise a wide variety of errors
        return FetchedPage(
            requested_url=url, final_url=url, markdown="", fetched_at=fetched_at,
            success=False, error=str(exc),
        )

    if not result.success:
        return FetchedPage(
            requested_url=url, final_url=result.url or url, markdown="", fetched_at=fetched_at,
            success=False, error=f"status_code={result.status_code}",
        )

    return FetchedPage(
        requested_url=url,
        final_url=result.url,
        markdown=str(result.markdown),
        fetched_at=fetched_at,
        success=True,
    )


async def fetch_single_page(url: str) -> FetchedPage:
    """Fetch one URL with a fresh headless browser. Used by the fetch_website
    agent tool for one-off live lookups during a chat turn.
    """
    async with AsyncWebCrawler(config=_BROWSER_CONFIG) as crawler:
        return await _run_single_fetch(crawler, url)


async def crawl_seed_pages(seed_paths: list[str] | None = None) -> list[FetchedPage]:
    """Fetch every seed URL with one shared browser instance, cache each
    page's markdown to disk, and drop exact-duplicate content (e.g. tabbed
    pages that turn out to render the same content regardless of tabKey -
    see config/seed_urls.py's NOTE on the merchant/investment banking pages).
    """
    paths = seed_paths if seed_paths is not None else CRAWL_SEED_URLS
    CRAWLED_PAGES_DIR.mkdir(parents=True, exist_ok=True)

    pages: list[FetchedPage] = []
    seen_content_hashes: dict[str, str] = {}  # content hash -> first URL that had it

    async with AsyncWebCrawler(config=_BROWSER_CONFIG) as crawler:
        for path in paths:
            url = f"{BASE_URL}{path}"
            page = await _run_single_fetch(crawler, url)

            if not page.success:
                print(f"[web_crawler] FAILED {url}: {page.error}")
                continue

            content_hash = hashlib.sha256(page.markdown.strip().encode("utf-8")).hexdigest()
            if content_hash in seen_content_hashes:
                print(f"[web_crawler] SKIP duplicate content: {url} (same as {seen_content_hashes[content_hash]})")
                continue
            seen_content_hashes[content_hash] = url

            cache_path = CRAWLED_PAGES_DIR / f"{_slugify_url_for_filename(path)}.md"
            cache_path.write_text(page.markdown, encoding="utf-8")

            pages.append(page)
            print(f"[web_crawler] OK {url} ({len(page.markdown)} chars)")

    return pages
