# Patterns (defaults + escape hatches)

## Contents
- Agent setup (single-agent default)
- Tools (schemas + reliability)
- Running (sync/async)
- Streaming (event loop)
- Sessions / memory (persistence + trimming)
- Handoffs (multi-agent routing)
- Guardrails (validation + short-circuit)
- Tracing (spans + metadata)
- MCP integration (consume MCP tools)

> If you need exact imports or signatures, consult [`docs-map.md`](docs-map.md) and follow the relevant official page.

## Agent setup (single-agent default)

### Default
- Implement **one agent** with a clear instruction block and a small set of tools.
- Keep the system instruction focused on: role, goals, constraints, tool usage rules, and output shape.
- Prefer returning a **structured final output** (JSON-ish dict / Pydantic model) if the caller needs reliability.

**Minimal example (Running agents docs)**

```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="You are a helpful assistant")
result = await Runner.run(agent, "Write a haiku about recursion in programming.")
print(result.final_output)
```

### Escape hatch
- If the agent has distinct roles or failure domains, switch to **handoffs** (see Handoffs).

## Tools (schemas + reliability)

### Default
- Design tools first. Treat tools as the contract between the agent and your system.
- Make tool inputs explicit and validated:
  - Prefer typed parameters (`str`, `int`, `bool`, enums) and structured objects (Pydantic) when needed.
  - Reject invalid inputs early (guardrails or tool-level validation).
- Make tools deterministic:
  - Idempotency where applicable
  - Clear error messages
  - Timeouts/retries when calling external services

**Default tool pattern (`@function_tool`)**

```python
from typing import Any
from typing_extensions import TypedDict
from agents import RunContextWrapper, function_tool

class Location(TypedDict):
    lat: float
    long: float

@function_tool
async def fetch_weather(location: Location) -> str:
    return "sunny"

@function_tool(name_override="fetch_data")
def read_file(ctx: RunContextWrapper[Any], path: str, directory: str | None = None) -> str:
    return "<file contents>"
```

### Escape hatch
- If tool arguments are complex, use a Pydantic model for arguments and keep the tool signature small.

## Running (sync/async)

### Default
- Use the SDK “runner” pattern from the official docs:
  - A thin wrapper that creates the agent and executes a run
  - Centralized configuration (model/settings/timeouts)

### Escape hatch
- If you need concurrency/background tasks/cancellation, follow the “running agents” guide and use async execution patterns.

## Streaming (event loop)

### Default
- Stream events and render incrementally:
  - Display partial model output as it arrives
  - Show tool execution start/end
  - Collect the final result at the end

**Default streaming pattern (Streaming docs)**

```python
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner

agent = Agent(name="Joker", instructions="You are a helpful assistant.")
result = Runner.run_streamed(agent, input="Please tell me 5 jokes.")

async for event in result.stream_events():
    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
        print(event.data.delta, end="", flush=True)
```

### Escape hatch
- If the UI only needs the final answer, don’t stream. Streaming adds complexity.

## Sessions / memory (persistence + trimming)

### Default
- Persist history outside the process (DB/storage), and treat each request as **stateless**:
  - Load history for this user/session
  - Trim/prune aggressively (token budget)
  - Run the agent
  - Persist new items/messages back to storage

**Built-in session example (Running agents docs)**

```python
from agents import Agent, Runner, SQLiteSession

agent = Agent(name="Assistant", instructions="Reply very concisely.")
session = SQLiteSession("conversation_123")

result = await Runner.run(agent, "What city is the Golden Gate Bridge in?", session=session)
result = await Runner.run(agent, "What state is it in?", session=session)
```

### Escape hatch
- If you need a drop-in persistent store, use a documented session memory adapter (see extensions in docs map).

## Handoffs (multi-agent routing)

### Default
- Implement a **coordinator** agent that routes to specialists:
  - Coordinator owns intent detection + routing
  - Specialists own domain logic/tools
- Keep tool sets minimal per agent to reduce confusion.
- Pass structured arguments in the handoff payload.

**Default handoff pattern (Quickstart)**

```python
from agents import Agent

history_tutor_agent = Agent(
    name="History Tutor",
    handoff_description="Specialist agent for historical questions",
    instructions="You provide assistance with historical queries. Explain important events and context clearly.",
)
math_tutor_agent = Agent(
    name="Math Tutor",
    handoff_description="Specialist agent for math questions",
    instructions="You provide help with math problems. Explain your reasoning at each step and include examples",
)
triage_agent = Agent(
    name="Triage Agent",
    instructions="You determine which agent to use based on the user's homework question",
    handoffs=[history_tutor_agent, math_tutor_agent],
)
```

### Escape hatch
- If the route depends on safety or compliance checks, apply a guardrail before handoff.

## Guardrails (validation + short-circuit)

### Default
- Use guardrails for:
  - Input validation (e.g., required fields)
  - Authorization boundaries (e.g., user isolation)
  - Output validation when strict structure is required
- Prefer guardrails that can **short-circuit** with an explicit validation report.

**Input guardrail pattern (Quickstart)**

```python
from pydantic import BaseModel
from agents import Agent, GuardrailFunctionOutput, InputGuardrail, Runner

class HomeworkOutput(BaseModel):
    is_homework: bool
    reasoning: str

guardrail_agent = Agent(
    name="Guardrail check",
    instructions="Check if the user is asking about homework.",
    output_type=HomeworkOutput,
)

async def homework_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(HomeworkOutput)
    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=not final_output.is_homework,
    )

triage_agent = Agent(
    name="Triage Agent",
    instructions="Route requests.",
    input_guardrails=[InputGuardrail(guardrail_function=homework_guardrail)],
)
```

### Escape hatch
- If validation is cheap and deterministic, do it inside the tool (in addition to guardrails).

## Tracing (spans + metadata)

### Default
- Enable tracing for all production runs.
- Attach run metadata: `user_id`, `request_id`, `session_id`, and any relevant feature flags.
- Ensure errors are recorded with enough context to reproduce.

**Tracing context manager (Tracing guide)**

```python
from agents import Agent, Runner, trace

agent = Agent(name="Joke generator", instructions="Tell funny jokes.")
with trace("Joke workflow"):
    first_result = await Runner.run(agent, "Tell me a joke")
```

### Escape hatch
- If you need external observability, implement/export via a tracing processor (see tracing API docs).

## MCP integration (consume MCP tools)

### Default (consume MCP servers from an agent)
- Use MCP when you want tools that live outside your process (shared services, data providers).
- Treat MCP tools like any other agent tool, but keep a **hard boundary** between:
  - **Request context** (user/org identifiers, auth, tenancy rules)
  - **Tool invocation** (what the model is allowed to do)
- Default workflow:
  - Identify the MCP server(s) to consume and how the connection is configured (URL/transport, credentials).
  - Fetch or discover the server’s available tools (names + schemas).
  - Register MCP tools with the agent’s toolset.
  - At invocation time, ensure every MCP call includes/derives the correct tenancy context (never cross-tenant).
  - Handle MCP failures gracefully (timeouts, retries, partial degradation).
- Start from the official MCP guide and MCP client utilities:
  - `references/docs-map.md` → Model Context Protocol
  - `references/docs-map.md` → MCP client utilities

**Hosted MCP tool (MCP docs)**

```python
from agents import Agent, HostedMCPTool, Runner

agent = Agent(
    name="Assistant",
    tools=[
        HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "gitmcp",
                "server_url": "https://gitmcp.io/openai/codex",
                "require_approval": "never",
            }
        )
    ],
)
result = await Runner.run(agent, "Which language is this repository written in?")
print(result.final_output)
```

### Practical guardrails (recommended)
- **Namespace tools** by server (avoid collisions). If the SDK supports it, keep tool names stable (e.g., `Calendar.get_events` rather than `get_events`).
- **Allowlist tools** the agent can call (don’t expose an entire MCP catalog unless needed).
- **Validate arguments** before calling MCP (schema validation + required fields).
- **Log and trace** MCP calls (tool name, latency, success/failure, request_id, user_id).

### Escape hatch (hosting)
- If you later need to *host* MCP tools, use:
  - `references/docs-map.md` → MCP server helpers
  - Keep it as a separate concern/skill unless you truly need it here.


