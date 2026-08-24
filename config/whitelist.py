"""Domain whitelist for the fetch_website agent tool - the SSRF guardrail.

Only prabhucapital.com (and real subdomains) may be fetched. The interactive
portal subdomains (ipoapply., mutualfund.) are deliberately excluded even
though they share the parent domain - they're login/transaction flows, not
informational content, and are referenced only via config/services_catalog.py.

is_allowed_url() is called twice by agent/tools.py::fetch_website: once on the
requested URL before fetching, and again on the final resolved URL after
fetch (Crawl4AI drives a real browser that can follow redirects), so a page
that redirects off-domain is still rejected.
"""

from __future__ import annotations

from urllib.parse import urlsplit

ALLOWED_HOST_SUFFIXES: tuple[str, ...] = ("prabhucapital.com",)

# Real subdomains of the allowed suffix above that must still be rejected -
# interactive portals, not content pages.
EXCLUDED_HOSTS: frozenset[str] = frozenset(
    {
        "ipoapply.prabhucapital.com",
        "mutualfund.prabhucapital.com",
    }
)

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def is_allowed_url(url: str) -> bool:
    """True only for http(s) URLs whose host is prabhucapital.com or a real
    subdomain of it, excluding the interactive portal subdomains above.

    Uses an exact suffix-with-dot match, never a substring check, so
    "evil.com/prabhucapital.com" or "prabhucapital.com.evil.com" are rejected.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return False

    if parts.scheme not in _ALLOWED_SCHEMES:
        return False

    host = (parts.hostname or "").lower()
    if not host:
        return False

    if host in EXCLUDED_HOSTS:
        return False

    return any(host == suffix or host.endswith(f".{suffix}") for suffix in ALLOWED_HOST_SUFFIXES)
