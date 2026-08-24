"""FastAPI app entrypoint: CORS, startup lifespan (DB init + model warm-up),
and route registration.

Run with: uvicorn app.main:app --reload
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import warm_up_models
from app.routes import chat, health
from config.settings import settings
from query_logging.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    warm_up_models()  # load embedder/reranker onto GPU/CPU before the first real request
    yield


app = FastAPI(title="Prabhu Sahayogi API", lifespan=lifespan)

# No compression middleware here - gzip would buffer the whole SSE response
# and defeat streaming (see the implementation plan's risk notes).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
