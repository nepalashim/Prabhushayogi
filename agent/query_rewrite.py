"""Follow-up-turn query rewriting: turns "how about PMS instead?" into a
standalone question using the conversation history. Skipped entirely on the
first turn of a session (nothing to resolve pronouns/references against).
"""

from __future__ import annotations

from llm.litellm_client import acompletion_with_fallback
from llm.prompts import QUERY_REWRITE_PROMPT

MAX_HISTORY_TURNS_FOR_REWRITE = 6


def _format_history(history: list[dict[str, str]]) -> str:
    lines = []
    for turn in history[-MAX_HISTORY_TURNS_FOR_REWRITE:]:
        role = "User" if turn["role"] == "user" else "Assistant"
        lines.append(f"{role}: {turn['content']}")
    return "\n".join(lines)


async def rewrite_query(history: list[dict[str, str]], message: str) -> str:
    """Rewrite `message` into a standalone question given `history`.

    `history` is a list of {"role": "user"|"assistant", "content": str}
    dicts, oldest first. Callers should skip calling this entirely on the
    first turn of a session (history == []) - not just for cost, but because
    there is nothing to resolve.
    """
    from config.settings import settings

    prompt = QUERY_REWRITE_PROMPT.format(history=_format_history(history), message=message)
    response = await acompletion_with_fallback(
        [{"role": "user", "content": prompt}],
        model=settings.REWRITE_MODEL,
        temperature=0,
    )
    rewritten = response.choices[0].message.content.strip()
    return rewritten or message  # never return an empty rewrite
