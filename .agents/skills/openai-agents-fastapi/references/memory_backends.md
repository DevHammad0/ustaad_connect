# Memory / Session Backends Reference

All backends implement the same interface: pass `session=<backend>` to `Runner.run()`.
The SDK automatically loads history before the run and persists new messages after.

---

## Table of Contents
1. [SQLite (default/lightweight)](#1-sqlite-defaultlightweight)
2. [Redis (production recommended)](#2-redis-production-recommended)
3. [SQLAlchemy / Postgres](#3-sqlalchemy--postgres)
4. [Dapr (distributed/cloud-native)](#4-dapr-distributedcloud-native)
5. [Encrypted Session](#5-encrypted-session)
6. [Compaction Session (long context)](#6-compaction-session-long-context)
7. [HITL Across Sessions](#7-hitl-across-sessions)
8. [Session Interface Reference](#8-session-interface-reference)

---

## 1. SQLite (default/lightweight)

No extra install. File-backed, single-server only.

```python
import asyncio
from agents import Agent, Runner, SQLiteSession

agent = Agent(name="Assistant", instructions="Reply very concisely.")

# session_id becomes the conversation key; SQLite file defaults to ./conversations.db
session = SQLiteSession("conversation_123")

async def main():
    result = await Runner.run(agent, "What city is the Golden Gate Bridge in?", session=session)
    print(result.final_output)  # San Francisco

    result = await Runner.run(agent, "What state is it in?", session=session)
    print(result.final_output)  # California (remembers context)

    # Inspect history
    all_items = await session.get_items()
    latest_items = await session.get_items(limit=2)
    print(f"Total items: {len(all_items)}, latest 2: {len(latest_items)}")

    session.close()
```

---

## 2. Redis (production recommended)

```bash
pip install "openai-agents[redis]"
# or: uv add "openai-agents[redis]"
```

```python
import asyncio
from agents import Agent, Runner
from agents.extensions.memory.redis_session import RedisSession

agent = Agent(name="Assistant", instructions="Reply very concisely.")


async def main():
    session_id = "redis_conversation_123"
    session = RedisSession.from_url(
        session_id,
        url="redis://localhost:6379/0",
    )

    if not await session.ping():
        print("Redis not available. Start with: redis-server")
        return

    await session.clear_session()  # clean start for demo

    result = await Runner.run(agent, "What city is the Golden Gate Bridge in?", session=session)
    print(result.final_output)

    result = await Runner.run(agent, "What state is it in?", session=session)
    print(result.final_output)

    await session.close()


async def demonstrate_advanced():
    # TTL-based expiry
    ttl_session = RedisSession.from_url(
        "ttl_session",
        url="redis://localhost:6379/0",
        ttl=3600,  # 1-hour expiry
    )

    # Multi-tenancy via custom key prefix
    tenant_session = RedisSession.from_url(
        "user_123",
        url="redis://localhost:6379/0",
        key_prefix="tenant_abc:sessions",
    )
```

---

## 3. SQLAlchemy / Postgres

```bash
pip install "openai-agents[sqlalchemy]"
# also: pip install asyncpg  # for Postgres async driver
```

```python
import asyncio
from agents import Agent, Runner
from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession

agent = Agent(name="Assistant", instructions="Reply very concisely.")


async def main():
    # SQLite (dev/test) — create_tables=True is useful for development
    session = SQLAlchemySession.from_url(
        "conversation_123",
        url="sqlite+aiosqlite:///:memory:",
        create_tables=True,
    )

    # Postgres (production)
    # session = SQLAlchemySession.from_url(
    #     "conversation_123",
    #     url="postgresql+asyncpg://user:pass@localhost/dbname",
    #     create_tables=True,
    # )

    result = await Runner.run(agent, "What city is the Golden Gate Bridge in?", session=session)
    print(result.final_output)

    result = await Runner.run(agent, "What state is it in?", session=session)
    print(result.final_output)

    latest_items = await session.get_items(limit=2)
    all_items = await session.get_items()
    print(f"Total: {len(all_items)}, latest 2: {len(latest_items)}")
```

---

## 4. Dapr (distributed/cloud-native)

Use when you need horizontal scaling, multi-region, or backend flexibility (Redis, PostgreSQL, Cosmos DB, etc.) via Dapr's state management.

```bash
pip install "openai-agents[dapr]"
```

Prerequisites:
```bash
# Install Dapr CLI and initialize
dapr init
# Start sidecar (in a separate terminal)
dapr run --app-id myapp --dapr-http-port 3500 --dapr-grpc-port 50001 --resources-path ./components
```

```python
import asyncio
import os
from agents import Agent, Runner
from agents.extensions.memory import (
    DAPR_CONSISTENCY_EVENTUAL,
    DAPR_CONSISTENCY_STRONG,
    DaprSession,
)

grpc_port = os.environ.get("DAPR_GRPC_PORT", "50001")
DEFAULT_STATE_STORE = os.environ.get("DAPR_STATE_STORE", "statestore")

agent = Agent(name="Assistant", instructions="Reply very concisely.")


async def main():
    session_id = "dapr_conversation_123"

    # Use async context manager for automatic cleanup
    async with DaprSession.from_address(
        session_id,
        state_store_name=DEFAULT_STATE_STORE,
        dapr_address=f"localhost:{grpc_port}",
    ) as session:
        if not await session.ping():
            print("Dapr sidecar not available")
            return

        await session.clear_session()

        result = await Runner.run(agent, "What city is the Golden Gate Bridge in?", session=session)
        print(result.final_output)

        result = await Runner.run(agent, "What state is it in?", session=session)
        print(result.final_output)


async def advanced_dapr():
    # TTL (store-dependent support)
    async with DaprSession.from_address(
        "ttl_demo",
        state_store_name=DEFAULT_STATE_STORE,
        dapr_address=f"localhost:{grpc_port}",
        ttl=3600,
    ) as ttl_session:
        pass  # messages auto-expire in 1 hour

    # Consistency levels
    async with DaprSession.from_address(
        "strong_session",
        state_store_name=DEFAULT_STATE_STORE,
        dapr_address=f"localhost:{grpc_port}",
        consistency=DAPR_CONSISTENCY_STRONG,  # or DAPR_CONSISTENCY_EVENTUAL
    ) as strong_session:
        pass

    # Multi-tenancy: use "tenant:user" as session_id for isolation
    async with DaprSession.from_address(
        "tenant-abc:user-123",
        state_store_name=DEFAULT_STATE_STORE,
        dapr_address=f"localhost:{grpc_port}",
    ) as tenant_session:
        pass
```

---

## 5. Encrypted Session

Wraps any session backend with transparent AES-GCM encryption. Items stored encrypted at rest.

```python
import asyncio
from agents import Agent, Runner, SQLiteSession
from agents.extensions.memory import EncryptedSession

agent = Agent(name="Assistant", instructions="Reply very concisely.")


async def main():
    session_id = "conversation_123"
    underlying_session = SQLiteSession(session_id)

    session = EncryptedSession(
        session_id=session_id,
        underlying_session=underlying_session,
        encryption_key="my-secret-encryption-key",  # use env var in production
        ttl=3600,  # 1-hour TTL for messages
    )

    result = await Runner.run(agent, "What city is the Golden Gate Bridge in?", session=session)
    print(result.final_output)

    result = await Runner.run(agent, "What state is it in?", session=session)
    print(result.final_output)

    # Decrypted transparently on read
    latest_items = await session.get_items(limit=2)
    print(f"Latest 2 (auto-decrypted): {len(latest_items)}")

    # Verify raw storage is encrypted
    raw_items = await underlying_session.get_items()
    for item in raw_items:
        if isinstance(item, dict) and item.get("__enc__") == 1:
            print(f"Encrypted envelope: payload length={len(item['payload'])}")

    underlying_session.close()
```

---

## 6. Compaction Session (long context)

Automatically compacts history when it grows too large, preserving context while reducing token usage.

```python
import asyncio
from agents import Agent, OpenAIResponsesCompactionSession, Runner, SQLiteSession

agent = Agent(
    name="Assistant",
    instructions="Reply concisely. Keep answers to 1-2 sentences.",
)


async def main():
    underlying = SQLiteSession(":memory:")

    session = OpenAIResponsesCompactionSession(
        session_id="demo-session",
        underlying_session=underlying,
        model="gpt-4.1",
        # Trigger compaction when >= 4 candidate items accumulate (default: 10)
        should_trigger_compaction=lambda ctx: len(ctx["compaction_candidate_items"]) >= 4,
    )

    prompts = [
        "What is the tallest mountain in the world?",
        "How tall is it in feet?",
        "When was it first climbed?",
        "Who was on that expedition?",
        "What country is the mountain in?",
    ]

    for i, prompt in enumerate(prompts, 1):
        print(f"Turn {i}: {prompt}")
        result = await Runner.run(agent, prompt, session=session)
        print(f"Assistant: {result.final_output}\n")

    # Inspect state after auto-compaction
    items = await session.get_items()
    print(f"Total items after auto-compaction: {len(items)}")
    for item in items:
        item_type = item.get("type") or ("message" if "role" in item else "unknown")
        print(f"  - {item_type}")

    # Manual compaction
    await session.run_compaction({"force": True})
    items = await session.get_items()
    print(f"Total items after manual compaction: {len(items)}")
```

---

## 7. HITL Across Sessions

Tools with `needs_approval=True` persist state across process boundaries. Resume from serialized `RunState`.

```python
import asyncio
import json
from pathlib import Path
from agents import Agent, ModelSettings, Runner, RunState, function_tool


@function_tool(
    name_override="fetch_profile",
    description_override="Fetches a customer profile after approval.",
    needs_approval=True,
)
def fetch_profile(customer_id: str) -> str:
    """Fetch profile for a customer."""
    return f"Profile for customer {customer_id}: VIP member since 2020"


agent = Agent(
    name="Support Agent",
    instructions="Fetch customer profiles when asked. Always use the fetch_profile tool.",
    tools=[fetch_profile],
    model_settings=ModelSettings(tool_choice="required"),
)

STATE_PATH = Path(".cache/hitl_state.json")


async def run_with_approval(message: str) -> str:
    """Run agent with interactive HITL approval loop."""
    result = await Runner.run(agent, message)

    while result.interruptions:
        print(f"\n{len(result.interruptions)} tool call(s) pending approval:")
        state = result.to_state()
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state.to_json()))

        # In production: serialize state, send to approval queue, resume in separate process
        stored = json.loads(STATE_PATH.read_text())
        state = await RunState.from_json(agent, stored)

        for interruption in result.interruptions:
            print(f"  Tool: {interruption.name}")
            print(f"  Args: {interruption.arguments}")
            approved = input("  Approve? (y/n): ").strip().lower() == "y"
            if approved:
                state.approve(interruption)
            else:
                state.reject(interruption)

        result = await Runner.run(agent, state)

    return result.final_output


async def main():
    output = await run_with_approval("Fetch profile for customer 104.")
    print(f"\nFinal output: {output}")
```

---

## 8. Session Interface Reference

All session backends implement:

| Method | Description |
|--------|-------------|
| `await session.get_items(limit=None)` | Retrieve conversation history (optionally last N items) |
| `await session.add_items(items)` | Append new items to history |
| `await session.clear_session()` | Delete all stored history |
| `await session.ping()` | Connectivity check (Redis/Dapr) |

Pass to runner:
```python
result = await Runner.run(agent, "message", session=session)
# SDK automatically calls get_items() before and add_items() after
```

Session backends:

| Backend | Import | Extra |
|---------|--------|-------|
| `SQLiteSession` | `from agents import SQLiteSession` | none |
| `RedisSession` | `from agents.extensions.memory.redis_session import RedisSession` | `openai-agents[redis]` |
| `SQLAlchemySession` | `from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession` | `openai-agents[sqlalchemy]` |
| `DaprSession` | `from agents.extensions.memory import DaprSession` | `openai-agents[dapr]` |
| `EncryptedSession` | `from agents.extensions.memory import EncryptedSession` | none (wraps another session) |
| `OpenAIResponsesCompactionSession` | `from agents import OpenAIResponsesCompactionSession` | none |
