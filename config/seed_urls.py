"""Fixed seed list for the offline website crawl, plus short aliases the
fetch_website agent tool can resolve without the caller needing full URLs.

Every path/tabKey below was confirmed by inspecting prabhucapital.com's live
navigation menu (2026-08-22). A few are flagged NOTE below where the crawl
could not confirm distinct server-side content per tabKey purely by
inspection - indexing/run_index.py's Stage 2 crawl run verifies this
empirically (by comparing extracted text across variants) and this list
should be adjusted based on those real results.
"""

from __future__ import annotations

BASE_URL = "https://www.prabhucapital.com"

# Crawled by indexing/run_index.py. Each entry is a path (no domain) under BASE_URL.
CRAWL_SEED_URLS: list[str] = [
    "/",
    "/about-us/who-we-are?tabKey=prabhu-capital",
    "/about-us/who-we-are?tabKey=expertise",
    "/about-us/leadership?tabKey=board-of-director",
    "/about-us/leadership?tabKey=management",
    "/about-us/leadership?tabKey=committee",
    "/about-us/leadership?tabKey=previous-chairman",
    # NOTE: the service-category sub-tabs visible on this page (Depository
    # Participant, RTS/RTA, Issues and Sales Management, Underwriting) did not
    # expose distinct tabKey links when inspected - only "rts-rta" is
    # confirmed. Verify empirically whether the other categories need
    # separate tabKey guesses or JS-driven tab clicks (Crawl4AI's js_code
    # option) to reach; expand this list once confirmed.
    "/our-services/merchant-banking-services?tabKey=rts-rta",
    "/our-services/investment-banking-services?tabKey=portfolio-management-services",
    "/downloads?tabKey=dp-related-form",
    "/downloads?tabKey=issue-notice",
    "/downloads?tabKey=press-release",
    "/mutual-fund",
    "/knowledge-center",
    "/media?tabKey=issue-notice",
    "/calendar",
    "/career",
]

# Short names the fetch_website agent tool accepts in place of a full URL, so
# the LLM can say e.g. "calendar" instead of guessing a path.
PAGE_ALIASES: dict[str, str] = {
    "homepage": "/",
    "about": "/about-us/who-we-are?tabKey=prabhu-capital",
    "expertise": "/about-us/who-we-are?tabKey=expertise",
    "leadership": "/about-us/leadership?tabKey=board-of-director",
    "merchant-banking-services": "/our-services/merchant-banking-services?tabKey=rts-rta",
    "investment-banking-services": "/our-services/investment-banking-services?tabKey=portfolio-management-services",
    "downloads": "/downloads?tabKey=dp-related-form",
    "forms": "/downloads?tabKey=dp-related-form",
    "news-and-events": "/downloads?tabKey=issue-notice",
    "press-releases": "/downloads?tabKey=press-release",
    "mutual-fund": "/mutual-fund",
    "knowledge-center": "/knowledge-center",
    "media": "/media?tabKey=issue-notice",
    "calendar": "/calendar",
    "career": "/career",
}

# Human-readable titles for each crawled page, keyed by the same path used in
# CRAWL_SEED_URLS. Needed because the site's real <title> tag is identical
# and generic on every single page (confirmed: "Prabhu Capital | A Subsidiary
# of Prabhu Bank" everywhere, via crawl4ai's CrawlResult.metadata) - not
# usable to distinguish sources in the UI's citation chips.
PAGE_TITLES: dict[str, str] = {
    "/": "Prabhu Capital - Home",
    "/about-us/who-we-are?tabKey=prabhu-capital": "About Prabhu Capital",
    "/about-us/who-we-are?tabKey=expertise": "Our Expertise",
    "/about-us/leadership?tabKey=board-of-director": "Board of Directors",
    "/about-us/leadership?tabKey=management": "Management Team",
    "/about-us/leadership?tabKey=committee": "Committee",
    "/about-us/leadership?tabKey=previous-chairman": "Previous Chairman",
    "/our-services/merchant-banking-services?tabKey=rts-rta": "Merchant Banking Services",
    "/our-services/investment-banking-services?tabKey=portfolio-management-services": (
        "Investment Banking Services (PMS)"
    ),
    "/downloads?tabKey=dp-related-form": "Downloads - Forms",
    "/downloads?tabKey=issue-notice": "Downloads - News & Events",
    "/downloads?tabKey=press-release": "Downloads - Press Releases",
    "/mutual-fund": "Mutual Fund",
    "/knowledge-center": "Knowledge Center",
    "/media?tabKey=issue-notice": "Media - Notices",
    "/calendar": "Calendar",
    "/career": "Careers",
}


def get_page_title(path: str) -> str:
    """Human-readable title for a crawled page path. Falls back to a
    title-cased slug of the last path segment for any URL not explicitly
    mapped above (e.g. a page fetch_website reaches that isn't in the seed list).
    """
    if path in PAGE_TITLES:
        return PAGE_TITLES[path]
    slug = path.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
    return slug.replace("-", " ").title() if slug else "Prabhu Capital"
