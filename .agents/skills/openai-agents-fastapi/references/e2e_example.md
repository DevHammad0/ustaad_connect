# End-to-End Example: FastAPI + Redis Session + SSE Streaming + Function Tool + Handoff

A self-contained FastAPI app combining Redis session memory, streaming SSE endpoints, a function tool, and agent handoff.

## Install

```bash
pip install "fastapi[standard]" "openai-agents[redis]" "uvicorn[standard]" python-dotenv
# or: uv add "fastapi[standard]" "openai-agents[redis]" "uvicorn[standard]" python-dotenv
```

Requires Redis running: `docker run -d -p 6379:6379 redis:7-alpine`

## Project Layout

```
src/
├── agents/
│   ├── __init__.py
│   └── support_agents.py   ← agent definitions
└── api/
    ├── __init__.py
    └── main.py              ← FastAPI app (this file)
.env
```

## .env

```env
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379/0
ENABLE_SESSIONS=true
```

## src/agents/support_agents.py

```python
from typing import Annotated
from agents import Agent, function_tool


@function_tool
def get_order_status(order_id: Annotated[str, "The order ID to look up"]) -> str:
    """Look up the status of a customer order."""
    # In production: query your database
    statuses = {
        "ORD-001": "shipped",
        "ORD-002": "processing",
        "ORD-003": "delivered",
    }
    status = statuses.get(order_id, "not found")
    return f"Order {order_id} status: {status}"


# Specialist agent for billing questions
billing_agent = Agent(
    name="Billing Agent",
    instructions=(
        "You are a billing specialist. Answer only billing-related questions concisely. "
        "If a question is not about billing, tell the user to ask the support agent."
    ),
    handoff_description="A billing specialist for payment and invoice questions.",
)

# Primary support agent — hands off billing questions to billing_agent
support_agent = Agent(
    name="Support Agent",
    instructions=(
        "You are a customer support agent. "
        "Use get_order_status to look up orders. "
        "For billing or payment questions, hand off to the billing agent. "
        "Be concise and helpful."
    ),
    tools=[get_order_status],
    handoffs=[billing_agent],
)
```

## src/api/main.py

```python
import json
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai.types.responses import ResponseTextDeltaEvent
from pydantic import BaseModel

from agents import Agent, RawResponsesStreamEvent, Runner, RunItemStreamEvent
from agents.extensions.memory.redis_session import RedisSession


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Support Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Import agents (after FastAPI app is defined to avoid circular imports)
# ---------------------------------------------------------------------------

from src.agents.support_agents import support_agent  # noqa: E402


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    input: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    output: str
    session_id: str | None


# ---------------------------------------------------------------------------
# Session helper
# ---------------------------------------------------------------------------

def get_session(session_id: str | None) -> RedisSession | None:
    if not session_id or os.getenv("ENABLE_SESSIONS", "true").lower() != "true":
        return None
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return RedisSession.from_url(session_id, url=redis_url)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/support/run", response_model=ChatResponse)
async def run_sync(request: ChatRequest):
    """Synchronous endpoint — waits for full output before responding."""
    session = get_session(request.session_id)
    try:
        result = await Runner.run(support_agent, input=request.input, session=session)
        return ChatResponse(output=result.final_output, session_id=request.session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if session:
            await session.close()


@app.post("/support/stream")
async def run_stream(request: ChatRequest):
    """SSE streaming endpoint — real-time token delivery."""
    session = get_session(request.session_id)

    async def event_generator():
        try:
            result = Runner.run_streamed(support_agent, input=request.input, session=session)

            async for event in result.stream_events():
                # Raw LLM text tokens
                if (
                    event.type == "raw_response_event"
                    and isinstance(event.data, ResponseTextDeltaEvent)
                ):
                    payload = {"type": "text_delta", "delta": event.data.delta}
                    yield f"data: {json.dumps(payload)}\n\n"

                # Structured run items (tool calls, handoffs, messages)
                elif event.type == "run_item_stream_event":
                    item = event.item
                    if item.type == "tool_call_item":
                        raw = item.raw_item
                        tool_name = getattr(raw, "name", "unknown")
                        payload = {"type": "tool_call", "tool_name": tool_name}
                        yield f"data: {json.dumps(payload)}\n\n"
                    elif item.type == "tool_call_output_item":
                        payload = {"type": "tool_result", "output": str(item.output)[:500]}
                        yield f"data: {json.dumps(payload)}\n\n"

                # Agent switch (handoff completed)
                elif event.type == "agent_updated_stream_event":
                    payload = {"type": "agent_updated", "agent_name": event.new_agent.name}
                    yield f"data: {json.dumps(payload)}\n\n"

            # Final event with token usage
            usage = result.final_response.usage if result.final_response else {}
            payload = {
                "type": "stream_complete",
                "session_id": request.session_id,
                "usage": {
                    "input_tokens": getattr(usage, "input_tokens", 0),
                    "output_tokens": getattr(usage, "output_tokens", 0),
                },
            }
            yield f"data: {json.dumps(payload)}\n\n"

        except Exception as exc:
            payload = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(payload)}\n\n"
        finally:
            if session:
                await session.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/support/session/{session_id}")
async def get_session_history(session_id: str):
    """Retrieve conversation history for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=400, detail="Sessions not enabled or no session_id")
    try:
        items = await session.get_items()
        return {"session_id": session_id, "message_count": len(items), "messages": items}
    finally:
        await session.close()


@app.delete("/support/session/{session_id}")
async def clear_session_history(session_id: str):
    """Clear conversation history for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=400, detail="Sessions not enabled")
    try:
        await session.clear_session()
        return {"cleared": True, "session_id": session_id}
    finally:
        await session.close()
```

## Run

```bash
uvicorn src.api.main:app --reload --port 8000
```

## Test

```bash
# Sync run
curl -X POST http://localhost:8000/support/run \
  -H "Content-Type: application/json" \
  -d '{"input": "What is the status of order ORD-001?", "session_id": "user-123"}'

# SSE stream
curl -N -X POST http://localhost:8000/support/stream \
  -H "Content-Type: application/json" \
  -d '{"input": "I have a billing question about my invoice.", "session_id": "user-123"}'

# Follow-up (context preserved via Redis session)
curl -X POST http://localhost:8000/support/run \
  -H "Content-Type: application/json" \
  -d '{"input": "What about order ORD-002?", "session_id": "user-123"}'

# View session history
curl http://localhost:8000/support/session/user-123

# Clear session
curl -X DELETE http://localhost:8000/support/session/user-123
```

## Key Patterns Demonstrated

- **Redis session**: `RedisSession.from_url(session_id, url=redis_url)` — pass `session=` to `Runner.run()` / `Runner.run_streamed()`
- **SSE streaming**: `Runner.run_streamed()` is NOT awaited; iterate with `async for event in result.stream_events()`
- **Token streaming**: check `event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent)`
- **Tool events**: `event.type == "run_item_stream_event"` → `event.item.type in ("tool_call_item", "tool_call_output_item")`
- **Handoff events**: `event.type == "agent_updated_stream_event"` → `event.new_agent.name`
- **Error handling**: always wrap the generator in try/except and emit `{"type": "error"}` so the client knows
- **Session cleanup**: always `await session.close()` in a `finally` block
