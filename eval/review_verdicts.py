"""Human calibration CLI (spec Section 5A rule 6).

Usage:
    python -m eval.review_verdicts --n 20 --reviewer <name>

Samples N logged verdicts, shows the query/answer/judge verdict, prompts
[a]gree/[d]isagree/[s]kip, and records the result in the human_review table.
Ends with an agreement-rate summary; if disagreement exceeds 10%, prints a
reminder to switch JUDGE_MODEL to the Groq fallback slot in .env (per the
spec, a config-only change).
"""

from __future__ import annotations

import argparse
import asyncio
import random
from datetime import datetime, timezone

from query_logging.db import get_connection, init_db

DISAGREEMENT_THRESHOLD = 0.10


async def _fetch_sample(n: int) -> list[tuple]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT id, user_query, answer, judge_json, final_action FROM verdicts "
            "WHERE judge_json IS NOT NULL ORDER BY id DESC LIMIT 500"
        )
        rows = await cursor.fetchall()
    finally:
        await conn.close()

    if len(rows) <= n:
        return rows
    return random.sample(rows, n)


async def _record_review(verdict_id: int, reviewer: str, reviewer_verdict: str) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT INTO human_review (verdict_id, reviewer, reviewer_verdict, notes, reviewed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (verdict_id, reviewer, reviewer_verdict, None, datetime.now(timezone.utc).isoformat()),
        )
        await conn.commit()
    finally:
        await conn.close()


async def run_review(n: int, reviewer: str) -> None:
    await init_db()
    sample = await _fetch_sample(n)

    if not sample:
        print("No logged verdicts with a judge_json yet - run some chat turns first.")
        return

    agree = 0
    disagree = 0
    skipped = 0

    for verdict_id, user_query, answer, judge_json, final_action in sample:
        print("\n" + "=" * 70)
        print(f"Query:  {user_query}")
        print(f"Answer: {answer}")
        print(f"Judge:  {judge_json}")
        print(f"Action: {final_action}")
        choice = input("Does the judge's verdict look correct? [a]gree / [d]isagree / [s]kip: ").strip().lower()

        if choice == "a":
            agree += 1
            await _record_review(verdict_id, reviewer, "AGREE")
        elif choice == "d":
            disagree += 1
            await _record_review(verdict_id, reviewer, "DISAGREE")
        else:
            skipped += 1

    reviewed = agree + disagree
    print("\n" + "=" * 70)
    print(f"Reviewed: {reviewed} (skipped {skipped})")
    if reviewed == 0:
        return

    disagreement_rate = disagree / reviewed
    print(f"Agreement rate: {agree}/{reviewed} ({(1 - disagreement_rate):.0%})")

    if disagreement_rate > DISAGREEMENT_THRESHOLD:
        print(
            f"\nDisagreement rate ({disagreement_rate:.0%}) exceeds the {DISAGREEMENT_THRESHOLD:.0%} threshold. "
            "Per spec Section 5A rule 6: switch JUDGE_MODEL in .env to the Groq fallback slot "
            "(e.g. groq/llama-3.3-70b-versatile) for cross-model judging - a config-only change."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Human calibration review of logged judge verdicts")
    parser.add_argument("--n", type=int, default=20, help="Number of verdicts to sample (default 20)")
    parser.add_argument("--reviewer", type=str, required=True, help="Your name/identifier")
    args = parser.parse_args()
    asyncio.run(run_review(args.n, args.reviewer))


if __name__ == "__main__":
    main()
