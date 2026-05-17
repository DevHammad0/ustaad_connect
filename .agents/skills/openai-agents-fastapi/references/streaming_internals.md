# SDK Streaming Internals

Read this when you need to handle raw SDK events inside your own streaming logic — i.e., you are writing a custom streaming loop rather than using the `router_factory.py` template.

If you are using `create_agent_router()` from the template, you do not need this file — event mapping is already handled for you.

---

## Raw SDK Event Types

These are emitted by `result.stream_events()` from `Runner.run_streamed()`.
They are distinct from the custom SSE events your router sends to clients (see `sse_events.md`).

| `event.type` | Class | Key fields | Use |
|---|---|---|---|
| `raw_response_event` | `RawResponsesStreamEvent` | `event.data` → `ResponseTextDeltaEvent` or `ResponseContentPartDoneEvent` | Token streaming |
| `run_item_stream_event` | `RunItemStreamEvent` | `event.item.type` → `"tool_call_item"`, `"tool_call_output_item"`, `"message_output_item"`, `"handoff_call_item"` | Structured items |
| `agent_updated_stream_event` | `AgentUpdatedStreamEvent` | `event.new_agent` | Handoff detection |

## Minimal Custom Streaming Loop

```python
from openai.types.responses import ResponseTextDeltaEvent
from agents import RawResponsesStreamEvent, RunItemStreamEvent

result = Runner.run_streamed(agent, input="hello")
async for event in result.stream_events():
    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
        print(event.data.delta, end="", flush=True)
    elif event.type == "run_item_stream_event":
        if event.item.type == "tool_call_item":
            print(f"\n[tool] {event.item.raw_item.name}")
        elif event.item.type == "tool_call_output_item":
            print(f"\n[tool output] {event.item.output}")
        elif event.item.type == "message_output_item":
            print(f"\n[message complete]")
    elif event.type == "agent_updated_stream_event":
        print(f"\n[handoff -> {event.new_agent.name}]")
```

## Mapping SDK Events to Custom SSE Events

If you are building your own event mapper (the template's `router_factory.py` already does this), the mapping is:

| SDK event | Custom SSE type |
|---|---|
| `raw_response_event` + `ResponseTextDeltaEvent` | `text_delta` |
| `run_item_stream_event` + `tool_call_item` | `tool_call` |
| `run_item_stream_event` + `tool_call_output_item` | `tool_result` |
| `run_item_stream_event` + `message_output_item` | `message_complete` |
| `run_item_stream_event` + `handoff_call_item` | `handoff` |
| `agent_updated_stream_event` | `agent_updated` |
| end of stream | `stream_complete` (include final usage stats) |
| exception | `error` |
