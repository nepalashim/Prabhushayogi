"""Golden-set quality gate (spec Section 8).

test_retrieval_hit_rate: free, no LLM calls - checks whether the expected
source appears in search_documents' top-5 results. Always runs; pytest's own
summary line ("N passed, M failed") IS the hit-rate report.

test_judge_pass_rate: calls the full agent workflow (real LLM calls) for
every golden-set question - gated behind RUN_LLM_EVAL=1 so a normal local
`pytest` run never burns API quota by default. Run explicitly with:
    RUN_LLM_EVAL=1 pytest eval/test_golden_set.py -k judge_pass_rate
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path

import pytest

from agent.tools import search_documents
from agent.workflow import PrabhuAgentWorkflow
from config.qdrant import COLLECTION_NAME, get_qdrant_client
from indexing.index_meta import read_index_meta
from query_logging.db import init_db

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.jsonl"


def _load_golden_set() -> list[dict]:
    items = []
    with GOLDEN_SET_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


GOLDEN_SET = _load_golden_set()
# "static_reference" items are answered from the system prompt's static data,
# not retrieval by design - checking search_documents hit-rate against them
# isn't meaningful, so they're excluded from that test only.
RETRIEVAL_ITEMS = [item for item in GOLDEN_SET if item["expected_sources"] != ["static_reference"]]


def _index_available() -> bool:
    if read_index_meta() is None:
        return False
    try:
        return get_qdrant_client().collection_exists(COLLECTION_NAME)
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def _skip_if_no_index():
    if not _index_available():
        pytest.skip("No index found / Qdrant unreachable - run indexing/run_index.py first.")


@pytest.mark.asyncio
@pytest.mark.parametrize("item", RETRIEVAL_ITEMS, ids=[item["id"] for item in RETRIEVAL_ITEMS])
async def test_retrieval_hit_rate(item: dict) -> None:
    """The expected source substring should appear in the top-5 reranked results."""
    result = await search_documents(item["question"])
    urls = [source["url_or_filename"] for source in result.sources]
    hit = any(expected in url for expected in item["expected_sources"] for url in urls)
    assert hit, f"None of {item['expected_sources']} found in top-5: {urls}"


# Confirmed empirically: Gemini's free tier enforces a per-MINUTE cap (15
# req/min for gemini-3.5-flash-lite - distinct from the per-DAY cap the full
# gemini-3.6-flash model hit earlier), and each full workflow turn can make
# several LLM calls (rewrite + up to a few tool-calling rounds + judge).
# Running the golden set back-to-back with no pacing burst past that limit
# and most items failed with a fast RateLimitError instead of a genuine
# judge verdict. This delay keeps sequential items well under the cap.
LLM_EVAL_PACING_SECONDS = float(os.environ.get("LLM_EVAL_PACING_SECONDS", "20"))


@pytest.mark.asyncio
@pytest.mark.skipif(os.environ.get("RUN_LLM_EVAL") != "1", reason="Set RUN_LLM_EVAL=1 to run (uses real LLM API quota).")
@pytest.mark.parametrize("item", GOLDEN_SET, ids=[item["id"] for item in GOLDEN_SET])
async def test_judge_pass_rate(item: dict) -> None:
    """Runs the full agent workflow end to end; records the final action.
    "answered" or "skipped_smalltalk" count as a pass, "fallback" as a miss -
    pytest's summary line reports the resulting pass rate across the set.
    """
    await asyncio.sleep(LLM_EVAL_PACING_SECONDS)
    await init_db()
    handler = PrabhuAgentWorkflow(timeout=120).run(query=item["question"], session_id=str(uuid.uuid4()), chat_history=[])
    result = await handler
    print(f"\n[{item['id']}] action={result['action']}")
    assert result["action"] in ("answered", "skipped_smalltalk"), f"fell back for: {item['question']!r}"
