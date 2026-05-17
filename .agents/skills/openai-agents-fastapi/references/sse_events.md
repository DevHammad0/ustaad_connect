# SSE Event Format Reference

The `/stream` endpoint emits Server-Sent Events (SSE). Each event is a line of the form:

```
data: {"type": "...", ...}\n\n
```

The client reads these as a stream and handles each `type` value.

---

## Event Types

### `text_delta`
Fired for every token of LLM text output. Use to update a streaming text display.

```json
{
  "type": "text_delta",
  "delta": "Hello"
}
```

Accumulate `delta` values to reconstruct the full response text.

---

### `tool_call`
Fired when the agent decides to invoke a tool. Use to show a "thinking…" or "using tool X" indicator.

```json
{
  "type": "tool_call",
  "tool_name": "get_menu",
  "call_id": "call_abc123"
}
```

---

### `tool_result`
Fired when a tool returns a value. Optional to display — useful for debugging or showing intermediate results.

```json
{
  "type": "tool_result",
  "call_id": "call_abc123",
  "output": "Today's menu:\n- Margherita Pizza $12\n..."
}
```

---

### `message_complete`
Fired when a full LLM message item is done (after all deltas for that turn). Contains the complete text. Use this if you prefer to wait for the full message rather than streaming deltas.

```json
{
  "type": "message_complete",
  "text": "Here is today's menu:\n- Margherita Pizza $12\n..."
}
```

---

### `handoff`
Fired when the active agent hands off to a specialist agent.

```json
{
  "type": "handoff",
  "target_agent": "Payment Agent"
}
```

---

### `agent_updated`
Fired when the SDK switches the active agent (e.g. after a handoff completes).

```json
{
  "type": "agent_updated",
  "agent_name": "Payment Agent"
}
```

---

### `stream_complete`
The final event — always emitted after the run finishes successfully. Contains token usage and echoes the `session_id`.

```json
{
  "type": "stream_complete",
  "usage": {
    "input_tokens": 312,
    "output_tokens": 87,
    "total_tokens": 399
  },
  "session_id": "user-14155551234"
}
```

After receiving this event, close the connection.

---

### `error`
Emitted if an exception occurs during the streaming run. The stream ends after this event.

```json
{
  "type": "error",
  "message": "OpenAI API rate limit exceeded"
}
```

---

## Client-Side Handling (JavaScript)

```javascript
const response = await fetch("/orders/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ input: userMessage, session_id: sessionId }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
let fullText = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n\n");
  buffer = lines.pop(); // keep incomplete chunk

  for (const line of lines) {
    if (!line.startsWith("data: ")) continue;
    const event = JSON.parse(line.slice(6));

    switch (event.type) {
      case "text_delta":
        fullText += event.delta;
        updateUI(fullText);
        break;
      case "tool_call":
        showThinkingIndicator(event.tool_name);
        break;
      case "tool_result":
        hideThinkingIndicator();
        break;
      case "message_complete":
        // Optional: use instead of streaming deltas
        break;
      case "handoff":
        updateAgentName(event.target_agent);
        break;
      case "stream_complete":
        logUsage(event.usage);
        break;
      case "error":
        showError(event.message);
        break;
    }
  }
}
```

---

## Client-Side Handling (Python / httpx)

```python
import httpx
import json

async def stream_agent(message: str, session_id: str):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/orders/stream",
            json={"input": message, "session_id": session_id},
        ) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event["type"] == "text_delta":
                    print(event["delta"], end="", flush=True)
                elif event["type"] == "stream_complete":
                    break
                elif event["type"] == "error":
                    raise RuntimeError(event["message"])
```

---

## Notes

- Events not listed above (e.g. raw SDK events with `"raw": true`) can be ignored on the client.
- The SSE stream always ends with either `stream_complete` or `error` — never silently.
- `session_id` in `stream_complete` is `null` when no session was used (stateless run).
- Token counts in `usage` reflect the full run, including all tool calls and handoffs.
