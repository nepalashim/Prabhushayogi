"""LLM-as-judge faithfulness gate (spec Section 5A). Implements all 7 rules:

1. Isolated call - _build_isolated_messages() builds a brand-new message list
   from scratch, never extending or referencing the generator's own messages/
   history/system prompt.
2. Deterministic + structured - temperature=0, strict JSON schema, retry once
   on parse failure.
3. Binary question only - the exact verbatim wording in llm/prompts.py.
4. Fail closed - a NO verdict or two consecutive call/parse failures are
   treated identically by callers (see agent/workflow.py's judge_gate step):
   never show the generated answer, always the safe fallback.
5. Every verdict is logged (see query_logging) - by the caller, not here;
   judge.py has no knowledge of persistence.
6. Human calibration hook - eval/review_verdicts.py, not this module.
7. Scope guard - enforced by the caller (agent/workflow.py), not here; this
   module has no idea whether it "should" run, only "given context+answer,
   verify."
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from config.settings import settings
from llm.litellm_client import acompletion_with_fallback
from llm.prompts import JUDGE_QUESTION, JUDGE_SYSTEM_PROMPT


@dataclass
class JudgeVerdict:
    supported: bool
    unsupported_claims: list[str]
    raw_response: str | None  # the raw text returned, kept for logging/debugging
    error: str | None = None  # set when a parse/call failure forced fail-closed


def _build_isolated_messages(context: str, answer: str, *, strict_retry: bool = False) -> list[dict[str, str]]:
    question = JUDGE_QUESTION
    if strict_retry:
        question += " Respond with ONLY the JSON object - no markdown fences, no other text."
    return [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nANSWER:\n{answer}\n\n{question}"},
    ]


def _parse_verdict(raw: str | None) -> tuple[bool, list[str]] | None:
    """Returns (supported, unsupported_claims), or None if `raw` doesn't
    parse into the expected {"supported": "YES"|"NO", "unsupported_claims": [...]} shape.
    """
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    supported_raw = data.get("supported")
    if supported_raw not in ("YES", "NO"):
        return None
    claims = data.get("unsupported_claims")
    if not isinstance(claims, list):
        return None
    return supported_raw == "YES", [str(claim) for claim in claims]


async def _call_judge_once(context: str, answer: str, *, strict_retry: bool = False) -> str | None:
    """One isolated judge API call. Returns the raw response text, or None on
    any call-level error (network, auth, provider outage, etc.).
    """
    try:
        response = await acompletion_with_fallback(
            _build_isolated_messages(context, answer, strict_retry=strict_retry),
            model=settings.JUDGE_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception:
        return None


async def evaluate(context: str, answer: str) -> JudgeVerdict:
    """Rules 2 + 4: deterministic, strict JSON, retry once on parse failure,
    then fail closed (supported=False) on a second failure.
    """
    raw = await _call_judge_once(context, answer)
    parsed = _parse_verdict(raw)

    if parsed is None:
        raw = await _call_judge_once(context, answer, strict_retry=True)
        parsed = _parse_verdict(raw)

    if parsed is None:
        return JudgeVerdict(supported=False, unsupported_claims=[], raw_response=raw, error="judge_parse_failed")

    supported, unsupported_claims = parsed
    return JudgeVerdict(supported=supported, unsupported_claims=unsupported_claims, raw_response=raw)
