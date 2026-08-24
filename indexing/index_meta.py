"""The embed-model/index coupling guard (spec section 3).

The embedding model and the Qdrant index are coupled: vectors from two
different models are not comparable. Both the indexing script and the
backend's startup check read this sidecar file and refuse to proceed on a
mismatch, rather than silently mixing or misreading vectors.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from config.settings import settings


@dataclass
class IndexMeta:
    embed_model: str
    embed_dim: int
    collection_name: str
    created_at: str
    chunk_count: int


class Compatibility(str, Enum):
    MATCH = "match"
    NO_INDEX_YET = "no_index_yet"
    MODEL_MISMATCH = "model_mismatch"
    DIM_MISMATCH = "dim_mismatch"


def _meta_path() -> Path:
    return Path(settings.INDEX_META_PATH)


def read_index_meta() -> IndexMeta | None:
    path = _meta_path()
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return IndexMeta(**data)


def write_index_meta(embed_model: str, embed_dim: int, collection_name: str, chunk_count: int) -> IndexMeta:
    meta = IndexMeta(
        embed_model=embed_model,
        embed_dim=embed_dim,
        collection_name=collection_name,
        created_at=datetime.now(timezone.utc).isoformat(),
        chunk_count=chunk_count,
    )
    path = _meta_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")
    return meta


def check_compatibility(current_model: str, current_dim: int) -> Compatibility:
    """Compare the currently-configured embedding model against what the
    existing index was built with.

    Dimension is checked independently of the model-name string, as a free
    extra safety net: two different model names could coincidentally produce
    the same dimension, but a dimension mismatch is unambiguous proof of
    incompatibility even if the name check were somehow bypassed.
    """
    existing = read_index_meta()
    if existing is None:
        return Compatibility.NO_INDEX_YET
    if existing.embed_dim != current_dim:
        return Compatibility.DIM_MISMATCH
    if existing.embed_model != current_model:
        return Compatibility.MODEL_MISMATCH
    return Compatibility.MATCH
