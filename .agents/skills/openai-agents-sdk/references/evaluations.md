---
# Evaluations (E1–E5)

These are **representative user requests** this Skill should support. Use them to validate the Skill and iterate on `SKILL.md`, `references/`, and `assets/templates/`.

## E1 — Single agent + 2 tools

**Prompt**

Build an OpenAI Agents SDK (Python) agent named `TodoAssistant` with two tools:
- `add_todo(title: str) -> str`
- `list_todos() -> list[str]`

The agent should ask clarifying questions only when needed, and return a structured final answer with:
- `action_taken`
- `todos` (latest list)
- `notes`

**Expected behavior**
- Uses a single default agent pattern (no unnecessary frameworks).
- Implements tools as structured tools (argument schema included).
- Runs the agent once with a sample input and shows how to call it from code.
- Mentions where to configure model/settings (without hardcoding secrets).

## E2 — Streaming

**Prompt**

Run the agent with streaming enabled and show how to:
- stream partial model output
- stream tool-call progress
- collect the final result at the end

**Expected behavior**
- Uses the SDK’s streaming primitives/events (per official docs).
- Demonstrates a clean “stream events → render → finalize” loop.
- Mentions how to handle cancellations/timeouts/retries at a high level.

## E3 — Sessions / memory

**Prompt**

Persist conversation history across runs. Add a minimal session/memory approach that:
- stores messages between runs
- trims/prunes history to avoid prompt bloat
- rehydrates context for the next run

**Expected behavior**
- Uses the SDK’s recommended session/memory approach (per official docs).
- Avoids holding global mutable state on the server (stateless request pattern).
- Mentions retention policy and user isolation as design considerations.

## E4 — Handoffs (multi-agent)

**Prompt**

Create a coordinator agent that can hand off to two specialists:
- `TodoWriter` (create/update todos)
- `TodoReporter` (summaries/metrics)

Show how handoff routing works and how arguments are passed safely.

**Expected behavior**
- Uses the SDK’s handoff pattern as the default.
- Clearly scopes responsibilities and avoids tool duplication.
- Includes error handling for failed or invalid handoffs.

## E5 — Guardrails + tracing

**Prompt**

Add guardrails so the agent:
- rejects requests that attempt to access another user’s data
- validates tool inputs (e.g., todo title non-empty)

Also enable tracing and show how to inspect traces/spans for a run.

**Expected behavior**
- Guardrails can short-circuit runs with a clear validation report.
- Tracing is enabled and includes useful metadata (user_id, request_id).
- Demonstrates where to plug in custom processors/exporters (if needed).


