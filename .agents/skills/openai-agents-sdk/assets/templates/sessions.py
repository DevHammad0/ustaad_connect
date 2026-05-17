"""
Template: sessions.py

Authoritative source: https://openai.github.io/openai-agents-python/running_agents/
"""

from __future__ import annotations

import asyncio

from agents import Agent, Runner, SQLiteSession


async def run_with_sqlite_session() -> None:
    agent = Agent(name="Assistant", instructions="Reply very concisely.")

    # Create a persistent session instance
    session = SQLiteSession("conversation_123")

    # First turn
    result = await Runner.run(agent, "What city is the Golden Gate Bridge in?", session=session)
    print(result.final_output)

    # Second turn - agent automatically remembers previous context
    result = await Runner.run(agent, "What state is it in?", session=session)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(run_with_sqlite_session())


