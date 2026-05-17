"""
Template: router_factory.py

Core factory that generates 5 standardized HTTP endpoints for any Agent.
Copy into your project (e.g. src/api/router_factory.py).

Usage:
    from agents import Agent
    from .router_factory import create_agent_router

    my_agent = Agent(name="Order Bot", instructions="...")
    router = create_agent_router(my_agent, prefix="/orders", agent_name="Order Bot")
    app.include_router(router)
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

from agents import Agent, ItemHelpers, Runner
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai.types.responses import ResponseTextDeltaEvent

from .request_models import AgentInfo, AgentRequest, AgentResponse, SessionMessagesResponse
from .session_utils import (
    clear_session,
    create_session_if_enabled,
    get_session_messages,
    get_session_info,
    is_sessions_enabled,
)

logger = logging.getLogger(__name__)


def create_agent_router(
    agent: Agent,
    prefix: str,
    agent_name: str,
) -> APIRouter:
    """
    Generate a FastAPI router with 5 standardized endpoints for the given Agent.

    Endpoints created:
        POST   {prefix}/run                   — synchronous run
        POST   {prefix}/stream                — SSE streaming run
        GET    {prefix}/session/{session_id}  — retrieve session history
        DELETE {prefix}/session/{session_id}  — clear session history
        GET    {prefix}/info                  — agent metadata

    Args:
        agent:       The configured Agent instance to expose.
        prefix:      URL prefix for all routes (e.g. "/orders").
        agent_name:  Human-readable name shown in docs and /info response.
    """
    router = APIRouter(prefix=prefix, tags=[agent_name])

    # ------------------------------------------------------------------
    # POST /run  — synchronous, returns after full completion
    # ------------------------------------------------------------------
    @router.post("/run", response_model=AgentResponse)
    async def run_agent(request: AgentRequest) -> AgentResponse:
        """Run the agent synchronously. Waits for the complete output before returning."""
        session = create_session_if_enabled(request.session_id)
        try:
            result = await Runner.run(
                agent,
                input=request.input,
                context=request.context,
                session=session,
            )
            usage = _extract_usage(result)
            return AgentResponse(
                output=result.final_output,
                success=True,
                usage=usage,
                session_id=request.session_id if session else None,
            )
        except Exception as exc:
            logger.exception("Agent run failed for session %s", request.session_id)
            return AgentResponse(
                output=f"Error: {exc}",
                success=False,
                usage={},
                session_id=request.session_id if session else None,
            )

    # ------------------------------------------------------------------
    # POST /stream  — SSE streaming
    # ------------------------------------------------------------------
    @router.post("/stream")
    async def stream_agent(request: AgentRequest) -> StreamingResponse:
        """
        Run the agent and stream events as Server-Sent Events (SSE).

        Connect with:
            EventSource or fetch() with ReadableStream on the client side.
            Each event is a JSON-encoded line: data: {...}\\n\\n
        """
        session = create_session_if_enabled(request.session_id)

        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                result = Runner.run_streamed(  # NOT awaited — returns RunResultStreaming
                    agent,
                    input=request.input,
                    context=request.context,
                    session=session,
                )

                async for event in result.stream_events():
                    payload = _format_stream_event(event)
                    if payload:
                        yield f"data: {json.dumps(payload)}\n\n"

                # After stream exhausted, emit completion with usage
                usage = _extract_usage(result)
                yield f"data: {json.dumps({'type': 'stream_complete', 'usage': usage, 'session_id': request.session_id if session else None})}\n\n"

            except Exception as exc:
                logger.exception("Streaming failed for session %s", request.session_id)
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    # ------------------------------------------------------------------
    # GET /session/{session_id}  — retrieve history
    # ------------------------------------------------------------------
    @router.get("/session/{session_id}", response_model=SessionMessagesResponse)
    async def get_session(
        session_id: str,
        limit: Optional[int] = None,
    ) -> SessionMessagesResponse:
        """Retrieve stored conversation history for a session."""
        messages = await get_session_messages(session_id, limit=limit)
        return SessionMessagesResponse(
            session_id=session_id,
            messages=messages,
            count=len(messages),
        )

    # ------------------------------------------------------------------
    # DELETE /session/{session_id}  — clear history
    # ------------------------------------------------------------------
    @router.delete("/session/{session_id}")
    async def delete_session(session_id: str) -> dict[str, Any]:
        """Clear all conversation history for a session."""
        cleared = await clear_session(session_id)
        return {"session_id": session_id, "cleared": cleared}

    # ------------------------------------------------------------------
    # GET /info  — agent metadata
    # ------------------------------------------------------------------
    @router.get("/info", response_model=AgentInfo)
    async def agent_info() -> AgentInfo:
        """Return static metadata about this agent and its available endpoints."""
        tool_names = [
            getattr(t, "name", type(t).__name__)
            for t in (agent.tools or [])
        ]
        handoff_names = [
            getattr(h, "agent_name", getattr(h, "name", str(h)))
            for h in (agent.handoffs or [])
        ]
        return AgentInfo(
            name=agent_name,
            model=agent.model or "default",
            tools=tool_names,
            handoffs=handoff_names,
            endpoints=[
                f"POST {prefix}/run",
                f"POST {prefix}/stream",
                f"GET  {prefix}/session/{{session_id}}",
                f"DELETE {prefix}/session/{{session_id}}",
                f"GET  {prefix}/info",
            ],
            sessions_enabled=is_sessions_enabled(),
        )

    return router


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_stream_event(event: Any) -> Optional[dict]:
    """Map an SDK StreamEvent to a JSON-serialisable dict for SSE clients."""
    if event.type == "raw_response_event":
        return _format_raw_response_event(event)
    if event.type == "run_item_stream_event":
        return _format_run_item_event(event)
    if event.type == "agent_updated_stream_event":
        return {
            "type": "agent_updated",
            "agent_name": event.new_agent.name if event.new_agent else None,
        }
    return None  # unknown event types are silently dropped


def _format_raw_response_event(event: Any) -> Optional[dict]:
    """Handle raw LLM response events (text deltas, tool calls, etc.)."""
    data = event.data
    if isinstance(data, ResponseTextDeltaEvent):
        return {"type": "text_delta", "delta": data.delta}
    # Other raw types (tool call delta, reasoning, refusal) — pass through type only
    event_type = getattr(data, "type", None)
    if event_type:
        return {"type": event_type, "raw": True}
    return None


def _format_run_item_event(event: Any) -> Optional[dict]:
    """Handle higher-level run item events (message complete, tool call, handoff)."""
    item = event.item
    item_type = getattr(item, "type", None)

    if item_type == "message_output_item":
        text = ItemHelpers.text_message_output(item)
        return {"type": "message_complete", "text": text}

    if item_type == "tool_call_item":
        return {
            "type": "tool_call",
            "tool_name": getattr(item, "name", None),
            "call_id": getattr(item, "call_id", None),
        }

    if item_type == "tool_call_output_item":
        return {
            "type": "tool_result",
            "call_id": getattr(item, "call_id", None),
            "output": getattr(item, "output", None),
        }

    if item_type == "handoff_item":
        return {
            "type": "handoff",
            "target_agent": getattr(item, "target_agent_name", None),
        }

    return None


def _extract_usage(result: Any) -> dict[str, int]:
    """Pull token counts from the run result's raw responses."""
    usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        for raw in getattr(result, "raw_responses", []):
            u = getattr(raw, "usage", None)
            if u:
                usage["input_tokens"] += getattr(u, "input_tokens", 0)
                usage["output_tokens"] += getattr(u, "output_tokens", 0)
                usage["total_tokens"] += getattr(u, "total_tokens", 0)
    except Exception:
        pass
    return usage
