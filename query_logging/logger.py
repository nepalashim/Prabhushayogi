"""Conversation/verdict logging. query_logging.db handles schema and
connections; this module handles the actual log writes and reads.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from query_logging.db import get_connection


async def log_verdict(
    *,
    session_id: str,
    user_query: str,
    rewritten_query: str | None,
    retrieved_chunk_ids: list[str],
    tools_used: list[str],
    answer: str,
    judge_json: dict[str, Any] | None,
    final_action: str,
    latency_ms: int,
) -> None:
    """Logs one turn. Called for every answer that contains factual claims
    (pass or fail verdict) per spec Section 5A rule 5.
    """
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT INTO verdicts
               (timestamp, session_id, user_query, rewritten_query, retrieved_chunk_ids,
                tools_used, answer, judge_json, final_action, latency_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                session_id,
                user_query,
                rewritten_query,
                json.dumps(retrieved_chunk_ids),
                json.dumps(tools_used),
                answer,
                json.dumps(judge_json) if judge_json is not None else None,
                final_action,
                latency_ms,
            ),
        )
        await conn.commit()
    finally:
        await conn.close()


async def log_smalltalk(*, session_id: str, user_query: str, answer: str, latency_ms: int) -> None:
    """Rule 7 (scope guard): small-talk/navigation answers skip the judge
    but must still be logged.
    """
    await log_verdict(
        session_id=session_id,
        user_query=user_query,
        rewritten_query=None,
        retrieved_chunk_ids=[],
        tools_used=[],
        answer=answer,
        judge_json=None,
        final_action="skipped_smalltalk",
        latency_ms=latency_ms,
    )


async def get_recent_turns(session_id: str, limit: int = 6) -> list[dict[str, str]]:
    """Reconstructs conversation history from the verdicts table itself
    (interleaving user_query then answer per row) - no separate messages
    table needed since every turn is already logged there regardless of outcome.
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT user_query, answer FROM verdicts WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        rows = await cursor.fetchall()
    finally:
        await conn.close()

    history: list[dict[str, str]] = []
    for user_query, answer in reversed(rows):
        history.append({"role": "user", "content": user_query})
        history.append({"role": "assistant", "content": answer})
    return history
