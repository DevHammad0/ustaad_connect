"""
Template: tools.py

Authoritative source: https://openai.github.io/openai-agents-python/tools/
"""

from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict

from agents import RunContextWrapper, FunctionTool, function_tool


class Location(TypedDict):
    lat: float
    long: float


@function_tool
async def fetch_weather(location: Location) -> str:
    """Fetch the weather for a given location."""
    # In real life, fetch from an API
    return "sunny"


@function_tool(name_override="fetch_data")
def read_file(ctx: RunContextWrapper[Any], path: str, directory: str | None = None) -> str:
    """Read the contents of a file."""
    # In real life, read from storage using ctx (authZ/tenancy checks)
    return "<file contents>"


def make_manual_function_tool() -> FunctionTool:
    """
    Manual tool registration example (Tools docs).
    """
    from pydantic import BaseModel

    class FunctionArgs(BaseModel):
        username: str
        age: int

    def do_some_work(data: str) -> str:
        return "done"

    async def run_function(ctx: RunContextWrapper[Any], args: str) -> str:
        parsed = FunctionArgs.model_validate_json(args)
        return do_some_work(data=f"{parsed.username} is {parsed.age} years old")

    return FunctionTool(
        name="process_user",
        description="Processes extracted user data",
        params_json_schema=FunctionArgs.model_json_schema(),
        on_invoke_tool=run_function,
    )


