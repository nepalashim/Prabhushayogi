"""Unit tests for the pure Reciprocal Rank Fusion function."""

from __future__ import annotations

from retrieval.rrf import reciprocal_rank_fusion


def test_item_ranked_first_in_both_lists_wins() -> None:
    dense = ["a", "b", "c"]
    keyword = ["a", "c", "b"]
    fused = reciprocal_rank_fusion([dense, keyword])
    assert fused[0][0] == "a"


def test_item_only_in_one_list_still_included() -> None:
    dense = ["a", "b"]
    keyword = ["c"]
    fused_ids = [item_id for item_id, _ in reciprocal_rank_fusion([dense, keyword])]
    assert set(fused_ids) == {"a", "b", "c"}


def test_agreement_across_lists_beats_a_single_top_rank() -> None:
    # "b" is #2 in both lists; "a" is #1 in only one list and absent from the other.
    dense = ["a", "b"]
    keyword = ["b", "c"]
    fused = reciprocal_rank_fusion([dense, keyword])
    scores = dict(fused)
    assert scores["b"] > scores["a"]


def test_empty_lists_produce_empty_result() -> None:
    assert reciprocal_rank_fusion([[], []]) == []
