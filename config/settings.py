"""Central configuration for Prabhu Sahayogi.

Every environment-driven value used anywhere in the codebase is defined here,
loaded once from `.env`, and imported as the shared `settings` singleton.

`resolve_device()` is the single source of truth for CPU/GPU selection.
`ml_models/embedder.py` and `ml_models/reranker.py` both call it and pass the
result as `device=...` — nothing else in the codebase should call
`torch.cuda.is_available()` or hardcode `.to("cuda")`.

Provider API keys (GEMINI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY) are all
intentionally optional at this layer (not required pydantic fields):
importing `config.settings` must work in early build stages (indexing,
retrieval) before any LLM key exists, and only whichever provider the
currently-configured GENERATOR_MODEL/JUDGE_MODEL/REWRITE_MODEL actually needs
has to be present. llm/litellm_client.py validates that at the point of use.

Currently defaults to the free Gemini tier (GENERATOR_MODEL etc. all
"gemini/..."). To switch to Claude later, only .env needs to change - set
ANTHROPIC_API_KEY and change the three model slots to "anthropic/claude-..."
(see .env.example's commented-out Claude block) - no code changes required,
by design.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

DeviceName = Literal["auto", "cuda", "cpu"]
ResolvedDevice = Literal["cuda", "cpu"]

# Default local models, picked by resolved device when EMBED_MODEL is unset.
_GPU_EMBED_MODEL = "Qwen/Qwen3-Embedding-0.6B"
_CPU_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM routing (LiteLLM model slots) ---
    # Both provider keys can be set at once - only the one matching the
    # currently-active model slots below is actually required at call time.
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    # Split across two "lite" models on purpose: each has its own separate
    # free-tier daily quota bucket (confirmed: gemini-3.6-flash, the full
    # model, caps at just 20 requests/day free tier - hit during testing).
    GENERATOR_MODEL: str = "gemini/gemini-3.5-flash-lite"
    JUDGE_MODEL: str = "gemini/gemini-3.1-flash-lite"
    REWRITE_MODEL: str = "gemini/gemini-3.1-flash-lite"
    GROQ_FALLBACK_MODEL: str = "groq/llama-3.3-70b-versatile"

    # --- Local model selection + device switching ---
    EMBED_DEVICE: DeviceName = "auto"
    EMBED_MODEL: str | None = None  # None => auto-pick from resolved device, see resolved_embed_model()
    RERANK_MODEL: str = DEFAULT_RERANK_MODEL

    # --- Qdrant ---
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "prabhu_chunks"

    # --- Storage ---
    SQLITE_DB_PATH: str = "data/app.db"
    INDEX_META_PATH: str = "data/index_meta.json"

    # --- App/server ---
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"
    # Verified empirically: Gemini 3.6-flash routinely does 2 rounds of
    # search_documents (refining its query) before giving a final answer,
    # even when the first result already contains it - this is deliberate
    # thoroughness, not a bug. 4 gives one round of buffer above that.
    MAX_TOOL_ITERATIONS: int = 4

    def resolved_embed_model(self) -> str:
        """The embedding model actually used: explicit EMBED_MODEL wins, else picked by device."""
        if self.EMBED_MODEL:
            return self.EMBED_MODEL
        return _GPU_EMBED_MODEL if resolve_device(self.EMBED_DEVICE) == "cuda" else _CPU_EMBED_MODEL

    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]


def resolve_device(explicit: DeviceName | None = None) -> ResolvedDevice:
    """Resolve EMBED_DEVICE (or an explicit override) to an actual "cuda" | "cpu".

    "cpu"  -> "cpu"
    "cuda" -> "cuda" if available, else falls back to "cpu" with a warning (never raises)
    "auto" -> "cuda" if available, else "cpu"
    """
    import torch  # local import: keeps `config` importable before torch is installed

    device = explicit if explicit is not None else get_settings().EMBED_DEVICE

    if device == "cpu":
        return "cpu"
    if device == "cuda":
        if torch.cuda.is_available():
            return "cuda"
        print("[config] EMBED_DEVICE=cuda requested but no CUDA device found - falling back to cpu.")
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"  # auto


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# pydantic-settings reads .env into the Settings object but does NOT export
# those values into os.environ. LiteLLM (and its fallback= mechanism, which
# makes its own internal call to the fallback model) resolves provider API
# keys via standard env vars, so all three are mirrored into the real process
# environment here, once, at import time - this is the one place that's
# allowed to touch os.environ for these vars.
if settings.GEMINI_API_KEY:
    os.environ.setdefault("GEMINI_API_KEY", settings.GEMINI_API_KEY)
if settings.ANTHROPIC_API_KEY:
    os.environ.setdefault("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY)
if settings.GROQ_API_KEY:
    os.environ.setdefault("GROQ_API_KEY", settings.GROQ_API_KEY)
