"""
Template: example_router.py

Minimal end-to-end example: define an agent and expose it via create_agent_router().

Steps to adapt this for your own agent:
1. Replace `example_agent` with your actual Agent definition.
2. Change `prefix` and `agent_name` to match your domain.
3. In main.py: `from .routers.example import router as example_router`
               `app.include_router(example_router)`

Required .env:
    OPENAI_API_KEY=sk-...
    ENABLE_SESSIONS=true          # optional, default true
    SESSION_DB_PATH=./sessions.db # optional
"""

from __future__ import annotations

from agents import Agent, function_tool
from fastapi import APIRouter

from .router_factory import create_agent_router


# ---------------------------------------------------------------------------
# 1. Define your tools
# ---------------------------------------------------------------------------

@function_tool
def get_menu() -> str:
    """Return the current restaurant menu."""
    return (
        "Today's menu:\n"
        "- Margherita Pizza  $12\n"
        "- Caesar Salad      $8\n"
        "- Grilled Chicken   $15\n"
        "- Chocolate Cake    $6\n"
    )


@function_tool
def place_order(item: str, quantity: int) -> str:
    """
    Place an order for the given menu item.

    Args:
        item:     Name of the menu item to order.
        quantity: Number of units to order.
    """
    return f"Order confirmed: {quantity}x {item}. Your order will be ready in 20 minutes."


# ---------------------------------------------------------------------------
# 2. Define the agent
# ---------------------------------------------------------------------------

example_agent = Agent(
    name="Restaurant Order Bot",
    model="gpt-4.1-mini",
    instructions=(
        "You are a friendly restaurant order assistant. "
        "Help customers browse the menu and place orders. "
        "Always confirm the full order before placing it. "
        "Use get_menu to show available items and place_order when the customer is ready."
    ),
    tools=[get_menu, place_order],
)

# ---------------------------------------------------------------------------
# 3. Create the router (all 5 endpoints generated automatically)
# ---------------------------------------------------------------------------

router: APIRouter = create_agent_router(
    agent=example_agent,
    prefix="/orders",
    agent_name="Restaurant Order Bot",
)

# ---------------------------------------------------------------------------
# Resulting endpoints:
#   POST   /orders/run
#   POST   /orders/stream
#   GET    /orders/session/{session_id}
#   DELETE /orders/session/{session_id}
#   GET    /orders/info
# ---------------------------------------------------------------------------
