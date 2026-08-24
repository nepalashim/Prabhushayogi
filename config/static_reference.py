"""Static reference data used by the system prompt and the judge's
safe-fallback response: account-specific query-tool pages (Phase 1 has no
auth/PII handling, so these are always a redirect target, never answered
directly) and real Prabhu Capital contact details.
"""

from __future__ import annotations

from typing import TypedDict


class QueryPage(TypedDict):
    label: str
    url: str


# Account-specific self-service tools. Any account-specific question (BOID,
# allotment, dividend, portfolio, etc.) must be redirected to one of these
# instead of answered directly - see llm/prompts.py's system prompt.
QUERY_TOOL_PAGES: list[QueryPage] = [
    {"label": "Share Allotment", "url": "https://www.prabhucapital.com/ipo-allotment"},
    {"label": "Right Share Eligibility Check", "url": "https://www.prabhucapital.com/right-share"},
    {"label": "Demat Rejection List", "url": "https://www.prabhucapital.com/demat-rejection"},
    {"label": "Dividend Rejection List", "url": "https://www.prabhucapital.com/ips-rejection"},
    {
        "label": "Non-Dematerialized Certificates",
        "url": "https://www.prabhucapital.com/non-demat-certificates",
    },
    {"label": "Unclaimed Dividends", "url": "https://www.prabhucapital.com/unclaimed-dividends"},
    {"label": "Bonus Share Tax", "url": "https://www.prabhucapital.com/bonus-share-tax"},
    {"label": "AMC Checker", "url": "https://www.prabhucapital.com/amc-checker"},
    {"label": "BOID Search", "url": "https://www.prabhucapital.com/boid-search"},
]

CONTACTS: dict[str, str] = {
    "hotline": "015970200",
    "email": "info@prabhucapital.com",
    "demat_support_viber": "9840076100",
    "pms_contact": "9840076200",
    "sip_support_whatsapp": "9861989800",
    "address": "Kamaladi, Kathmandu, Nepal",
    "information_officer_name": "Roshan KC",
    "information_officer_ext": "416",
    "information_officer_email": "roshan.kc@prabhucapital.com",
    "grievances_officer_name": "Bijay Moktan Tamang",
    "grievances_officer_ext": "418",
    "grievances_officer_email": "bijaya.tamang@prabhucapital.com",
}
