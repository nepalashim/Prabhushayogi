"""The online query pipeline: PrabhuAgentWorkflow ties together query
rewriting, the tool-calling agent loop, and the judge gate.

Usage: PrabhuAgentWorkflow().run(query=..., session_id=..., chat_history=[...])
`chat_history` is a list of {"role": "user"|"assistant", "content": str}
dicts, oldest first (empty on a session's first turn).

Streaming/judge-gate design (see the implementation plan): the generator's
answer is produced fully server-side before the judge ever sees it, and the
judge runs BEFORE the workflow's StopEvent - nothing reaches
app/routes/chat.py's SSE translation layer until it has already passed (or
failed) the faithfulness check. StatusEvents streamed via
ctx.write_event_to_stream() during the run never carry unverified content -
only short progress labels.

Two things below were verified empirically against the live Gemini API while
building this, not assumed:
- Tool-call round-trip: a CLEAN, minimal OpenAI-style reconstruction of the
  assistant's tool-call message (role/content/tool_calls with just
  id+type+function.name+function.arguments) is sufficient - Gemini's extra
  thinking/thought-signature fields do not need to be preserved.
- Gemini 3.6-flash routinely does 2 rounds of search_documents (refining its
  query) before answering, even when the first result already contains the
  answer - this is deliberate thoroughness, not a bug, hence
  MAX_TOOL_ITERATIONS=4 in config (verified converging within 3 rounds).
"""

from __future__ import annotations

import json
import time

from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step

from agent.events import AnswerDraftedEvent, QueryReadyEvent, StatusEvent
from agent.query_rewrite import rewrite_query
from agent.tools import TOOL_SCHEMAS, ToolResult, fetch_website, list_services, search_documents
from config.settings import settings
from judge.fallback_response import build_fallback_response
from judge.judge import evaluate
from llm.litellm_client import acompletion_with_fallback
from llm.prompts import STATIC_REFERENCE_CONTEXT, SYSTEM_PROMPT
from query_logging.logger import log_smalltalk, log_verdict

_FACTUAL_TOOLS = {"search_documents", "fetch_website"}
_TOOL_STATUS_MESSAGES = {
    "search_documents": ("retrieving", "Searching documents..."),
    "fetch_website": ("fetching", "Checking prabhucapital.com..."),
}


def _clean_tool_call_message(content: str | None, tool_calls: list) -> dict:
    """A minimal OpenAI-style reconstruction of an assistant tool-call
    message - verified sufficient for the Gemini round-trip (see module
    docstring); provider-specific extra fields do not need to be preserved.
    """
    return {
        "role": "assistant",
        "content": content,
        "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in tool_calls
        ],
    }


async def _dispatch_tool_call(ctx: Context, name: str, args: dict) -> ToolResult:
    if name in _TOOL_STATUS_MESSAGES:
        stage, message = _TOOL_STATUS_MESSAGES[name]
        ctx.write_event_to_stream(StatusEvent(stage=stage, message=message))

    if name == "search_documents":
        return await search_documents(**args)
    if name == "fetch_website":
        return await fetch_website(**args)
    if name == "list_services":
        return list_services()
    return ToolResult(content=f"Unknown tool requested: {name}", sources=[])


class PrabhuAgentWorkflow(Workflow):
    @step
    async def rewrite(self, ctx: Context, ev: StartEvent) -> QueryReadyEvent:
        query: str = ev.get("query")
        session_id: str = ev.get("session_id")
        history: list[dict[str, str]] = ev.get("chat_history", default=[]) or []

        await ctx.store.set("session_id", session_id)
        await ctx.store.set("original_query", query)
        await ctx.store.set("start_time", time.monotonic())

        if not history:
            await ctx.store.set("rewritten_query", None)
            return QueryReadyEvent(query=query, is_follow_up=False)

        ctx.write_event_to_stream(StatusEvent(stage="rewriting", message="Understanding your question..."))
        standalone_query = await rewrite_query(history, query)
        await ctx.store.set("rewritten_query", standalone_query)
        return QueryReadyEvent(query=standalone_query, is_follow_up=True)

    @step
    async def agent_loop(self, ctx: Context, ev: QueryReadyEvent) -> AnswerDraftedEvent:
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": ev.query},
        ]
        used_factual_tools = False
        tools_used: list[str] = []
        collected_sources: list[dict[str, str]] = []
        context_parts: list[str] = []
        last_message = None

        for _ in range(settings.MAX_TOOL_ITERATIONS):
            response = await acompletion_with_fallback(
                messages,
                model=settings.GENERATOR_MODEL,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.2,
            )
            message = response.choices[0].message
            last_message = message

            if not message.tool_calls:
                return AnswerDraftedEvent(
                    answer=message.content or "",
                    context="\n\n".join(context_parts),
                    sources=collected_sources,
                    used_factual_tools=used_factual_tools,
                    tools_used=tools_used,
                )

            messages.append(_clean_tool_call_message(message.content, message.tool_calls))

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments or "{}")
                tools_used.append(name)
                result = await _dispatch_tool_call(ctx, name, args)

                if name in _FACTUAL_TOOLS:
                    used_factual_tools = True
                    context_parts.append(result.content)
                    collected_sources.extend(result.sources)

                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result.content})

        # Exhausted MAX_TOOL_ITERATIONS without a final text answer.
        fallback_text = (last_message.content if last_message else None) or (
            "I wasn't able to fully answer that within the time available - please contact us directly."
        )
        return AnswerDraftedEvent(
            answer=fallback_text,
            context="\n\n".join(context_parts),
            sources=collected_sources,
            used_factual_tools=used_factual_tools,
            tools_used=tools_used,
        )

    @step
    async def judge_gate(self, ctx: Context, ev: AnswerDraftedEvent) -> StopEvent:
        session_id: str = await ctx.store.get("session_id")
        original_query: str = await ctx.store.get("original_query")
        rewritten_query: str | None = await ctx.store.get("rewritten_query")
        start_time: float = await ctx.store.get("start_time")
        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Rule 7 (scope guard): pure navigation/small-talk (no factual tool
        # was ever called this turn) skips the judge but is still logged.
        if not ev.used_factual_tools:
            await log_smalltalk(session_id=session_id, user_query=original_query, answer=ev.answer, latency_ms=latency_ms)
            return StopEvent(
                result={
                    "answer": ev.answer,
                    "sources": [],
                    "action": "skipped_smalltalk",
                    "session_id": session_id,
                }
            )

        ctx.write_event_to_stream(StatusEvent(stage="verifying", message="Verifying answer..."))
        # STATIC_REFERENCE_CONTEXT is appended so legitimate mentions of
        # contact details / redirect pages (system-prompt-instructed, not
        # tool-retrieved) aren't wrongly flagged as unsupported - see its
        # docstring in llm/prompts.py for the failure mode this fixes.
        judge_context = f"{ev.context}\n\n{STATIC_REFERENCE_CONTEXT}"
        verdict = await evaluate(judge_context, ev.answer)

        judge_json = {"supported": "YES" if verdict.supported else "NO", "unsupported_claims": verdict.unsupported_claims}
        if verdict.error:
            judge_json["error"] = verdict.error

        if verdict.supported:
            final_answer = ev.answer
            action = "answered"
            sources = ev.sources
        else:
            # Rule 4 (fail closed): never show the generated answer.
            relevant_url = ev.sources[0]["url_or_filename"] if ev.sources else None
            final_answer = build_fallback_response(relevant_url)
            action = "fallback"
            sources = []

        retrieved_chunk_ids = [s["chunk_id"] for s in ev.sources if "chunk_id" in s]
        await log_verdict(
            session_id=session_id,
            user_query=original_query,
            rewritten_query=rewritten_query,
            retrieved_chunk_ids=retrieved_chunk_ids,
            tools_used=ev.tools_used,
            # Log the ORIGINAL candidate answer the judge actually evaluated,
            # not final_answer (which is the generic fallback text on
            # rejection) - the human calibration process (eval/review_verdicts.py)
            # needs to see what was rejected to judge whether the verdict
            # itself was correct, and the fallback text is always identical
            # regardless of what triggered it, so it has no diagnostic value.
            answer=ev.answer,
            judge_json=judge_json,
            final_action=action,
            latency_ms=latency_ms,
        )

        return StopEvent(result={"answer": final_answer, "sources": sources, "action": action, "session_id": session_id})
