"""Device-aware sentence-embedding wrapper, shared by indexing and retrieval.

Loading is lazy and cached: importing this module must stay cheap (no model
download/GPU allocation at import time), and both the indexer and the FastAPI
app should end up sharing exactly one loaded model per process.

Document vs. query embedding is NOT symmetric for instruction-tuned models
like Qwen3-Embedding: its sentence-transformers config defines a "query"
prompt (an instruction prefix) that must be applied at retrieval time for
good ranking, but is never applied automatically (default_prompt_name is
None) - confirmed empirically: without it, retrieval was dominated by
navigation boilerplate over the actually-relevant chunks. embed_documents()
and embed_query() are therefore separate functions, not aliases of each
other; each looks up the right prompt name if the loaded model defines one,
and falls back to no prompt for models that don't (e.g. bge-small-en-v1.5 on
CPU), so this works unchanged across the GPU/CPU model switch.
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from config.settings import resolve_device, settings


@lru_cache
def get_embedder() -> SentenceTransformer:
    """The shared embedding model, loaded once per process onto resolve_device()."""
    model_name = settings.resolved_embed_model()
    device = resolve_device()
    print(f"[ml_models.embedder] loading '{model_name}' on device='{device}'")
    return SentenceTransformer(model_name, device=device)


def _prompt_name_if_defined(name: str) -> str | None:
    model = get_embedder()
    return name if name in model.prompts else None


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a batch of chunk texts for indexing. Returns one vector per input, in order."""
    if not texts:
        return []
    model = get_embedder()
    vectors = model.encode(
        texts, prompt_name=_prompt_name_if_defined("document"), convert_to_numpy=True, show_progress_bar=False
    )
    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single query for retrieval, applying the model's "query"
    instruction prompt when it defines one (e.g. Qwen3-Embedding) - this is
    NOT the same as embed_documents([query])[0] for such models.
    """
    model = get_embedder()
    vector = model.encode(
        query, prompt_name=_prompt_name_if_defined("query"), convert_to_numpy=True, show_progress_bar=False
    )
    return vector.tolist()


def embedding_dimension() -> int:
    """The vector size of the currently loaded embedding model."""
    dim = get_embedder().get_embedding_dimension()
    if dim is None:
        raise RuntimeError("Loaded embedding model did not report a dimension.")
    return dim
