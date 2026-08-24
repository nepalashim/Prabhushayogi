"""Workflow event types for PrabhuAgentWorkflow.

StatusEvent is also what app/routes/chat.py translates directly into SSE
`status` frames while the workflow runs - it is only ever sent BEFORE any
generated answer text, never carries unverified content, and its presence in
the stream is exactly how the "judge runs before the client sees anything"
design (see the implementation plan) stays honest end-to-end.
"""

from __future__ import annotations

from llama_index.core.workflow import Event


class StatusEvent(Event):
    """A progress update streamed to the client while the workflow runs."""

    stage: str  # "rewriting" | "retrieving" | "fetching" | "verifying"
    message: str


class QueryReadyEvent(Event):
    """The standalone query (rewritten if this was a follow-up turn) the
    agent loop should act on.
    """

    query: str
    is_follow_up: bool


class AnswerDraftedEvent(Event):
    """The generator's finished answer, plus what it used to produce it -
    ready for the judge gate (or the small-talk skip).
    """

    answer: str
    context: str  # concatenated tool outputs the answer was grounded in
    sources: list[dict[str, str]]
    used_factual_tools: bool
    tools_used: list[str]  # names of every tool called this turn, for the verdict log
