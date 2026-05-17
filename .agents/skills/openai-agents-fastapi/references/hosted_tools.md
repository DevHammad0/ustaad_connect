# Hosted Tools Reference

Read this when your agent needs server-side tools that run on OpenAI's infrastructure —
web search, file/vector-store search, or code execution. These attach to `Agent(tools=[...])`
with no `@function_tool` decorator and no local execution.

---

## Web Search

```python
from agents import Agent, WebSearchTool

agent = Agent(
    name="Researcher",
    tools=[
        WebSearchTool(
            user_location={"type": "approximate", "city": "New York"},
        )
    ],
)
```

Optional: `search_context_size` (`"low"` | `"medium"` | `"high"`) controls how much web content
is included in the model's context per search call.

---

## File Search (Vector Store)

```python
from agents import Agent, FileSearchTool

agent = Agent(
    name="Doc QA",
    tools=[
        FileSearchTool(
            max_num_results=3,
            vector_store_ids=["vs_abc123"],
            include_search_results=True,   # include raw chunks in tool output
        )
    ],
)
```

Create vector stores and upload files via the OpenAI Files API before referencing them here.

---

## Code Interpreter

```python
from agents import Agent, CodeInterpreterTool

agent = Agent(
    name="Calculator",
    model="gpt-4.1",
    tools=[
        CodeInterpreterTool(
            tool_config={"type": "code_interpreter", "container": {"type": "auto"}},
        )
    ],
)
```

Note: streaming with Code Interpreter requires org verification for `gpt-5`-class models.
For `gpt-4.1` and below, streaming works without special access.

---

## Combining with FastAPI

Hosted tools attach at `Agent` construction time and work transparently with
`create_agent_router()` — no changes to the router or streaming logic are needed.
The tool calls appear as `tool_call` / `tool_result` SSE events in the stream.
