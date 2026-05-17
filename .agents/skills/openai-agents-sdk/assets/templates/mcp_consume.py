"""
Template: mcp_consume.py

Goal: consume MCP tools from an agent (Phase 3).

Authoritative source: https://openai.github.io/openai-agents-python/mcp/
"""

from __future__ import annotations

import asyncio
import os

from agents import Agent, HostedMCPTool, Runner
from agents.mcp import MCPServerStreamableHttp
from agents.model_settings import ModelSettings


async def consume_hosted_mcp_tool() -> None:
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


async def consume_streamable_http_server() -> None:
    token = os.environ["MCP_SERVER_TOKEN"]
    async with MCPServerStreamableHttp(
        name="Streamable HTTP Python Server",
        params={
            "url": "http://localhost:8000/mcp",
            "headers": {"Authorization": f"Bearer {token}"},
            "timeout": 10,
        },
        cache_tools_list=True,
        max_retry_attempts=3,
    ) as server:
        agent = Agent(
            name="Assistant",
            instructions="Use the MCP tools to answer the questions.",
            mcp_servers=[server],
            model_settings=ModelSettings(tool_choice="required"),
        )
        result = await Runner.run(agent, "Add 7 and 22.")
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(consume_hosted_mcp_tool())


