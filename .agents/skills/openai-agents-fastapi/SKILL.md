---
name: openai-agents-fastapi
description: |
  Expose OpenAI Agents SDK agents through FastAPI with SSE streaming endpoints,
  session memory, and standardized routes. Use when connecting openai-agents to
  a FastAPI server, serving agents over HTTP, building streaming agent APIs,
  or when the user mentions FastAPI + agents, /stream endpoints, SSE with agents,
  wants to call an agent from a REST client, or needs to add HTTP API routes
  around an OpenAI agent. Also use when the user is building any agent-powered
  backend (WhatsApp bot, chatbot, assistant API, order-taking service) and needs
  HTTP endpoints to receive messages and stream responses.
---

# OpenAI Agents SDK — FastAPI Integration

Wire any `Agent` into a production FastAPI server with streaming SSE endpoints, session memory,
and standardized routes. Complements the `openai-agents-sdk` skill (building agents) with the HTTP layer.

## Read Only What You Need

Most tasks only need the templates + the core sections below. Only read reference files
when the task explicitly involves that topic.

| Only read if... | File |
|---|---|
| User needs multi-agent setup, error handling, or architecture overview | `references/patterns.md` |
| User is building a frontend/client that consumes SSE events (event shapes, field names) | `references/sse_events.md` |
| User is writing a **custom** streaming loop (not using the router_factory template) | `references/streaming_internals.md` |
| User mentions **session memory**, Redis, SQLAlchemy, Dapr, or distributed sessions | `references/memory_backends.md` |
| User needs a complete worked example with Redis + SSE + tools + handoffs | `references/e2e_example.md` |
| User mentions **MCP**, Model Context Protocol, or attaching an MCP server | `references/mcp.md` |
| User mentions **hosted tools**: web search, file search, code interpreter | `references/hosted_tools.md` |
| User mentions **tracing**, observability, Langfuse, or trace processors | `references/tracing.md` |
| User mentions guardrails, HITL, parallelization, LLM-as-judge, or routing patterns | `references/agent_patterns.md` |

**Templates** (copy these directly into the project — read only the ones needed):
- `assets/templates/main.py` — FastAPI app with lifespan, CORS, health endpoint
- `assets/templates/router_factory.py` — `create_agent_router()`: the 5-endpoint factory
- `assets/templates/request_models.py` — Pydantic request/response models
- `assets/templates/session_utils.py` — SQLiteSession helpers (read if sessions are needed)
- `assets/templates/example_router.py` — minimal end-to-end wiring (start here)

---

## Workflow

1. **Build the agent first** (use `openai-agents-sdk` skill if needed)
2. **Copy `main.py` + `router_factory.py` + `request_models.py`** into the project
3. **Create a router** with `create_agent_router(agent, prefix="/yourpath", agent_name="Your Agent")`
4. **Mount the router** in the FastAPI app: `app.include_router(router)`
5. **Set env vars** and run: `uvicorn src.api.main:app --reload`

For sessions: also copy `session_utils.py` and set `ENABLE_SESSIONS=true`.

---

## The 5-Endpoint Pattern

Every `create_agent_router()` call generates these automatically:

| Method | Path | Purpose | Returns |
|--------|------|---------|---------|
| `POST` | `{prefix}/run` | Synchronous, waits for full output | `AgentResponse` |
| `POST` | `{prefix}/stream` | SSE stream, real-time events | `StreamingResponse` |
| `GET` | `{prefix}/session/{session_id}` | Retrieve conversation history | `SessionMessagesResponse` |
| `DELETE` | `{prefix}/session/{session_id}` | Clear session memory | `{"cleared": true}` |
| `GET` | `{prefix}/info` | Agent metadata (model, tools, handoffs) | `AgentInfo` |

**Request body** (both `/run` and `/stream`):
```json
{ "input": "What can I order?", "session_id": "user-abc123", "context": {} }
```
`session_id` is optional. When provided and `ENABLE_SESSIONS=true`, history is loaded before
the run and persisted after.

---

## Session Integration

Sessions are opt-in per request (pass `session_id`) and opt-out globally (`ENABLE_SESSIONS=false`).
SQLite-backed by default — good for single-server deployments. For distributed deployments
(multiple servers, WhatsApp bots, etc.) swap to `RedisSession` or `SQLAlchemySession`.

```bash
ENABLE_SESSIONS=true           # default: true
SESSION_DB_PATH=./sessions.db  # default: ./conversations.db
```

For Redis/SQLAlchemy/Dapr backends, read `references/memory_backends.md`.

---

## Key Rules

- **Always `async def` endpoints** — `Runner.run_sync()` blocks the event loop. Use `await Runner.run()` or `Runner.run_streamed()`.
- **`Runner.run_streamed()` is NOT awaited** — call it directly, then `async for event in result.stream_events()`.
- **`StreamingResponse` must use `media_type="text/event-stream"`** for SSE.
- **Validate `OPENAI_API_KEY` at startup** in the lifespan — fail fast with a clear message.
- **One router per agent, one prefix per router** — keeps routes clean and auto-docs readable.
- **CORS**: default config allows all origins — restrict `allow_origins` in production.

---

## Environment Variables

```bash
OPENAI_API_KEY=sk-...          # Required
ENABLE_SESSIONS=true           # Optional, default true
SESSION_DB_PATH=./sessions.db  # Optional
LOG_LEVEL=INFO                 # Optional
```

---

## Dependencies

```toml
[project]
dependencies = [
    "fastapi[standard]>=0.116.1",
    "openai-agents>=0.2.3",
    "uvicorn[standard]>=0.35.0",
    "python-dotenv>=1.1.1",
]
```

```bash
# Base install
pip install "fastapi[standard]" "openai-agents>=0.2.3" "uvicorn[standard]" python-dotenv

# Extras: redis → openai-agents[redis] | postgres → openai-agents[sqlalchemy] asyncpg
#         dapr  → openai-agents[dapr]  | voice   → openai-agents[voice]
```

---

## Validate

```bash
uvicorn src.api.main:app --reload

curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello", "session_id": "test-1"}'

curl -N -X POST http://localhost:8000/agent/stream \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello", "session_id": "test-1"}'

curl http://localhost:8000/agent/info
```

---

## Reference Links

- Docs: https://openai.github.io/openai-agents-python/
- Examples: https://github.com/openai/openai-agents-python/tree/main/examples
