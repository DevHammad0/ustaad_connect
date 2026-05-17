# Patterns — OpenAI Agents FastAPI Integration

## Architecture Overview

```
HTTP Client
    │
    ▼
FastAPI app (main.py)
    │  lifespan: load .env, validate OPENAI_API_KEY
    │  CORS middleware
    │  GET /health
    │
    ├── APIRouter (prefix=/orders)      ← create_agent_router(order_agent, ...)
    │       POST /orders/run
    │       POST /orders/stream
    │       GET  /orders/session/{id}
    │       DELETE /orders/session/{id}
    │       GET  /orders/info
    │
    └── APIRouter (prefix=/support)     ← create_agent_router(support_agent, ...)
            POST /support/run
            POST /support/stream
            ...
```

One router factory call → 5 endpoints. Add as many agents as you need.

---

## Critical: Streaming Gotcha

`Runner.run_streamed()` is **not** awaited. It returns a `RunResultStreaming` object immediately. You then async-iterate its events:

```python
# CORRECT
result = Runner.run_streamed(agent, input="hello")  # no await
async for event in result.stream_events():
    ...

# WRONG — this would block until the run completes before streaming
result = await Runner.run_streamed(agent, input="hello")  # breaks streaming
```

`Runner.run()` IS awaited (returns `RunResult` after completion):

```python
# CORRECT
result = await Runner.run(agent, input="hello")
print(result.final_output)
```

---

## Multiple Agents in One App

```python
# src/api/main.py
from .routers.order_bot import router as order_router
from .routers.support_bot import router as support_router

app.include_router(order_router)   # prefix="/orders"
app.include_router(support_router) # prefix="/support"
```

Each agent gets its own router, its own session namespace, and its own `/info` endpoint. They share the same FastAPI process but are otherwise independent.

---

## Error Handling in the Stream Generator

Always wrap the streaming body in try/except and emit an error event — otherwise the client gets a broken stream with no indication of what went wrong:

```python
async def event_generator():
    try:
        result = Runner.run_streamed(agent, input=request.input)
        async for event in result.stream_events():
            payload = _format_stream_event(event)
            if payload:
                yield f"data: {json.dumps(payload)}\n\n"
        yield f"data: {json.dumps({'type': 'stream_complete'})}\n\n"
    except Exception as exc:
        logger.exception("Streaming failed")
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
```

---

## Session Strategy

| Scenario | `session_id` | Result |
|----------|-------------|--------|
| First message, new user | `"user-abc"` | Creates session, stores message |
| Follow-up from same user | `"user-abc"` | Loads history, runs with context, stores new turn |
| Stateless (no memory needed) | omit | No DB read/write, fully stateless |
| One-time context injection | omit + pass `context={}` | Context goes to this run only |

For WhatsApp bots, use the WhatsApp `from` phone number as `session_id` — it's already a stable per-user identifier.

---

## Connecting to a WhatsApp Webhook

A typical WhatsApp webhook flow with this skill:

```python
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(body: dict):
    sender = body["from"]       # e.g. "14155551234"
    message = body["text"]      # e.g. "I'd like to order a pizza"

    # Reuse the /stream internally, or call Runner directly:
    session = create_session_if_enabled(sender)
    result = await Runner.run(platr_agent, input=message, session=session)
    reply = result.final_output

    # Send reply back via WhatsApp API
    await send_whatsapp_message(to=sender, text=reply)
    return {"status": "ok"}
```

The session memory means the agent remembers the order across multiple messages in the conversation.

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key. |
| `ENABLE_SESSIONS` | `true` | Set to `false` to disable all session storage. |
| `SESSION_DB_PATH` | `./conversations.db` | Path to the SQLite database file. |
| `LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

---

## pyproject.toml / requirements

```toml
[project]
requires-python = ">=3.11"
dependencies = [
    "fastapi[standard]>=0.116.1",
    "openai-agents>=0.2.3",
    "uvicorn[standard]>=0.35.0",
    "python-dotenv>=1.1.1",
]
```

Or with `uv`:
```bash
uv add "fastapi[standard]" "openai-agents" "uvicorn[standard]" python-dotenv
```

---

## Recommended Project Layout

```
src/
├── api/
│   ├── main.py             ← FastAPI app (from templates/main.py)
│   ├── router_factory.py   ← create_agent_router (from templates/router_factory.py)
│   ├── request_models.py   ← Pydantic models (from templates/request_models.py)
│   ├── session_utils.py    ← Session helpers (from templates/session_utils.py)
│   └── routers/
│       ├── order_bot.py    ← Agent + router for order taking
│       └── support_bot.py  ← Agent + router for support
└── agents/                 ← Pure agent definitions (no FastAPI imports)
    ├── order_agent.py
    └── support_agent.py
```

Separating pure agent definitions from the API layer keeps agents testable without starting a server.

---

## Production Checklist

- [ ] Set `allow_origins` to specific domains (not `"*"`) in CORSMiddleware
- [ ] Add rate limiting on `/run` and `/stream` (e.g. `slowapi` or a reverse proxy)
- [ ] Use `RedisSession` or `SQLAlchemySession` instead of `SQLiteSession` for multi-worker deployments
- [ ] Set `SESSION_DB_PATH` to a persistent volume mount (not container-local `/tmp`)
- [ ] Add authentication middleware before agent routers for protected deployments
- [ ] Configure `uvicorn` workers: `uvicorn src.api.main:app --workers 4`
