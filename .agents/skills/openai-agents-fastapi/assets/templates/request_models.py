"""
Template: request_models.py

Pydantic models for request/response shapes used by create_agent_router().
Copy this file into your project (e.g. src/api/models.py) and import from there.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request body for /run and /stream endpoints."""

    input: str | list = Field(
        ...,
        description="User message (string) or structured input list",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier for multi-turn memory. Omit for stateless runs.",
    )
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional extra context passed to the agent run (not conversation history).",
    )


class AgentResponse(BaseModel):
    """Response body for the synchronous /run endpoint."""

    output: Any = Field(..., description="Final agent output (string or structured)")
    success: bool = Field(..., description="Whether the run completed without error")
    usage: dict[str, int] = Field(
        default_factory=dict,
        description="Token counts: input_tokens, output_tokens, total_tokens",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Echo of the session_id used, if sessions are enabled",
    )


class SessionMessagesResponse(BaseModel):
    """Response for GET /session/{session_id}."""

    session_id: str
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered list of conversation items stored in the session",
    )
    count: int = Field(..., description="Number of items returned")


class AgentInfo(BaseModel):
    """Static metadata about an agent, returned by GET /info."""

    name: str
    model: str
    tools: list[str] = Field(
        default_factory=list,
        description="Names of tools available to this agent",
    )
    handoffs: list[str] = Field(
        default_factory=list,
        description="Names of agents this agent can hand off to",
    )
    endpoints: list[str] = Field(
        default_factory=list,
        description="Available HTTP endpoints for this router",
    )
    sessions_enabled: bool = Field(
        default=False,
        description="Whether session memory is enabled for this deployment",
    )
