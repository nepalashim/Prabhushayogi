"""GET /api/health - device/model/index_meta status.

Surfaces the embed-model/index coupling guard (indexing/index_meta.py) at the
app layer: a mismatched index reports HTTP 503 here, and the chat endpoint
(app/routes/chat.py) refuses to serve for the same reason, rather than
silently returning wrong retrieval results.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config.settings import resolve_device, settings
from indexing.index_meta import Compatibility, check_compatibility
from ml_models.embedder import embedding_dimension

router = APIRouter()

OK_COMPATIBILITY_STATES = {Compatibility.MATCH, Compatibility.NO_INDEX_YET}


@router.get("/health")
async def health() -> JSONResponse:
    embed_model = settings.resolved_embed_model()
    compatibility = check_compatibility(embed_model, embedding_dimension())
    ok = compatibility in OK_COMPATIBILITY_STATES

    body = {
        "status": "ok" if ok else "index_mismatch",
        "device": resolve_device(),
        "embed_model": embed_model,
        "generator_model": settings.GENERATOR_MODEL,
        "judge_model": settings.JUDGE_MODEL,
        "index_compatibility": compatibility.value,
    }
    return JSONResponse(content=body, status_code=200 if ok else 503)
