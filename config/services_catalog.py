"""Static service catalog for the list_services() agent tool - cheap,
zero-latency grounding for navigation questions. Every name/URL here was
confirmed against the live prabhucapital.com navigation and service pages.

NOTE: the four merchant-banking-services sub-categories (Depository
Participant, RTS/RTA, Issue Management, Underwriting) did not expose distinct
per-category URLs when inspected, so they currently all point at the same
tabKey=rts-rta page. Update the individual `url` fields here if Stage 2's
crawl turns up distinct URLs for each.
"""

from __future__ import annotations

from typing import TypedDict

_MERCHANT_BANKING_URL = "https://www.prabhucapital.com/our-services/merchant-banking-services?tabKey=rts-rta"


class ServiceEntry(TypedDict):
    name: str
    description: str
    url: str


SERVICES: list[ServiceEntry] = [
    {
        "name": "Depository Participant (Demat) Services",
        "description": (
            "Demat account opening, securities dematerialization, and settlement services. "
            "Prabhu Capital is a SEBON-licensed Depository Participant and an authorized "
            "member of CDSC."
        ),
        "url": _MERCHANT_BANKING_URL,
    },
    {
        "name": "Registrar to Shares (RTS/RTA)",
        "description": "Share registrar services for listed companies and their shareholders.",
        "url": _MERCHANT_BANKING_URL,
    },
    {
        "name": "Issue Management (IPO / Rights / Debentures)",
        "description": "Managing public share issues, rights issues, and debenture issues for companies.",
        "url": _MERCHANT_BANKING_URL,
    },
    {
        "name": "Underwriting",
        "description": "Underwriting services for public securities issues.",
        "url": _MERCHANT_BANKING_URL,
    },
    {
        "name": "Portfolio Management Services (PMS)",
        "description": "Discretionary and non-discretionary portfolio management for investors.",
        "url": "https://www.prabhucapital.com/our-services/investment-banking-services?tabKey=portfolio-management-services",
    },
    {
        "name": "Mutual Fund / SIP",
        "description": "Mutual fund schemes and Systematic Investment Plan (SIP) options.",
        "url": "https://www.prabhucapital.com/mutual-fund",
    },
]
