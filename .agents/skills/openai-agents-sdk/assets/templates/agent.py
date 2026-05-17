"""
Template: agent.py

Authoritative source: https://openai.github.io/openai-agents-python/quickstart/
"""

from __future__ import annotations

from agents import Agent


def build_basic_agent(*, name: str = "Assistant", instructions: str) -> Agent:
    """
    Minimal agent constructor.
    """
    return Agent(name=name, instructions=instructions)


def build_triage_agent() -> Agent:
    """
    Multi-agent handoff example (Quickstart).
    """
    history_tutor_agent = Agent(
        name="History Tutor",
        handoff_description="Specialist agent for historical questions",
        instructions="You provide assistance with historical queries. Explain important events and context clearly.",
    )
    math_tutor_agent = Agent(
        name="Math Tutor",
        handoff_description="Specialist agent for math questions",
        instructions="You provide help with math problems. Explain your reasoning at each step and include examples",
    )
    triage_agent = Agent(
        name="Triage Agent",
        instructions="You determine which agent to use based on the user's homework question",
        handoffs=[history_tutor_agent, math_tutor_agent],
    )
    return triage_agent


