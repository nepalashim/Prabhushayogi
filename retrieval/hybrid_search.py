"""Hybrid (dense + keyword) retrieval with Reciprocal Rank Fusion, shared by
the search_documents agent tool and the golden-set eval script.

Qdrant's payload full-text index is a FILTER (MatchText), not a
relevance-ranked query by itself - the keyword side below fetches a filtered
candidate set that way, then ranks it client-side with a lightweight
IDF-weighted term-match score (see _keyword_search). This is a deliberate
Phase-1 simplification, not full BM25 (no length normalization, no proper
corpus statistics caching - each search recomputes term document frequencies
with a few extra Qdrant count() calls, fine at this corpus size); a natural
upgrade path later is Qdrant's native sparse-vector BM25 + built-in RRF
fusion query if the corpus grows enough for the difference to matter.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from qdrant_client import models

from config.qdrant import COLLECTION_NAME, get_qdrant_client
from indexing.qdrant_loader import VECTOR_NAME
from ml_models.embedder import embed_query
from retrieval.rrf import reciprocal_rank_fusion

DENSE_CANDIDATES = 20
KEYWORD_CANDIDATES = 50

# A compact, hand-curated stopword list (not a full NLTK corpus - avoids an
# extra download for a Phase-1 keyword pass). Without this, common words like
# "what"/"are"/"the" get OR-matched against nearly every chunk in the corpus,
# turning the "keyword candidate set" into close to the whole collection and
# swamping the RRF fusion with noise - confirmed empirically during Stage 3
# testing (every top result was navigation boilerplate until this was added).
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "what", "which", "who", "whom", "this", "that", "these", "those",
        "and", "or", "but", "if", "then", "so", "of", "at", "by", "for",
        "with", "about", "against", "between", "into", "through", "during",
        "to", "from", "in", "on", "off", "over", "under", "again", "further",
        "how", "when", "where", "why", "all", "any", "both", "each", "few",
        "more", "most", "other", "some", "such", "no", "nor", "not", "only",
        "own", "same", "than", "too", "very", "can", "will", "just", "should",
        "now", "do", "does", "did", "doing", "have", "has", "had", "having",
        "i", "me", "my", "we", "our", "you", "your", "it", "its", "they", "their",
    }
)
_WORD_RE = re.compile(r"[a-z0-9]+")


def _extract_keyword_terms(query: str) -> list[str]:
    words = _WORD_RE.findall(query.lower())
    return [word for word in words if word not in _STOPWORDS and len(word) > 1]


@dataclass
class RankedChunk:
    chunk_id: str
    text: str
    source: str
    url_or_filename: str
    section_title: str | None
    doc_type: str
    score: float


def _dense_search(query: str, limit: int) -> list[tuple[str, dict]]:
    """Returns [(point_id, payload), ...] ranked by dense cosine similarity."""
    client = get_qdrant_client()
    query_vector = embed_query(query)
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        using=VECTOR_NAME,
        limit=limit,
        with_payload=True,
    )
    return [(str(point.id), point.payload) for point in results.points]


def _term_document_frequency(client: object, term: str) -> int:
    return client.count(
        collection_name=COLLECTION_NAME,
        count_filter=models.Filter(must=[models.FieldCondition(key="text", match=models.MatchText(text=term))]),
        exact=True,
    ).count


def _keyword_search(query: str, limit: int) -> list[tuple[str, dict]]:
    """Filtered-candidate-set + client-side IDF-weighted term-match ranking.

    A term that appears in nearly every chunk (e.g. "demat" on a demat-services
    site) should barely move the ranking; a term that appears in only a few
    chunks (e.g. "renewal") should count for much more. Confirmed necessary
    empirically: without this weighting, a chunk ranked #1 by dense search
    dropped to rank 16/49 in the keyword list purely because other, less
    relevant chunks repeated the common term "demat" more times - dragging
    the correct answer out of the fused top results entirely.
    """
    client = get_qdrant_client()
    terms = _extract_keyword_terms(query)
    if not terms:
        return []

    total_chunks = client.count(collection_name=COLLECTION_NAME, exact=True).count
    if total_chunks == 0:
        return []

    term_weights = {
        term: math.log((total_chunks + 1) / (_term_document_frequency(client, term) + 1)) + 1.0 for term in terms
    }

    candidates, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=models.Filter(
            should=[models.FieldCondition(key="text", match=models.MatchText(text=term)) for term in terms]
        ),
        limit=limit,
        with_payload=True,
    )

    def weighted_score(payload: dict) -> float:
        text_lower = (payload.get("text") or "").lower()
        return sum(text_lower.count(term) * term_weights[term] for term in terms)

    scored = [(str(point.id), point.payload, weighted_score(point.payload)) for point in candidates]
    scored.sort(key=lambda triple: triple[2], reverse=True)
    return [(point_id, payload) for point_id, payload, _score in scored]


def hybrid_search(query: str, top_k: int = 20) -> list[RankedChunk]:
    """Dense + keyword retrieve, fused with RRF, returning the top_k chunks."""
    dense_results = _dense_search(query, DENSE_CANDIDATES)
    keyword_results = _keyword_search(query, KEYWORD_CANDIDATES)

    payload_by_id: dict[str, dict] = dict(dense_results)
    payload_by_id.update(keyword_results)

    dense_ids = [point_id for point_id, _payload in dense_results]
    keyword_ids = [point_id for point_id, _payload in keyword_results]
    fused = reciprocal_rank_fusion([dense_ids, keyword_ids])

    ranked_chunks = []
    for point_id, score in fused[:top_k]:
        payload = payload_by_id[point_id]
        ranked_chunks.append(
            RankedChunk(
                chunk_id=point_id,
                text=payload.get("text", ""),
                source=payload.get("source", ""),
                url_or_filename=payload.get("url_or_filename", ""),
                section_title=payload.get("section_title"),
                doc_type=payload.get("doc_type", ""),
                score=score,
            )
        )
    return ranked_chunks
