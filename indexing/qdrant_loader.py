"""Qdrant collection management for the offline indexing pipeline: creating
the collection (dense vector + full-text index) and upserting chunks.
"""

from __future__ import annotations

from qdrant_client import models

from config.qdrant import COLLECTION_NAME, get_qdrant_client
from indexing.chunker import Chunk
from ml_models.embedder import embed_documents, embedding_dimension

VECTOR_NAME = "dense"
TEXT_FIELD = "text"
UPSERT_BATCH_SIZE = 64


def ensure_collection(force_recreate: bool = False) -> None:
    """Create the Qdrant collection (dense vector + full-text index on chunk
    text) if it doesn't already exist, or drop and recreate it if force_recreate.
    """
    client = get_qdrant_client()
    dim = embedding_dimension()

    exists = client.collection_exists(COLLECTION_NAME)
    if exists and force_recreate:
        client.delete_collection(COLLECTION_NAME)
        exists = False

    if not exists:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={VECTOR_NAME: models.VectorParams(size=dim, distance=models.Distance.COSINE)},
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=TEXT_FIELD,
            field_schema=models.TextIndexParams(
                type=models.TextIndexType.TEXT,
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                lowercase=True,
            ),
        )


def upsert_chunks(chunks: list[Chunk]) -> None:
    """Embed and upsert `chunks` into the Qdrant collection in batches."""
    if not chunks:
        return

    client = get_qdrant_client()
    for start in range(0, len(chunks), UPSERT_BATCH_SIZE):
        batch = chunks[start : start + UPSERT_BATCH_SIZE]
        vectors = embed_documents([chunk.text for chunk in batch])
        points = [
            models.PointStruct(
                id=chunk.chunk_id,
                vector={VECTOR_NAME: vector},
                payload={
                    "text": chunk.text,
                    "source": chunk.source,
                    "url_or_filename": chunk.url_or_filename,
                    "section_title": chunk.section_title,
                    "doc_type": chunk.doc_type,
                    "crawl_or_parse_date": chunk.crawl_or_parse_date,
                    "is_table": chunk.is_table,
                },
            )
            for chunk, vector in zip(batch, vectors)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)


def collection_point_count() -> int:
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        return 0
    return client.count(COLLECTION_NAME, exact=True).count
