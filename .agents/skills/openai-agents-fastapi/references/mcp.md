# MCP Integration Reference

Read this when attaching MCP (Model Context Protocol) servers to an agent in a FastAPI deployment.
The key constraint is lifecycle management: MCP servers must be started once at app startup
(in `lifespan`), not per-request.

---

## The Lifecycle Rule

`MCPServerStdio` and `MCPServerStreamableHttp` are async context managers that manage
a subprocess or HTTP connection. Opening one per request spawns a new process every call —
slow and leaky. The right pattern:

```python
# main.py — start once, share across all requests
from contextlib import asynccontextmanager
from agents.mcp import MCPServerStdio

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with MCPServerStdio(
        name="Filesystem",
        params={"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/root"]},
        cache_tools_list=True,
    ) as mcp_server:
        app.state.mcp_fs = mcp_server
        yield
```

Then in each router, build the agent per-request using the already-running server:

```python
# router
def _build_agent(request: Request) -> Agent:
    return Agent(
        name="File Assistant",
        model="gpt-4.1",
        mcp_servers=[request.app.state.mcp_fs],
    )
```

Agent construction is cheap (no subprocess). The subprocess started at lifespan time.

---

## Transport Types

### 1. Stdio (local subprocess — filesystem, git, etc.)

```python
from agents.mcp import MCPServerStdio

async with MCPServerStdio(
    name="Filesystem",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
    },
    cache_tools_list=True,
) as server:
    agent = Agent(name="Assistant", mcp_servers=[server])
```

Windows note: use `"command": "npx.cmd"` instead of `"npx"`.

### 2. Streamable HTTP (self-hosted, recommended for production)

```python
from agents.mcp import MCPServerStreamableHttp

async with MCPServerStreamableHttp(
    name="My MCP Server",
    params={
        "url": "http://localhost:8001/mcp",
        "headers": {"Authorization": "Bearer token"},
    },
    cache_tools_list=True,
    max_retry_attempts=3,
) as server:
    agent = Agent(name="Assistant", mcp_servers=[server])
```

### 3. Hosted MCP (OpenAI-managed, zero infra)

```python
from agents import Agent, HostedMCPTool

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
```

Hosted MCP attaches via `tools=[]` (not `mcp_servers=[]`) and needs no lifecycle management.

### 4. SSE transport (legacy)

```python
from agents.mcp import MCPServerSse

async with MCPServerSse(
    name="Legacy Server",
    params={"url": "http://localhost:8001/sse"},
) as server:
    agent = Agent(name="Assistant", mcp_servers=[server])
```

---

## Tool Filtering

Restrict which MCP tools the agent can see:

```python
from agents.mcp import create_static_tool_filter

server = MCPServerStreamableHttp(
    params={"url": "http://localhost:8001/mcp"},
    tool_filter=create_static_tool_filter(allowed_tool_names=["read_file", "list_directory"]),
)
```

For dynamic filtering (per-request), pass a callable:

```python
server = MCPServerStreamableHttp(
    params={"url": "http://localhost:8001/mcp"},
    tool_filter=lambda ctx, tools: [t for t in tools if not t.name.startswith("write_")],
)
```

---

## With `create_agent_router()`

MCP servers wire in at agent construction. If your agent is fixed (same tools for all requests),
build it once:

```python
# At module level, after lifespan starts app.state.mcp_fs
from agents import Agent

def make_router(app: FastAPI) -> APIRouter:
    agent = Agent(name="File Agent", mcp_servers=[app.state.mcp_fs])
    return create_agent_router(agent, prefix="/files", agent_name="File Agent")
```

If the agent changes per-request (e.g., different tools based on user role), override the
`run` and `stream` endpoints in the router factory — see `patterns.md` for that pattern.

---

## Full Docs

https://openai.github.io/openai-agents-python/mcp/
