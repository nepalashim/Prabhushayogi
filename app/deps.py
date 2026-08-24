"""Startup-time singleton warm-up.

The embedder/reranker/qdrant client are already @lru_cache'd getters
(ml_models/embedder.py, ml_models/reranker.py, config/qdrant.py) - calling
them once here during the FastAPI lifespan just makes sure the first real
user request doesn't pay the model-loading cost.
"""

from __future__ import annotations

from config.qdrant import get_qdrant_client
from ml_models.embedder import get_embedder
from ml_models.reranker import get_reranker


def warm_up_models() -> None:
    get_embedder()
    get_reranker()
    get_qdrant_client()
