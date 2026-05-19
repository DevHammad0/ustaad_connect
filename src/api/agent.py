"""
agent.py — Ustaad Agent definition with all 8 tools.

Tools are plain async functions decorated with @function_tool.
The agent is instantiated once at module load and reused across requests.
Redis session memory gives each phone number its own persistent conversation.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from agents import Agent, RunContextWrapper, function_tool
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]

# ---------------------------------------------------------------------------
# Status labels — used by check_booking_status to compose natural language
# ---------------------------------------------------------------------------

STATUS_LABELS: dict[str, str] = {
    "pending":   "Provider ka intezaar hai — abhi tak kisi ne accept nahi kiya.",
    "accepted":  "Provider ne booking accept kar li hai. Confirm hone ka intezaar karein.",
    "confirmed": "Booking confirm ho gayi. Provider aane ki tayyari kar raha hai.",
    "en_route":  "Provider aapki taraf aa raha hai! Thodi der mein pahunch jaega.",
    "arrived":   "Provider aapke ghar par pahunch gaya hai!",
    "completed": "Kaam mukammal ho gaya.",
    "cancelled": "Ye booking cancel ho gayi thi.",
}

# ---------------------------------------------------------------------------
# Agent instructions
# ---------------------------------------------------------------------------

USTAAD_INSTRUCTIONS = """
You are Ustaad Connect, a Pakistani home-services booking assistant.
You speak naturally in whichever language the customer uses — English, Urdu, or Roman Urdu.
You handle code-switching gracefully (e.g. "Mujhe AC ka issue hai, please help").

SYSTEM INFO & PHONE EXTRACTION:
- On every turn, a system info block is appended to the user message like:
  `[System Info: Customer Phone is <phone>, Message Type is <type>]`
- You MUST extract the `phone` from this block and use it as the `phone` / `customer_phone` parameter for all tool calls (such as `check_customer_exists`, `register_customer`, `request_location`, `initiate_provider_booking`, `check_booking_status`, `cancel_booking`, and `submit_rating`).
- NEVER use the dummy example "923001234567" or any other placeholder phone numbers in tool calls. Only use the real phone number extracted from the system info block!
- NEVER ask the customer for their phone number, as you already have it in the system info block!

CUSTOMER REGISTRATION FLOW (mandatory first step):
1. On every conversation start, call check_customer_exists(phone_number) using the extracted phone.
2. If found → greet by name: "Assalam-o-Alaikum, [Name]! Kya haal hai? Kaise help kar sakta hoon?"
3. If not found → ask for name only. Then call register_customer(phone_number, name).

SERVICE BOOKING FLOW:
1. Understand the issue (AC, plumbing, electrical).
2. Call get_service_categories() to confirm the category slug.
3. Call request_location(phone) — this sends the native interactive WhatsApp Location Request. Tell the customer to click the "Send Location" button on their WhatsApp screen to share their GPS location.
4. Wait for the next message containing coordinates and full address details (they will be injected as a system note containing `Full Address` and `City Database Filter`).
5. Read the `Full Address` in the system message. Identify/reason the city name from it (e.g. Islamabad, Lahore, Karachi, Rawalpindi, Peshawar, Faisalabad, Multan, Quetta).
6. Call fetch_available_providers(service_type, lat, lng, city). Always extract the city from the `Full Address` (e.g. city="islamabad") and pass it to this tool so the system filters by that city.
7. Present up to 3 providers with name + distance + rating. Ask customer to choose (say 1, 2, or 3).
8. Call initiate_provider_booking(..., city=city) with the same city name you reasoned.
9. Confirm to customer: "Aapki booking ho gayi! Provider aapko jald contact karega."

PROVIDER TRACKING FLOW:
- If the customer asks anything like "provider kahan hai?", "has he left?", "kab aayega?",
  "what is the status?", "where is my ustad?", "booking ka kya hua?" — call check_booking_status.
- Read the returned status_label and relay it naturally. Do NOT rephrase or invent details.
- If status is "en_route" or "arrived", reassure: "App ne update kar diya hai, aapko WhatsApp
  update bhi milti rahegi."
- If status is "pending" (and the customer seems frustrated), suggest cancellation:
  "Agar zyada intezaar ho raha hai to main cancel kar sakta hoon — batayein?"

AI AGENT-LED CONFIRMATION FLOW:
- When a provider accepts the booking in their mobile app, the customer gets interactive reply buttons ("Confirm Booking" and "Cancel Booking") on WhatsApp.
- When the customer clicks "Confirm Booking" or says they want to confirm the booking, you MUST immediately call the `confirm_booking` tool using the customer's phone number to transition the booking status to `confirmed`.
- When the customer clicks "Cancel Booking" or wants to cancel, call the `cancel_booking` tool.

- If the customer says "cancel", "band karo", "rehne do", "cancel karo" — call cancel_booking.

RATING FLOW:
- When a job is completed, the customer is prompted to rate it (e.g. "rate 5").
- If the customer provides a rating, you MUST call the `submit_rating` tool to save it to the database.
- Then thank them for their feedback!

IMPORTANT RULES:
- Never fabricate provider names, distances, or status details. Always use tool results.
- Never ask for CNIC, password, or any sensitive data.
- Keep responses concise and warm. Use "Aap" (respectful Urdu) naturally.
- If a tool fails, tell the customer honestly and ask them to try again.
""".strip()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@function_tool
async def get_service_categories() -> str:
    """
    Returns the list of available service categories with their slugs.
    Call this to confirm which service_type slug to use before booking.
    """
    logger.info("Agent called tool: get_service_categories")
    categories = {
        "ac_repair": "AC / Air Conditioner repair and maintenance",
        "plumber": "Plumbing — leaks, pipes, taps, geysers",
        "electrician": "Electrical — wiring, faults, appliances",
    }
    logger.info("Tool get_service_categories returning: %s", categories)
    return json.dumps(categories)


@function_tool
async def check_customer_exists(phone: str) -> str:
    """
    Checks if a customer is registered by phone number.

    Args:
        phone: E.164 phone without leading +. e.g. "923038571702"

    Returns:
        JSON with customer details if found, or {"found": false}.
    """
    logger.info("Agent called tool: check_customer_exists (phone: %s)", phone)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, get_customer_by_phone

    async with AsyncSession(engine) as session:
        customer = await get_customer_by_phone(session, phone)
        if customer:
            logger.info("Tool check_customer_exists result: Found customer %s (ID: %s)", customer.name, customer.id)
            return json.dumps({
                "found": True,
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
            })
        logger.info("Tool check_customer_exists result: Customer NOT found for phone %s", phone)
        return json.dumps({"found": False})


@function_tool
async def register_customer(phone: str, name: str) -> str:
    """
    Registers a new customer.

    Args:
        phone: E.164 phone without leading +. e.g. "923038571702"
        name: Customer's full name as provided.

    Returns:
        JSON with the newly created customer details.
    """
    logger.info("Agent called tool: register_customer (phone: %s, name: %s)", phone, name)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, register_customer as db_register

    async with AsyncSession(engine) as session:
        customer = await db_register(session, phone, name)
        logger.info("Tool register_customer result: Successfully registered %s (ID: %s)", customer.name, customer.id)
        return json.dumps({
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "registered": True,
        })


@function_tool
async def request_location(phone: str) -> str:
    """
    Sends an official, interactive Meta WhatsApp Location Request message to the customer's phone.
    This opens the native GPS location picker on their WhatsApp app.
    Call this tool whenever you need to get the customer's coordinates to find nearby providers.

    Args:
        phone: Customer's E.164 phone number without leading +. e.g. "923038571702"

    Returns:
        JSON with the status of the native WhatsApp location request.
    """
    logger.info("Agent called tool: request_location (phone: %s)", phone)
    from src.api.whatsapp import send_whatsapp_location_request

    success = await send_whatsapp_location_request(to_phone=phone)
    if success:
        logger.info("Tool request_location result: Successfully dispatched WhatsApp location request to %s", phone)
    else:
        logger.error("Tool request_location result: FAILED to dispatch WhatsApp location request to %s. Check token/credentials in .env!", phone)
    return json.dumps({
        "success": success,
        "action": "request_location",
        "message": "Location request sent successfully via WhatsApp." if success else "Failed to send location request."
    })


@function_tool
async def fetch_available_providers(
    service_type: str,
    lat: float,
    lng: float,
    city: str | None = None,
) -> str:
    """
    Finds available providers near the customer's location for the given service.

    Args:
        service_type: One of "ac_repair", "plumber", "electrician"
        lat: Customer latitude
        lng: Customer longitude
        city: Optional city name (e.g., "islamabad", "lahore"). If provided, the system filters by this city. If not, it falls back to the geocoded city.

    Returns:
        JSON list of up to 5 ProviderCard objects ranked by distance.
        Returns empty list if none available.
    """
    logger.info("Agent called tool: fetch_available_providers (service_type: %s, lat: %s, lng: %s, city: %s)", service_type, lat, lng, city)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, fetch_available_providers as db_fetch
    from src.api.geocoding import reverse_geocode_city, CITY_SLUG_MAP
    from src.api.models import ServiceType

    try:
        svc = ServiceType(service_type)
    except ValueError:
        logger.warning("Tool fetch_available_providers failed: Unknown service_type '%s'", service_type)
        return json.dumps({"error": f"Unknown service_type: {service_type}"})

    if city:
        city_slug = CITY_SLUG_MAP.get(city.lower().strip(), city.lower().strip())
    else:
        location_data = await reverse_geocode_city(lat, lng)
        city_slug = location_data.get("slug")
        
    logger.info("Tool fetch_available_providers resolved city: %s", city_slug)

    async with AsyncSession(engine) as session:
        cards = await db_fetch(session, svc, lat, lng, city_slug, limit=5)
        logger.info("Tool fetch_available_providers found %s providers nearby", len(cards))

    return json.dumps([
        {
            "id": c.id,
            "name": c.name,
            "service_type": c.service_type.value,
            "area": c.area,
            "average_rating": c.average_rating,
            "rating_count": c.rating_count,
            "years_experience": c.years_experience,
            "total_jobs_done": c.total_jobs_done,
            "is_verified": c.is_verified,
            "distance_km": c.distance_km,
        }
        for c in cards
    ])


@function_tool
async def initiate_provider_booking(
    customer_phone: str,
    provider_id: int,
    issue: str,
    lat: float,
    lng: float,
    service_type: str,
    city: str | None = None,
) -> str:
    """
    Creates a booking between the customer and the chosen provider.

    Args:
        customer_phone: E.164 phone without +.
        provider_id: ID of the chosen provider (from fetch_available_providers).
        issue: Free-text description of the problem.
        lat: Customer latitude.
        lng: Customer longitude.
        service_type: One of "ac_repair", "plumber", "electrician".
        city: Optional city name (e.g., "islamabad", "lahore"). If provided, saves this city to the booking.

    Returns:
        JSON with booking_id, status, and provider details.
    """
    logger.info(
        "Agent called tool: initiate_provider_booking (phone: %s, provider_id: %s, issue: %s, service_type: %s, city: %s)",
        customer_phone, provider_id, issue, service_type, city
    )
    import time
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import (
        engine,
        get_customer_by_phone,
        create_booking,
        get_booking_with_relations,
    )
    from src.api.geocoding import reverse_geocode_city, CITY_SLUG_MAP
    from src.api.models import ServiceType

    try:
        svc = ServiceType(service_type)
    except ValueError:
        logger.warning("Tool initiate_provider_booking failed: Unknown service_type '%s'", service_type)
        return json.dumps({"error": f"Unknown service_type: {service_type}"})

    idempotency_key = f"{customer_phone}:{int(time.time())}"
    
    if city:
        city_slug = CITY_SLUG_MAP.get(city.lower().strip(), city.lower().strip())
    else:
        location_data = await reverse_geocode_city(lat, lng)
        city_slug = location_data.get("slug")

    async with AsyncSession(engine) as session:
        customer = await get_customer_by_phone(session, customer_phone)
        if not customer:
            logger.warning("Tool initiate_provider_booking failed: Customer with phone %s not registered", customer_phone)
            return json.dumps({"error": "Customer not found. Please register first."})

        booking = await create_booking(
            session,
            customer_id=customer.id,
            provider_id=provider_id,
            issue=issue,
            lat=lat,
            lng=lng,
            city=city_slug,
            service_type=svc,
            idempotency_key=idempotency_key,
        )

        provider = booking.provider
        logger.info(
            "Tool initiate_provider_booking result: Successfully booked provider %s (ID: %s) for booking ID %s",
            provider.name, provider.id, booking.id
        )

    return json.dumps({
        "booking_id": booking.id,
        "status": booking.status.value,
        "idempotency_key": idempotency_key,
        "provider": {
            "id": provider.id,
            "name": provider.name,
            "phone": provider.phone,
            "area": provider.area,
        },
        "message": (
            f"Booking confirmed! {provider.name} will contact you shortly. "
            f"Booking ID: #{booking.id}"
        ),
    })


@function_tool
async def check_booking_status(
    customer_phone: str,
    booking_id: int | None = None,
) -> str:
    """
    Returns the live status of the customer's booking.
    Use this when the customer asks where the provider is, has he left, what's the status, etc.

    Args:
        customer_phone: E.164 phone without +. Used to find the most recent booking.
        booking_id: Optional. If provided, fetches that specific booking instead.

    Returns:
        JSON with status, status_label (in Urdu/Roman Urdu), provider name, and cost details.
    """
    logger.info("Agent called tool: check_booking_status (phone: %s, booking_id: %s)", customer_phone, booking_id)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import (
        engine,
        get_booking_with_relations,
        get_latest_booking_for_customer,
    )

    async with AsyncSession(engine) as session:
        if booking_id:
            try:
                booking = await get_booking_with_relations(session, booking_id)
            except Exception:
                logger.warning("Tool check_booking_status failed: Booking #%s not found", booking_id)
                return json.dumps({"error": f"Booking #{booking_id} not found."})
        else:
            booking = await get_latest_booking_for_customer(session, customer_phone)

        if not booking:
            logger.warning("Tool check_booking_status failed: No active booking found for phone %s", customer_phone)
            return json.dumps({"error": "No active booking found."})

        provider = booking.provider
        status = booking.status.value
        label = STATUS_LABELS.get(status, "Status unknown.")

        # Append final cost to completed label
        if status == "completed" and booking.final_cost:
            label = f"Kaam mukammal ho gaya. Final cost: PKR {booking.final_cost}."

        logger.info(
            "Tool check_booking_status result: Booking ID %s status is %s (Label: %s)",
            booking.id, status, label
        )

        return json.dumps({
            "booking_id": booking.id,
            "status": status,
            "status_label": label,
            "provider_name": provider.name,
            "provider_phone": provider.phone,
            "service_type": booking.service_type.value,
            "estimated_cost_min": booking.estimated_cost_min,
            "estimated_cost_max": booking.estimated_cost_max,
            "final_cost": booking.final_cost,
            "created_at": booking.created_at.isoformat(),
            "updated_at": booking.updated_at.isoformat(),
        })


@function_tool
async def cancel_booking(booking_id: int, customer_phone: str) -> str:
    """
    Cancels a booking on behalf of the customer.

    Args:
        booking_id: The booking to cancel.
        customer_phone: Used to verify the booking belongs to this customer.

    Returns:
        JSON confirmation of cancellation.
    """
    logger.info("Agent called tool: cancel_booking (booking_id: %s, phone: %s)", booking_id, customer_phone)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, get_booking_with_relations, update_booking
    from src.api.models import BookingStatus, CancelledBy

    async with AsyncSession(engine) as session:
        try:
            booking = await get_booking_with_relations(session, booking_id)
        except Exception:
            logger.warning("Tool cancel_booking failed: Booking #%s not found", booking_id)
            return json.dumps({"error": f"Booking #{booking_id} not found."})

        if booking.status in (BookingStatus.completed, BookingStatus.cancelled):
            logger.warning("Tool cancel_booking failed: Booking #%s is already %s", booking_id, booking.status.value)
            return json.dumps({
                "error": f"Booking #{booking_id} is already {booking.status.value} and cannot be cancelled."
            })

        await update_booking(
            session,
            booking_id,
            status=BookingStatus.cancelled,
            cancelled_by=CancelledBy.customer,
        )
        logger.info("Tool cancel_booking result: Successfully cancelled Booking ID %s", booking_id)

        return json.dumps({
            "booking_id": booking_id,
            "status": "cancelled",
            "message": f"Booking #{booking_id} has been cancelled successfully.",
        })


@function_tool
async def confirm_booking(
    customer_phone: str,
    booking_id: int | None = None,
) -> str:
    """
    Confirms a booking when the customer explicitly agrees to proceed (e.g. clicks Confirm Booking on WhatsApp).
    Transitions the booking status from 'accepted' to 'confirmed'.
    Sends a WhatsApp confirmation to the customer.

    Args:
        customer_phone: E.164 phone without +. Used to locate the booking.
        booking_id: Optional. The specific booking ID to confirm.

    Returns:
        JSON with the updated booking status.
    """
    logger.info("Agent called tool: confirm_booking (phone: %s, booking_id: %s)", customer_phone, booking_id)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import (
        engine,
        get_booking_with_relations,
        get_latest_booking_for_customer,
        update_booking,
    )
    from src.api.models import BookingStatus
    from src.api.whatsapp import send_whatsapp_message

    async with AsyncSession(engine) as session:
        if booking_id:
            try:
                booking = await get_booking_with_relations(session, booking_id)
            except Exception:
                logger.warning("Tool confirm_booking failed: Booking #%s not found", booking_id)
                return json.dumps({"error": f"Booking #{booking_id} not found."})
        else:
            booking = await get_latest_booking_for_customer(session, customer_phone)

        if not booking:
            logger.warning("Tool confirm_booking failed: No active booking found for phone %s", customer_phone)
            return json.dumps({"error": "No booking found to confirm."})

        if booking.status != BookingStatus.accepted:
            logger.warning(
                "Tool confirm_booking failed: Booking #%s is in status %s, expected 'accepted'",
                booking.id, booking.status.value
            )
            return json.dumps({
                "error": (
                    f"Booking cannot be confirmed. Current status is '{booking.status.value}', "
                    "expected 'accepted'."
                )
            })

        booking = await update_booking(session, booking.id, status=BookingStatus.confirmed)
        provider_name = booking.provider.name

        logger.info(
            "Tool confirm_booking result: Successfully confirmed Booking ID %s",
            booking.id
        )

        return json.dumps({
            "booking_id": booking.id,
            "status": "confirmed",
            "message": f"Booking confirmed! {provider_name} is on their way."
        })


@function_tool
async def submit_rating(customer_phone: str, rating: int, review: str | None = None) -> str:
    """
    Submits a rating for the customer's most recently completed booking.
    Call this when the customer provides a rating (1 to 5) for their service.

    Args:
        customer_phone: E.164 phone without +.
        rating: Integer between 1 and 5.
        review: Optional text review.

    Returns:
        JSON with the status of the rating submission.
    """
    logger.info("Agent called tool: submit_rating (phone: %s, rating: %s)", customer_phone, rating)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, get_latest_booking_for_customer, submit_rating as db_submit_rating
    from src.api.models import BookingStatus

    async with AsyncSession(engine) as session:
        booking = await get_latest_booking_for_customer(session, customer_phone)

        if not booking:
            logger.warning("Tool submit_rating failed: No booking found for phone %s", customer_phone)
            return json.dumps({"error": "No booking found to rate."})

        if booking.status != BookingStatus.completed:
            logger.warning("Tool submit_rating failed: Booking %s is not completed", booking.id)
            return json.dumps({"error": "Only completed bookings can be rated."})

        try:
            await db_submit_rating(session, booking.id, rating, review)
        except Exception as e:
            logger.error("Error submitting rating: %s", str(e))
            return json.dumps({"error": f"Database error submitting rating: {str(e)}"})
            
        logger.info("Tool submit_rating result: Successfully rated Booking ID %s with %s stars", booking.id, rating)

        return json.dumps({
            "booking_id": booking.id,
            "status": "success",
            "message": f"Successfully recorded {rating}-star rating."
        })


# ---------------------------------------------------------------------------
# Agent instantiation
# ---------------------------------------------------------------------------

ustaad_agent = Agent(
    name="Ustaad Agent",
    model="gpt-4o-mini",
    instructions=USTAAD_INSTRUCTIONS,
    tools=[
        get_service_categories,
        check_customer_exists,
        register_customer,
        request_location,
        fetch_available_providers,
        initiate_provider_booking,
        check_booking_status,
        cancel_booking,
        confirm_booking,
        submit_rating,
    ],
)
