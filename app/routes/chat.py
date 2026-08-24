"""POST /api/chat/stream - the SSE chat endpoint.

Streaming/judge-gate design: status events (from PrabhuAgentWorkflow) stream
live as the workflow runs, but the answer text is only ever sent AFTER the
workflow has fully finished - meaning after the judge has already run.
answer_chunk frames then "fake-stream" the already-vetted text for a typing
effect; nothing unverified ever reaches the client. Event sequence:
status* -> answer_chunk* -> sources -> done, or error in place of the tail.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from agent.events import StatusEvent
from agent.workflow import PrabhuAgentWorkflow
from app.schemas import ChatRequest
from config.settings import settings
from indexing.index_meta import Compatibility, check_compatibility
from ml_models.embedder import embedding_dimension
from query_logging.logger import get_recent_turns

router = APIRouter()

_OK_COMPATIBILITY_STATES = {Compatibility.MATCH, Compatibility.NO_INDEX_YET}
ANSWER_CHUNK_SIZE = 40  # characters per fake-streamed chunk, for a typing effect
ANSWER_CHUNK_DELAY_SECONDS = 0.02
SSE_KEEPALIVE_SECONDS = 15
WORKFLOW_TIMEOUT_SECONDS = 120


def _frame(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data)}


async def _stream_chat_response(session_id: str, message: str) -> AsyncIterator[dict]:
    compatibility = check_compatibility(settings.resolved_embed_model(), embedding_dimension())
    if compatibility not in _OK_COMPATIBILITY_STATES:
        yield _frame(
            "error",
            {
                "message": (
                    f"The search index is incompatible with the current embedding model "
                    f"({compatibility.value}). Re-run the indexer."
                )
            },
        )
        return

    try:
        history = await get_recent_turns(session_id)
        handler = PrabhuAgentWorkflow(timeout=WORKFLOW_TIMEOUT_SECONDS).run(
            query=message, session_id=session_id, chat_history=history
        )

        async for event in handler.stream_events():
            if isinstance(event, StatusEvent):
                yield _frame("status", {"stage": event.stage, "message": event.message})

        result = await handler
    except Exception as exc:
        # Deliberately broad: any failure here (workflow timeout, provider
        # outage, etc.) must still end the SSE stream with a clean `error`
        # frame instead of leaving the connection hanging or crashing the app.
        yield _frame("error", {"message": f"Something went wrong while answering: {exc}"})
        return

    answer: str = result["answer"]
    for start in range(0, len(answer), ANSWER_CHUNK_SIZE):
        yield _frame("answer_chunk", {"text": answer[start : start + ANSWER_CHUNK_SIZE]})
        await asyncio.sleep(ANSWER_CHUNK_DELAY_SECONDS)

    yield _frame("sources", {"sources": result["sources"]})
    yield _frame("done", {"action": result["action"], "session_id": result["session_id"]})


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> EventSourceResponse:
    return EventSourceResponse(
        _stream_chat_response(request.session_id, request.message), ping=SSE_KEEPALIVE_SECONDS
    )
