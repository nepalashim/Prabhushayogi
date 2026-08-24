"""Device-aware cross-encoder reranker wrapper, used at query time only
(the offline indexing pipeline never reranks - there's nothing to rank yet).
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import CrossEncoder

from config.settings import resolve_device, settings


@lru_cache
def get_reranker() -> CrossEncoder:
    """The shared reranker model, loaded once per process onto resolve_device()."""
    model_name = settings.RERANK_MODEL
    device = resolve_device()
    print(f"[ml_models.reranker] loading '{model_name}' on device='{device}'")
    return CrossEncoder(model_name, device=device)


def rerank(query: str, candidates: list[str], top_n: int) -> list[tuple[int, float]]:
    """Score `query` against each of `candidates` and return the top_n as
    (original_index, score) pairs, highest score first.
    """
    if not candidates:
        return []
    model = get_reranker()
    pairs = [(query, candidate) for candidate in candidates]
    scores = model.predict(pairs)
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    return [(index, float(score)) for index, score in ranked[:top_n]]
