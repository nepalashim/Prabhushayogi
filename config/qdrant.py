"""Qdrant client factory — the single place a QdrantClient is constructed."""

from __future__ import annotations

from functools import lru_cache

from qdrant_client import QdrantClient

from config.settings import settings

COLLECTION_NAME = settings.QDRANT_COLLECTION_NAME


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)
