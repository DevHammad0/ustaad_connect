"""
routes/provider.py — Provider app endpoints.

All endpoints require X-App-Secret header.
Button taps in the provider app call these endpoints to advance booking status.

Endpoints:
  GET  /api/provider/{provider_id}/active-job          → Current active booking
  POST /api/provider/bookings/{id}/accept              → Accept + set cost estimate
  POST /api/provider/bookings/{id}/confirm             → Confirm job start
  POST /api/provider/bookings/{id}/status              → Advance to en_route | arrived
  POST /api/provider/bookings/{id}/complete            → Complete with final cost
  POST /api/provider/bookings/{id}/cancel              → Cancel booking
"""

from __future__ import annotations

import logging
import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.api.database import (
    get_booking_with_relations,
    get_session,
    update_booking,
)
from src.api.models import (
    ActiveJobResponse,
    Booking,
    BookingAcceptRequest,
    BookingAcceptResponse,
    BookingCancelRequest,
    BookingCompleteRequest,
    BookingCompleteResponse,
    BookingStatus,
    BookingStatusRequest,
    BookingStatusResponse,
    BOOKING_TRANSITIONS,
    CancelledBy,
    ErrorResponse,
    Provider,
    ProviderDetail,
    ProviderRegisterRequest,
    ProviderLoginRequest,
    ProviderLocationUpdateRequest,
    ProviderProfileUpdateRequest,
)
from src.api.whatsapp import send_whatsapp_message, send_whatsapp_interactive_buttons

load_dotenv()

logger = logging.getLogger(__name__)

APP_SECRET: str = os.environ["APP_SECRET"]

router = APIRouter(prefix="/api/provider", tags=["provider"])



# ---------------------------------------------------------------------------
# Auth dependency (shared with customer router)
# ---------------------------------------------------------------------------


async def verify_app_secret(x_app_secret: Annotated[str | None, Header()] = None) -> None:
    if x_app_secret != APP_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing X-App-Secret header.")


AppSecretDep = Annotated[None, Depends(verify_app_secret)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# GET /api/provider/{provider_id}/active-job
# ---------------------------------------------------------------------------


@router.get(
    "/{provider_id}/active-job",
    response_model=ActiveJobResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
@router.get(
    "/{provider_id}/job",
    response_model=ActiveJobResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_active_job(
    provider_id: int,
    _: AppSecretDep,
    session: SessionDep,
) -> ActiveJobResponse:
    """
    Returns the current active booking for the provider.
    The provider app calls this on load to determine which button to show.
    """
    active_statuses = [
        BookingStatus.pending,
        BookingStatus.accepted,
        BookingStatus.confirmed,
        BookingStatus.en_route,
        BookingStatus.arrived,
    ]
    result = await session.execute(
        select(Booking)
        .where(
            Booking.provider_id == provider_id,
            Booking.status.in_(active_statuses),  # type: ignore[attr-defined]
        )
        .order_by(Booking.created_at.desc())  # type: ignore[arg-type]
        .limit(1)
    )
    booking = result.scalars().first()

    if not booking:
        raise HTTPException(status_code=404, detail="No active job found for this provider.")

    booking = await get_booking_with_relations(session, booking.id)
    customer = booking.customer

    return ActiveJobResponse(
        booking_id=booking.id,
        customer_name=customer.name,
        customer_phone=customer.phone,
        issue=booking.issue,
        service_type=booking.service_type,
        customer_lat=booking.customer_lat,
        customer_lng=booking.customer_lng,
        customer_city=booking.customer_city,
        status=booking.status,
        estimated_cost_min=booking.estimated_cost_min,
        estimated_cost_max=booking.estimated_cost_max,
        created_at=booking.created_at,
    )


# ---------------------------------------------------------------------------
# POST /api/provider/bookings/{booking_id}/accept
# ---------------------------------------------------------------------------


@router.post(
    "/bookings/{booking_id}/accept",
    response_model=BookingAcceptResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def accept_booking(
    booking_id: int,
    body: BookingAcceptRequest,
    _: AppSecretDep,
    session: SessionDep,
) -> BookingAcceptResponse:
    """
    Provider accepts the booking and sets an estimated cost range.
    Sends a WhatsApp message to the customer with the estimate.

    Provider app: "Accept Job" button → calls this endpoint.
    """
    booking = await _get_booking_or_404(session, booking_id)
    _require_status(booking, BookingStatus.pending)

    booking = await update_booking(
        session,
        booking_id,
        status=BookingStatus.accepted,
        estimated_cost_min=body.estimated_cost_min,
        estimated_cost_max=body.estimated_cost_max,
    )

    provider_name = booking.provider.name
    customer_phone = booking.customer.phone
    visit_fee = booking.provider.visit_fee

    body_text = (
        f"Aapke plumbing/repairing masle ke liye, Ustaad {provider_name} ne niche diya gaya estimate offer kiya hai:\n\n"
        f"💵 *Visit Charge:* PKR {visit_fee}\n"
        f"🔧 *Estimated Repair Cost:* PKR {body.estimated_cost_min}–{body.estimated_cost_max}\n\n"
        f"Kya aap is booking ko confirm karna chahte hain?"
    )
    
    buttons = [
        {"id": "confirm_booking", "title": "Confirm Booking"},
        {"id": "cancel_booking", "title": "Cancel Booking"},
    ]

    whatsapp_sent = await send_whatsapp_interactive_buttons(
        to_phone=customer_phone,
        body_text=body_text,
        buttons=buttons,
        header_text="Ustaad Connect — Estimate Offered",
        footer_text="Niche diye gaye buttons se confirm ya cancel karein."
    )

    return BookingAcceptResponse(
        booking_id=booking_id,
        status=BookingStatus.accepted,
        estimated_cost_min=body.estimated_cost_min,
        estimated_cost_max=body.estimated_cost_max,
        whatsapp_sent=whatsapp_sent,
    )


# ---------------------------------------------------------------------------
# POST /api/provider/bookings/{booking_id}/confirm
# ---------------------------------------------------------------------------


@router.post(
    "/bookings/{booking_id}/confirm",
    response_model=BookingStatusResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def confirm_booking(
    booking_id: int,
    _: AppSecretDep,
    session: SessionDep,
) -> BookingStatusResponse:
    """
    Provider confirms the job is starting.
    Sends a WhatsApp message informing the customer.

    Provider app: "Confirm / Start Job" button → calls this endpoint.
    """
    booking = await _get_booking_or_404(session, booking_id)
    _require_status(booking, BookingStatus.accepted)

    booking = await update_booking(session, booking_id, status=BookingStatus.confirmed)

    provider_name = booking.provider.name
    customer_phone = booking.customer.phone

    wa_message = (
        f"🔧 Booking confirmed! {provider_name} aapke paas aa raha hai.\n"
        f"Agar koi sawal ho to humse rabta karein."
    )
    whatsapp_sent = await send_whatsapp_message(customer_phone, wa_message)

    return BookingStatusResponse(
        booking_id=booking_id,
        status=BookingStatus.confirmed,
        whatsapp_sent=whatsapp_sent,
    )


# ---------------------------------------------------------------------------
# POST /api/provider/bookings/{booking_id}/status
# ---------------------------------------------------------------------------


_STATUS_MESSAGES: dict[BookingStatus, str] = {
    BookingStatus.en_route: "🚗 {provider_name} aapki taraf aa raha hai! Thodi der mein pahunch jaenge.",
    BookingStatus.arrived:  "📍 {provider_name} aapke darwaze par hai! Darwaza khol dein.",
}


@router.post(
    "/bookings/{booking_id}/status",
    response_model=BookingStatusResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def advance_booking_status(
    booking_id: int,
    body: BookingStatusRequest,
    _: AppSecretDep,
    session: SessionDep,
) -> BookingStatusResponse:
    """
    Advances the booking through en_route → arrived.
    Each transition triggers a WhatsApp message to the customer.

    Provider app buttons:
      "I'm On My Way" → { "status": "en_route" }
      "I've Arrived"  → { "status": "arrived" }
    """
    booking = await _get_booking_or_404(session, booking_id)

    expected_from = BOOKING_TRANSITIONS.get(booking.status)
    if expected_from != body.status:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid transition: cannot move from '{booking.status.value}' to '{body.status.value}'. "
                f"Expected next status: '{expected_from.value if expected_from else 'none'}'."
            ),
        )

    booking = await update_booking(session, booking_id, status=body.status)

    provider_name = booking.provider.name
    customer_phone = booking.customer.phone
    template = _STATUS_MESSAGES.get(body.status, "")
    wa_message = template.format(provider_name=provider_name)
    whatsapp_sent = await send_whatsapp_message(customer_phone, wa_message)

    return BookingStatusResponse(
        booking_id=booking_id,
        status=body.status,
        whatsapp_sent=whatsapp_sent,
    )


# ---------------------------------------------------------------------------
# POST /api/provider/bookings/{booking_id}/complete
# ---------------------------------------------------------------------------


@router.post(
    "/bookings/{booking_id}/complete",
    response_model=BookingCompleteResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def complete_booking(
    booking_id: int,
    body: BookingCompleteRequest,
    _: AppSecretDep,
    session: SessionDep,
) -> BookingCompleteResponse:
    """
    Provider marks the job complete and records the final cost.
    Increments provider.total_jobs_done.
    Sends a WhatsApp message to the customer with the final bill and rating prompt.

    Provider app: "Mark Complete" button (requires entering final cost) → calls this endpoint.
    """
    booking = await _get_booking_or_404(session, booking_id)
    _require_status(booking, BookingStatus.arrived)

    provider = booking.provider

    booking = await update_booking(
        session,
        booking_id,
        status=BookingStatus.completed,
        final_cost=body.final_cost,
    )

    # Increment provider total_jobs_done
    provider.total_jobs_done += 1
    session.add(provider)
    await session.commit()

    customer_phone = booking.customer.phone
    provider_name = provider.name

    wa_message = (
        f"✅ Kaam mukammal ho gaya! {provider_name} ne aapka masla hal kar diya.\n"
        f"Final Cost: PKR {body.final_cost}\n\n"
        f"Apna feedback aur rating (1–5 stars) isi chat par reply kar ke share karein (e.g., \"5 boht achi service\").\n"
        f"Shukriya Ustaad Connect use karne ka 🙏"
    )
    whatsapp_sent = await send_whatsapp_message(customer_phone, wa_message)

    return BookingCompleteResponse(
        booking_id=booking_id,
        status=BookingStatus.completed,
        final_cost=body.final_cost,
        whatsapp_sent=whatsapp_sent,
    )


# ---------------------------------------------------------------------------
# POST /api/provider/bookings/{booking_id}/cancel
# ---------------------------------------------------------------------------


@router.post(
    "/bookings/{booking_id}/cancel",
    response_model=BookingStatusResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def cancel_booking(
    booking_id: int,
    body: BookingCancelRequest,
    _: AppSecretDep,
    session: SessionDep,
) -> BookingStatusResponse:
    """
    Cancels a booking. Either party can cancel.
    If the provider cancels, a WhatsApp notification is sent to the customer.

    Provider app: "Cancel Job" button → { "cancelled_by": "provider" }
    """
    booking = await _get_booking_or_404(session, booking_id)

    if booking.status in (BookingStatus.completed, BookingStatus.cancelled):
        raise HTTPException(
            status_code=400,
            detail=f"Booking #{booking_id} is already '{booking.status.value}' and cannot be cancelled.",
        )

    booking = await update_booking(
        session,
        booking_id,
        status=BookingStatus.cancelled,
        cancelled_by=body.cancelled_by,
    )

    whatsapp_sent = False
    if body.cancelled_by == CancelledBy.provider:
        provider_name = booking.provider.name
        customer_phone = booking.customer.phone
        wa_message = (
            f"❌ Afsos, {provider_name} aapki booking accept nahi kar saka.\n"
            f"Hum aapko doosra provider dhundh rahe hain. "
            f"Ustaad Connect se dobara book karein."
        )
        whatsapp_sent = await send_whatsapp_message(customer_phone, wa_message)

    return BookingStatusResponse(
        booking_id=booking_id,
        status=BookingStatus.cancelled,
        whatsapp_sent=whatsapp_sent,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_booking_or_404(session: AsyncSession, booking_id: int) -> Booking:
    """Fetches a booking with relations or raises 404."""
    try:
        return await get_booking_with_relations(session, booking_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Booking #{booking_id} not found.")


def _require_status(booking: Booking, required: BookingStatus) -> None:
    """Raises 400 if the booking is not in the expected status."""
    if booking.status != required:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Action requires booking status '{required.value}', "
                f"but current status is '{booking.status.value}'."
            ),
        )


# ===========================================================================
# Brand New Mobile Provider App Endpoints
# ===========================================================================


@router.post(
    "/register",
    response_model=ProviderDetail,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
async def register_provider(
    body: ProviderRegisterRequest,
    _: AppSecretDep,
    session: SessionDep,
) -> ProviderDetail:
    """
    Onboards a new provider. Ensures phone uniqueness.
    """
    result = await session.execute(
        select(Provider).where(Provider.phone == body.phone)
    )
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A provider with this phone number is already registered."
        )

    provider = Provider(
        name=body.name,
        phone=body.phone,
        service_type=body.service_type,
        city=body.city,
        area=body.area,
        visit_fee=body.visit_fee,
        years_experience=body.years_experience,
        lat=body.lat,
        lng=body.lng,
        bio=body.bio,
        cnic=body.cnic,
        profile_pic_url=body.profile_pic_url,
        is_active=True,
        is_verified=False,
    )

    session.add(provider)
    await session.commit()
    await session.refresh(provider)

    return ProviderDetail(
        id=provider.id,
        name=provider.name,
        service_type=provider.service_type,
        area=provider.area,
        average_rating=provider.average_rating,
        rating_count=provider.rating_count,
        years_experience=provider.years_experience,
        total_jobs_done=provider.total_jobs_done,
        is_verified=provider.is_verified,
        distance_km=0.0,
        visit_fee=provider.visit_fee,
        phone=provider.phone,
        is_active=provider.is_active,
        bio=provider.bio,
        profile_pic_url=provider.profile_pic_url,
        city=provider.city,
        lat=provider.lat,
        lng=provider.lng,
        joined_at=provider.joined_at,
    )


@router.post(
    "/login",
    response_model=ProviderDetail,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def login_provider(
    body: ProviderLoginRequest,
    _: AppSecretDep,
    session: SessionDep,
) -> ProviderDetail:
    """
    Passwordless authentication for providers via their E.164 phone.
    """
    result = await session.execute(
        select(Provider).where(Provider.phone == body.phone)
    )
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(
            status_code=404,
            detail="No provider profile matches this phone number."
        )

    return ProviderDetail(
        id=provider.id,
        name=provider.name,
        service_type=provider.service_type,
        area=provider.area,
        average_rating=provider.average_rating,
        rating_count=provider.rating_count,
        years_experience=provider.years_experience,
        total_jobs_done=provider.total_jobs_done,
        is_verified=provider.is_verified,
        distance_km=0.0,
        visit_fee=provider.visit_fee,
        phone=provider.phone,
        is_active=provider.is_active,
        bio=provider.bio,
        profile_pic_url=provider.profile_pic_url,
        city=provider.city,
        lat=provider.lat,
        lng=provider.lng,
        joined_at=provider.joined_at,
    )


@router.get(
    "/{provider_id}/profile",
    response_model=ProviderDetail,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_provider_profile(
    provider_id: int,
    _: AppSecretDep,
    session: SessionDep,
) -> ProviderDetail:
    """
    Returns full details for a provider profile.
    """
    result = await session.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(
            status_code=404,
            detail=f"Provider with ID #{provider_id} not found."
        )

    return ProviderDetail(
        id=provider.id,
        name=provider.name,
        service_type=provider.service_type,
        area=provider.area,
        average_rating=provider.average_rating,
        rating_count=provider.rating_count,
        years_experience=provider.years_experience,
        total_jobs_done=provider.total_jobs_done,
        is_verified=provider.is_verified,
        distance_km=0.0,
        visit_fee=provider.visit_fee,
        phone=provider.phone,
        is_active=provider.is_active,
        bio=provider.bio,
        profile_pic_url=provider.profile_pic_url,
        city=provider.city,
        lat=provider.lat,
        lng=provider.lng,
        joined_at=provider.joined_at,
    )


@router.put(
    "/{provider_id}/profile",
    response_model=ProviderDetail,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def update_provider_profile(
    provider_id: int,
    body: ProviderProfileUpdateRequest,
    _: AppSecretDep,
    session: SessionDep,
) -> ProviderDetail:
    """
    Updates provider profile details.
    """
    result = await session.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(
            status_code=404,
            detail=f"Provider with ID #{provider_id} not found."
        )

    if body.is_active is not None:
        provider.is_active = body.is_active
    if body.bio is not None:
        provider.bio = body.bio
    if body.visit_fee is not None:
        provider.visit_fee = body.visit_fee
    if body.area is not None:
        provider.area = body.area
    if body.cnic is not None:
        provider.cnic = body.cnic

    session.add(provider)
    await session.commit()
    await session.refresh(provider)

    return ProviderDetail(
        id=provider.id,
        name=provider.name,
        service_type=provider.service_type,
        area=provider.area,
        average_rating=provider.average_rating,
        rating_count=provider.rating_count,
        years_experience=provider.years_experience,
        total_jobs_done=provider.total_jobs_done,
        is_verified=provider.is_verified,
        distance_km=0.0,
        visit_fee=provider.visit_fee,
        phone=provider.phone,
        is_active=provider.is_active,
        bio=provider.bio,
        profile_pic_url=provider.profile_pic_url,
        city=provider.city,
        lat=provider.lat,
        lng=provider.lng,
        joined_at=provider.joined_at,
    )


@router.post(
    "/{provider_id}/location",
    responses={
        200: {"description": "Location updated successfully"},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def update_provider_location(
    provider_id: int,
    body: ProviderLocationUpdateRequest,
    _: AppSecretDep,
    session: SessionDep,
):
    """
    Background coordinate tracker endpoint to stream real-time coordinates.
    """
    result = await session.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(
            status_code=404,
            detail=f"Provider with ID #{provider_id} not found."
        )

    provider.lat = body.lat
    provider.lng = body.lng

    session.add(provider)
    await session.commit()

    return {"success": True, "message": "Location updated successfully."}


@router.get(
    "/{provider_id}/bookings",
    response_model=list[ActiveJobResponse],
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_provider_bookings_history(
    provider_id: int,
    _: AppSecretDep,
    session: SessionDep,
) -> list[ActiveJobResponse]:
    """
    Returns historical/past/active booking records for a provider.
    """
    result = await session.execute(
        select(Provider).where(Provider.id == provider_id)
    )
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(
            status_code=404,
            detail=f"Provider with ID #{provider_id} not found."
        )

    result_bookings = await session.execute(
        select(Booking)
        .where(Booking.provider_id == provider_id)
        .order_by(Booking.created_at.desc())  # type: ignore[arg-type]
    )
    bookings = result_bookings.scalars().all()

    history = []
    for b in bookings:
        # Load relations since they are lazy loaded
        b_rel = await get_booking_with_relations(session, b.id)
        history.append(
            ActiveJobResponse(
                booking_id=b_rel.id,
                customer_name=b_rel.customer.name,
                customer_phone=b_rel.customer.phone,
                issue=b_rel.issue,
                service_type=b_rel.service_type,
                customer_lat=b_rel.customer_lat,
                customer_lng=b_rel.customer_lng,
                customer_city=b_rel.customer_city,
                status=b_rel.status,
                estimated_cost_min=b_rel.estimated_cost_min,
                estimated_cost_max=b_rel.estimated_cost_max,
                created_at=b_rel.created_at,
            )
        )

    return history

