"""
routes/customer.py — Customer-facing endpoints.

Endpoints:
  POST /api/customer/chat              → AI agent conversation
  POST /api/customer/bookings/{id}/rate → Star rating after job completion
"""

from __future__ import annotations

import logging
import os
from typing import Annotated

from agents import Runner
from agents.extensions.memory import RedisSession
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from upstash_redis.asyncio import Redis as UpstashRedis


# ---------------------------------------------------------------------------
# Upstash → redis-py pipeline compatibility adapter
# ---------------------------------------------------------------------------

class _CompatiblePipeline:
    """Wraps an Upstash AsyncPipeline to expose the redis-py `.execute()` API."""

    def __init__(self, pipe) -> None:
        self._pipe = pipe

    def __getattr__(self, name: str):
        return getattr(self._pipe, name)

    async def execute(self) -> list:
        return await self._pipe.exec()


class _CompatibleRedis(UpstashRedis):
    """Upstash async Redis client whose `.pipeline()` returns a redis-py-compatible wrapper."""

    def pipeline(self):
        return _CompatiblePipeline(super().pipeline())


class UstaadRedisSession(RedisSession):
    """RedisSession subclass that removes default key prefixes and stores history directly under the phone number."""

    def __init__(self, session_id: str, *args, **kwargs) -> None:
        super().__init__(session_id, *args, **kwargs)
        # The Agents SDK uses `_session_key` for its internal INCR message counter
        # and `_messages_key` for the actual List of messages.
        # We swap them here so the exact phone number is the List of messages.
        self._session_key = f"{session_id}:counter"
        self._messages_key = session_id

from src.api.agent import ustaad_agent
from src.api.database import get_session, get_booking_with_relations, submit_rating
from src.api.geocoding import reverse_geocode_city
from src.api.models import (
    BookingRatingRequest,
    BookingStatus,
    BookingStatusResponse,
    CustomerChatRequest,
    CustomerChatResponse,
    ErrorResponse,
)

load_dotenv()

logger = logging.getLogger(__name__)

APP_SECRET: str = os.environ["APP_SECRET"]

# Async Upstash Redis client — full conversation history stored via RedisSession
_redis = _CompatibleRedis.from_env()
CONV_TTL = 10800  # 3 hours

router = APIRouter(prefix="/api/customer", tags=["customer"])


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def verify_app_secret(x_app_secret: Annotated[str | None, Header()] = None) -> None:
    """Validates the X-App-Secret header on every request."""
    if x_app_secret != APP_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing X-App-Secret header.")


AppSecretDep = Annotated[None, Depends(verify_app_secret)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# POST /api/customer/chat
# ---------------------------------------------------------------------------


@router.post(
    "/chat",
    response_model=CustomerChatResponse,
    responses={401: {"model": ErrorResponse}},
)
async def customer_chat(
    body: CustomerChatRequest,
    _: AppSecretDep,
    session: SessionDep,
) -> CustomerChatResponse:
    """
    Main WhatsApp chat endpoint. Passes the customer message to the Ustaad Agent.

    If lat/lng are provided (customer shared location), the city is resolved and
    injected as a system context note before running the agent.
    """
    session_id = f"session:{body.phone}"

    # Build the input message
    user_message = body.message

    # If GPS coordinates are provided, prepend a system context note
    if body.lat is not None and body.lng is not None:
        location_data = await reverse_geocode_city(body.lat, body.lng)
        city_slug = location_data.get("slug")
        full_address = location_data.get("address")
        
        city_label = city_slug or "unknown"
        address_label = full_address or "unknown"
        
        location_note = (
            f"[SYSTEM: Location received — "
            f"Lat: {body.lat}, Lng: {body.lng}, Full Address: {address_label}, "
            f"City Database Filter: {city_label}]"
        )
        user_message = f"{location_note}\n\n{body.message}".strip()
        logger.info("GPS received: lat=%s, lng=%s, city_slug=%s", body.lat, body.lng, city_label)

    # Dynamically inject customer phone number and message type into input
    system_info = f"[System Info: Customer Phone is {body.phone}, Message Type is api]"
    user_message = f"{user_message}\n\n{system_info}"

    # Per-customer RedisSession — full history stored in Upstash, rolling 3-hour TTL
    agent_session = UstaadRedisSession(
        session_id=body.phone,
        redis_client=_redis,
        ttl=CONV_TTL,
    )

    result = await Runner.run(
        ustaad_agent,
        input=user_message,
        session=agent_session,
        context={"phone": body.phone},
    )

    reply = result.final_output or "Maafi chahta hoon, kuch masla aa gaya. Dobara try karein."
    return CustomerChatResponse(reply=reply, session_id=f"session:{body.phone}")


# ---------------------------------------------------------------------------
# POST /api/customer/bookings/{booking_id}/rate
# ---------------------------------------------------------------------------


@router.post(
    "/bookings/{booking_id}/rate",
    response_model=BookingStatusResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def rate_booking(
    booking_id: int,
    body: BookingRatingRequest,
    _: AppSecretDep,
    session: SessionDep,
) -> BookingStatusResponse:
    """
    Customer submits a star rating (1–5) after job completion.
    Double-rating is blocked — only one rating per booking allowed.
    """
    try:
        booking = await get_booking_with_relations(session, booking_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Booking #{booking_id} not found.")

    if booking.status != BookingStatus.completed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot rate a booking with status '{booking.status.value}'. Only completed bookings can be rated.",
        )

    if booking.customer_rating is not None:
        raise HTTPException(
            status_code=400,
            detail="You have already submitted a rating for this booking.",
        )

    await submit_rating(session, booking_id, body.rating, body.review)

    return BookingStatusResponse(
        booking_id=booking_id,
        status=BookingStatus.completed,
        whatsapp_sent=False,  # No WhatsApp needed for rating confirmation
    )
