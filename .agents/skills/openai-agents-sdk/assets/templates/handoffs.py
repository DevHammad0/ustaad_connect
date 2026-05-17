"""
Template: handoffs.py

Authoritative sources:
- https://openai.github.io/openai-agents-python/quickstart/
- https://openai.github.io/openai-agents-python/agents/
"""

from __future__ import annotations

from agents import Agent


def build_triage_agent() -> Agent:
    booking_agent = Agent(name="Booking agent", instructions="Handle booking questions and requests.")
    refund_agent = Agent(name="Refund agent", instructions="Handle refund questions and requests.")

    triage_agent = Agent(
        name="Triage agent",
        instructions=(
            "Help the user with their questions. "
            "If they ask about booking, hand off to the booking agent. "
            "If they ask about refunds, hand off to the refund agent."
        ),
        handoffs=[booking_agent, refund_agent],
    )

    return triage_agent


def build_orchestrator_using_agents_as_tools() -> Agent:
    spanish_agent = Agent(name="Spanish agent", instructions="You translate the user's message to Spanish")
    french_agent = Agent(name="French agent", instructions="You translate the user's message to French")

    orchestrator_agent = Agent(
        name="orchestrator_agent",
        instructions=(
            "You are a translation agent. You use the tools given to you to translate."
            "If asked for multiple translations, you call the relevant tools."
        ),
        tools=[
            spanish_agent.as_tool(
                tool_name="translate_to_spanish",
                tool_description="Translate the user's message to Spanish",
            ),
            french_agent.as_tool(
                tool_name="translate_to_french",
                tool_description="Translate the user's message to French",
            ),
        ],
    )
    return orchestrator_agent


