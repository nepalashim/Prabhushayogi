"""SQLite schema + connection setup for conversation/verdict logging."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from config.settings import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS verdicts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT NOT NULL,
    session_id          TEXT NOT NULL,
    user_query          TEXT NOT NULL,
    rewritten_query     TEXT,
    retrieved_chunk_ids TEXT,
    tools_used          TEXT,
    answer              TEXT NOT NULL,
    judge_json          TEXT,
    final_action        TEXT NOT NULL,
    latency_ms          INTEGER
);

CREATE TABLE IF NOT EXISTS human_review (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    verdict_id          INTEGER NOT NULL REFERENCES verdicts(id),
    reviewer            TEXT NOT NULL,
    reviewer_verdict    TEXT NOT NULL,
    notes               TEXT,
    reviewed_at         TEXT NOT NULL
);
"""


def _db_path() -> Path:
    path = Path(settings.SQLITE_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def init_db() -> None:
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.executescript(_SCHEMA)
        await conn.commit()


async def get_connection() -> aiosqlite.Connection:
    """A fresh connection with the standard pragmas set. Caller closes it
    (use `async with` or a try/finally at the call site) - single-writer
    SQLite is fine at Phase-1 scale with a single uvicorn worker (see the
    implementation plan's risk notes for the multi-worker caveat).
    """
    conn = await aiosqlite.connect(_db_path())
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA busy_timeout=5000;")
    return conn
