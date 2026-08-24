"""Safe-fallback response builder (spec Section 5A rule 4): what the user
sees whenever the judge rejects an answer (or fails twice).
"""

from __future__ import annotations

from config.static_reference import CONTACTS

FALLBACK_MESSAGE = (
    "I'm not able to confirm that information from what I have available right now. "
    "Please reach out to Prabhu Capital directly so we can get you an accurate answer:\n\n"
    f"- Support Hotline: {CONTACTS['hotline']}\n"
    f"- Email: {CONTACTS['email']}\n"
    f"- Information Officer: {CONTACTS['information_officer_name']} "
    f"(ext {CONTACTS['information_officer_ext']}, {CONTACTS['information_officer_email']})"
)


def build_fallback_response(relevant_url: str | None = None) -> str:
    """The safe fallback text shown when the judge rejects an answer.
    Optionally appends a relevant website link if one is known from context.
    """
    if relevant_url:
        return f"{FALLBACK_MESSAGE}\n\nYou may also find relevant information here: {relevant_url}"
    return FALLBACK_MESSAGE
