"""Reciprocal Rank Fusion - a pure function, deliberately independent of
Qdrant so it's trivially unit-testable (see tests/test_rrf.py).
"""

from __future__ import annotations

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = DEFAULT_RRF_K) -> list[tuple[str, float]]:
    """Fuse multiple ranked ID lists into one score-sorted list.

    score[id] = sum, over every list containing id, of 1 / (k + rank_in_that_list)
    (rank is 0-indexed, so a top result contributes 1/(k+0)). IDs absent from
    a given list simply don't get a contribution from that list.
    """
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, item_id in enumerate(ranked_list):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
