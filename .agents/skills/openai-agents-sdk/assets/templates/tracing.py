"""
Template: tracing.py

Authoritative source: https://openai.github.io/openai-agents-python/tracing/
"""

from __future__ import annotations

import asyncio
import os

from agents import Agent, Runner, set_tracing_export_api_key, trace


def configure_tracing_from_env() -> None:
    """
    Minimal tracing export configuration (example).
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        set_tracing_export_api_key(api_key)


async def demo() -> None:
    configure_tracing_from_env()
    agent = Agent(name="Joke generator", instructions="Tell funny jokes.")
    with trace("Joke workflow"):
        first_result = await Runner.run(agent, "Tell me a joke")
        second_result = await Runner.run(agent, f"Rate this joke: {first_result.final_output}")
        print(f"Joke: {first_result.final_output}")
        print(f"Rating: {second_result.final_output}")


if __name__ == "__main__":
    asyncio.run(demo())


