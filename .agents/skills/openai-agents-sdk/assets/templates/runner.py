"""
Template: runner.py

Authoritative sources:
- https://openai.github.io/openai-agents-python/running_agents/
- https://openai.github.io/openai-agents-python/streaming/
"""

from __future__ import annotations

import asyncio

from openai.types.responses import ResponseTextDeltaEvent

from agents import Agent, ItemHelpers, Runner, function_tool


async def run_basic() -> None:
    agent = Agent(name="Assistant", instructions="You are a helpful assistant")
    result = await Runner.run(agent, "Write a haiku about recursion in programming.")
    print(result.final_output)


async def run_multi_turn() -> None:
    agent = Agent(name="Assistant", instructions="Reply very concisely.")
    result = await Runner.run(agent, "What city is the Golden Gate Bridge in?")
    new_input = result.to_input_list() + [{"role": "user", "content": "What state is it in?"}]
    result = await Runner.run(agent, new_input)
    print(result.final_output)


async def run_stream_text_deltas() -> None:
    agent = Agent(name="Joker", instructions="You are a helpful assistant.")
    result = Runner.run_streamed(agent, input="Please tell me 5 jokes.")
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)


@function_tool
def how_many_jokes() -> int:
    return 5


async def run_stream_structured_events() -> None:
    agent = Agent(
        name="Joker",
        instructions="First call the `how_many_jokes` tool, then tell that many jokes.",
        tools=[how_many_jokes],
    )
    result = Runner.run_streamed(agent, input="Hello")
    async for event in result.stream_events():
        if event.type == "raw_response_event":
            continue
        if event.type == "agent_updated_stream_event":
            print(f"Agent updated: {event.new_agent.name}")
        elif event.type == "run_item_stream_event":
            if event.item.type == "tool_call_item":
                print("-- Tool was called")
            elif event.item.type == "tool_call_output_item":
                print(f\"-- Tool output: {event.item.output}\")
            elif event.item.type == "message_output_item":
                print(f\"-- Message output:\\n {ItemHelpers.text_message_output(event.item)}\")


if __name__ == "__main__":
    asyncio.run(run_basic())


