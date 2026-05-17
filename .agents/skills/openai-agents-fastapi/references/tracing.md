# Tracing Reference

Read this when you need to add observability to your FastAPI agent backend —
grouping multi-turn conversations into traces, disabling tracing per-run, or
sending traces to a custom processor.

Traces are sent to OpenAI's platform by default whenever `OPENAI_API_KEY` is set.
No extra setup is needed for basic tracing — it's on by default.

---

## Wrap a Workflow in a Named Trace

Group related runs (e.g., a pipeline) under one named trace:

```python
from agents import Runner, trace

with trace("Order processing pipeline"):
    availability = await Runner.run(agent, "Check stock for item X")
    result = await Runner.run(agent, f"Place order: {availability.final_output}")
```

---

## Group Multi-Turn Conversations

Tie all turns from one conversation into a single trace using `group_id`:

```python
import uuid
from agents import Runner, trace

# At conversation start — store this per session_id
conversation_id = uuid.uuid4().hex[:16]

# Each turn
with trace("User turn", group_id=conversation_id):
    result = await Runner.run(agent, user_input)
```

This is the recommended pattern for chat-style FastAPI endpoints. Store `conversation_id`
alongside your `session_id`.

---

## FastAPI Background Tasks

Background tasks exit before traces flush. Always call `flush_traces()` in a `finally` block:

```python
from agents import Runner, trace, flush_traces

def process_async_job(prompt: str):
    try:
        with trace("background_job"):
            Runner.run_sync(agent, prompt)
    finally:
        flush_traces()
```

---

## Disable Tracing Per-Run

```python
from agents import Runner, RunConfig

result = await Runner.run(
    agent,
    "hello",
    run_config=RunConfig(tracing_disabled=True),
)
```

---

## Disable Tracing Globally

```python
from agents import set_tracing_disabled

set_tracing_disabled(True)
```

Or set `OPENAI_AGENTS_DISABLE_TRACING=1` in the environment.

---

## Custom Trace Processor

Send traces to your own backend (e.g., Langfuse, Datadog):

```python
from agents import add_trace_processor, set_trace_processors

# Add alongside the default OpenAI processor
add_trace_processor(my_custom_processor)

# Replace all processors
set_trace_processors([my_custom_processor])
```

---

## Key Functions

`trace()`, `flush_traces()`, `add_trace_processor()`, `set_trace_processors()`,
`set_tracing_export_api_key()`, `set_tracing_disabled()`
