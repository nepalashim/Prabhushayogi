"""The three agent tools (spec Section 2) plus their OpenAI-style schemas for
LiteLLM's tools= parameter. Hand-written schemas, not auto-derived from the
function signatures, so what the LLM actually sees exactly matches what's in
this file - no framework layer in between, reasonable with only 3 tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.seed_urls import BASE_URL, PAGE_ALIASES, get_page_title
from config.services_catalog import SERVICES
from config.whitelist import is_allowed_url
from indexing.web_crawler import fetch_single_page
from ml_models.reranker import rerank
from retrieval.hybrid_search import hybrid_search

SEARCH_TOP_K_CANDIDATES = 20
SEARCH_TOP_N_RESULTS = 5
FETCH_CONTENT_CHAR_BUDGET = 8000  # keep a single tool result within a reasonable context budget


@dataclass
class ToolResult:
    """A tool's output. `sources` always carries the chunk/page-level source
    metadata the generator is required to cite per source alongside its claims.
    """

    content: str
    sources: list[dict[str, str]]


async def search_documents(query: str) -> ToolResult:
    """Hybrid search (dense + keyword, RRF-fused) over the indexed PDF corpus
    and crawled website pages, reranked to the most relevant few.
    """
    candidates = hybrid_search(query, top_k=SEARCH_TOP_K_CANDIDATES)
    if not candidates:
        return ToolResult(content="No indexed content matched this query.", sources=[])

    texts = [chunk.text for chunk in candidates]
    top = rerank(query, texts, top_n=SEARCH_TOP_N_RESULTS)

    lines: list[str] = []
    sources: list[dict[str, str]] = []
    for idx, _score in top:
        chunk = candidates[idx]
        # Deliberately NOT bracket-style ("[Source: ...]") - the generator
        # was directly mimicking that exact visual pattern as inline
        # citations in its answers, which looked cluttered in the UI.
        # Sources are already shown to the user separately as chips
        # (see SourceChips.tsx), so the model doesn't need to echo them.
        lines.append(f'From "{chunk.source}":\n{chunk.text}')
        sources.append(
            {
                "title": chunk.source,
                "url_or_filename": chunk.url_or_filename,
                "doc_type": chunk.doc_type,
                "chunk_id": chunk.chunk_id,
            }
        )

    return ToolResult(content="\n\n---\n\n".join(lines), sources=sources)


async def fetch_website(url_or_page: str) -> ToolResult:
    """Live-fetch a whitelisted prabhucapital.com page for fresh information
    not yet in the offline index (news, notices, calendar, etc.).
    """
    if url_or_page.startswith("http"):
        target_url = url_or_page
    else:
        alias = url_or_page.strip().lower()
        if alias not in PAGE_ALIASES:
            return ToolResult(
                content=f"'{url_or_page}' is not a recognized page. Valid pages: {', '.join(sorted(PAGE_ALIASES))}",
                sources=[],
            )
        target_url = f"{BASE_URL}{PAGE_ALIASES[alias]}"

    if not is_allowed_url(target_url):
        return ToolResult(content=f"'{target_url}' is not an allowed page to fetch.", sources=[])

    page = await fetch_single_page(target_url)

    if not page.success:
        return ToolResult(content=f"Could not fetch '{target_url}': {page.error}", sources=[])

    # Re-validate the FINAL resolved URL too - Crawl4AI drives a real browser
    # that can follow redirects off-domain (see config/whitelist.py docstring).
    if not is_allowed_url(page.final_url):
        return ToolResult(content=f"'{target_url}' redirected off-domain and was rejected.", sources=[])

    title = get_page_title(page.final_url.replace(BASE_URL, "") or "/")
    return ToolResult(
        content=page.markdown[:FETCH_CONTENT_CHAR_BUDGET],
        sources=[{"title": title, "url_or_filename": page.final_url, "doc_type": "webpage"}],
    )


def list_services() -> ToolResult:
    """Cheap, zero-latency static service catalog - no I/O, synchronous."""
    # No inline URL here on purpose - see search_documents' note on why (the
    # generator would otherwise echo it back as inline citation clutter);
    # sources are already carried separately below for the UI's chips.
    lines = [f"{svc['name']}: {svc['description']}" for svc in SERVICES]
    sources = [{"title": svc["name"], "url_or_filename": svc["url"], "doc_type": "webpage"} for svc in SERVICES]
    return ToolResult(content="\n".join(lines), sources=sources)


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Semantic + keyword hybrid search over indexed PDF documents and crawled "
                "website pages. Use for static policy, fee, procedure, or 'what is / how do I' "
                "questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search query."}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_website",
            "description": (
                "Live-fetch a whitelisted prabhucapital.com page for fresh information not yet "
                "in the offline index (latest news/notices, current NAV, calendar, new registrar "
                "announcements). Pass a short page name, e.g. one of: "
                + ", ".join(sorted(PAGE_ALIASES))
                + " - or a full https://www.prabhucapital.com/... URL. Do not invent other URLs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url_or_page": {
                        "type": "string",
                        "description": "A page name from the list above, or a full prabhucapital.com URL.",
                    }
                },
                "required": ["url_or_page"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_services",
            "description": (
                "Returns the canonical Prabhu Capital service catalog (names, descriptions, "
                "URLs). Use for simple navigation / 'what services do you offer' questions."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
