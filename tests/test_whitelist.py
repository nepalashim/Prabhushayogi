"""Unit tests for the fetch_website domain whitelist (SSRF guardrail)."""

from __future__ import annotations

import pytest

from config.whitelist import is_allowed_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.prabhucapital.com/",
        "https://prabhucapital.com/calendar",
        "http://www.prabhucapital.com/media?tabKey=issue-notice",
    ],
)
def test_allows_real_site_urls(url: str) -> None:
    assert is_allowed_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/prabhucapital.com",  # substring in path, not the host
        "https://prabhucapital.com.evil.com/",  # suffix-looking prefix trick
        "https://ipoapply.prabhucapital.com/",  # excluded interactive portal
        "https://mutualfund.prabhucapital.com/",  # excluded interactive portal
        "https://notprabhucapital.com/",  # similar but different domain
        "ftp://www.prabhucapital.com/",  # disallowed scheme
        "https://127.0.0.1/",  # IP literal, not the real domain
        "not a url at all",
    ],
)
def test_rejects_unsafe_urls(url: str) -> None:
    assert is_allowed_url(url) is False
