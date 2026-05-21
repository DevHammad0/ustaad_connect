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
    ServiceType,
)
from src.api.whatsapp import send_whatsapp_message, send_whatsapp_interactive_buttons

load_dotenv()

logger = logging.getLogger(__name__)

_SERVICE_ISSUE_MAP = {
    "english": {
        ServiceType.ac_repair: "AC issue",
        ServiceType.plumber: "plumbing issue",
        ServiceType.electrician: "electrical issue",
        ServiceType.handyman: "handyman issue",
    },
    "roman_urdu": {
        ServiceType.ac_repair: "AC masle",
        ServiceType.plumber: "plumbing masle",
        ServiceType.electrician: "bijli ke masle",
        ServiceType.handyman: "handyman masle",
    },
    "urdu": {
        ServiceType.ac_repair: "اے سی کے مسئلے",
        ServiceType.plumber: "پلمبنگ کے مسئلے",
        ServiceType.electrician: "بجلی کے مسئلے",
        ServiceType.handyman: "ہینڈی مین کے مسئلے",
    }
}

_PROVIDER_MESSAGES = {
    "english": {
        "estimate_body": (
            "Ustaad {provider_name} has offered the following estimate for your issue:\n\n"
            "Visit Charge: PKR {visit_fee}\n"
            "Estimated Repair Cost: PKR {min_cost}-{max_cost}\n\n"
            "Do you want to confirm this booking?"
        ),
        "estimate_header": "Ustaad Connect - Estimate Offered",
        "estimate_footer": "Use buttons below to confirm or cancel.",
        "confirm": "Your booking is confirmed with {provider_name}! They will contact you shortly regarding your {issue_type}. Your Booking ID is #{booking_id}. If you have any questions, feel free to ask!",
        "en_route": "{provider_name} is on the way.",
        "arrived": "{provider_name} has arrived at your location.",
        "complete": (
            "Job completed. {provider_name} resolved your issue.\n"
            "Final Cost: PKR {final_cost}\n\n"
            "Please share your rating (1-5 stars) and review in this chat (e.g. \"5 good service\").\n"
            "Thank you for using Ustaad Connect."
        ),
        "cancel": "Ustaad {provider_name} was unable to accept your booking. Please search for another provider on Ustaad Connect.",
    },
    "roman_urdu": {
        "estimate_body": (
            "Ustaad {provider_name} ne aapke masle ke liye estimate offer kiya hai:\n\n"
            "Visit Charge: PKR {visit_fee}\n"
            "Estimated Repair Cost: PKR {min_cost}-{max_cost}\n\n"
            "Kya aap is booking ko confirm karna chahte hain?"
        ),
        "estimate_header": "Ustaad Connect - Estimate Offered",
        "estimate_footer": "Niche diye gaye buttons se confirm ya cancel karein.",
        "confirm": "Aapki booking {provider_name} ke saath confirm ho gayi hai! Woh aapke {issue_type} ke silsile mein jald hi aap se rabta karenge. Booking ID: #{booking_id}. Agar koi sawal ho to pooch sakte hain!",
        "en_route": "{provider_name} aapki taraf aa rahe hain.",
        "arrived": "{provider_name} aapki location par pahunch chuke hain.",
        "complete": (
            "Kaam mukammal ho gaya. {provider_name} ne aapka masla hal kar diya.\n"
            "Final Cost: PKR {final_cost}\n\n"
            "Apna feedback aur rating (1-5 stars) isi chat par reply kar ke share karein (e.g. \"5 achi service\").\n"
            "Shukriya Ustaad Connect use karne ka."
        ),
        "cancel": "Ustaad {provider_name} aapki booking accept nahi kar sake. Bara-e-maharbani Ustaad Connect se koi doosra provider book karein.",
    },
    "urdu": {
        "estimate_body": (
            "استاد {provider_name} نے آپ کے مسئلے کے لیے درج ذیل تخمینہ پیش کیا ہے:\n\n"
            "وزٹ چارجز: PKR {visit_fee}\n"
            "تخمینی مرمتی لاگت: PKR {min_cost}-{max_cost}\n\n"
            "کیا آپ اس بکنگ کی تصدیق کرنا چاہتے ہیں؟"
        ),
        "estimate_header": "استاد کنیکٹ - تخمینہ پیش کیا گیا",
        "estimate_footer": "تصدیق یا منسوخی کے لیے نیچے دیے گئے بٹن استعمال کریں۔",
        "confirm": "آپ کی بکنگ {provider_name} کے ساتھ تصدیق ہو گئی ہے! وہ آپ کے {issue_type} کے سلسلے میں جلد ہی آپ سے رابطہ کریں گے۔ بکنگ آئی ڈی: #{booking_id}۔ اگر آپ کا کوئی سوال ہے تو بلا جھجھک پوچھیں!",
        "en_route": "{provider_name} راستے میں ہیں۔",
        "arrived": "{provider_name} آپ کی لوکیشن پر پہنچ چکے ہیں۔",
        "complete": (
            "کام مکمل ہو گیا۔ {provider_name} نے آپ کا مسئلہ حل کر دیا ہے۔\n"
            "آخری لاگت: PKR {final_cost}\n\n"
            "براہ کرم اسی چیٹ پر اپنی ریٹنگ (1-5 اسٹارز) اور تبصرہ شیئر کریں (مثال کے طور پر \"5 بہت اچھی سروس\")۔\n"
            "استاد کنیکٹ استعمال کرنے کا شکریہ۔"
        ),
        "cancel": "استاد {provider_name} آپ کی بکنگ قبول نہیں کر سکے۔ براہ کرم استاد کنیکٹ پر کسی دوسرے پرووائیڈر کو تلاش کریں۔",
    }
}

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

    lang = getattr(booking, "language", "roman_urdu") or "roman_urdu"
    if lang not in _PROVIDER_MESSAGES:
        lang = "roman_urdu"

    body_template = _PROVIDER_MESSAGES[lang]["estimate_body"]
    body_text = body_template.format(
        provider_name=provider_name,
        visit_fee=visit_fee,
        min_cost=body.estimated_cost_min,
        max_cost=body.estimated_cost_max
    )

    header_text = _PROVIDER_MESSAGES[lang]["estimate_header"]
    footer_text = _PROVIDER_MESSAGES[lang]["estimate_footer"]

    buttons = [
        {"id": "confirm_booking", "title": "Confirm Booking"},
        {"id": "cancel_booking", "title": "Cancel Booking"},
    ]

    whatsapp_sent = await send_whatsapp_interactive_buttons(
        to_phone=customer_phone,
        body_text=body_text,
        buttons=buttons,
        header_text=header_text,
        footer_text=footer_text
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

    lang = getattr(booking, "language", "roman_urdu") or "roman_urdu"
    if lang not in _PROVIDER_MESSAGES:
        lang = "roman_urdu"

    svc_type = booking.service_type
    issue_type = _SERVICE_ISSUE_MAP[lang].get(svc_type, "issue")

    confirm_template = _PROVIDER_MESSAGES[lang]["confirm"]
    wa_message = confirm_template.format(
        provider_name=provider_name,
        issue_type=issue_type,
        booking_id=booking_id
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

    lang = getattr(booking, "language", "roman_urdu") or "roman_urdu"
    if lang not in _PROVIDER_MESSAGES:
        lang = "roman_urdu"

    status_key = body.status.value
    template = _PROVIDER_MESSAGES[lang].get(status_key, "")
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

    lang = getattr(booking, "language", "roman_urdu") or "roman_urdu"
    if lang not in _PROVIDER_MESSAGES:
        lang = "roman_urdu"

    complete_template = _PROVIDER_MESSAGES[lang]["complete"]
    wa_message = complete_template.format(
        provider_name=provider_name,
        final_cost=body.final_cost
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

        lang = getattr(booking, "language", "roman_urdu") or "roman_urdu"
        if lang not in _PROVIDER_MESSAGES:
            lang = "roman_urdu"

        cancel_template = _PROVIDER_MESSAGES[lang]["cancel"]
        wa_message = cancel_template.format(provider_name=provider_name)
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

    if body.name is not None:
        provider.name = body.name
    if body.phone is not None:
        provider.phone = body.phone
    if body.service_type is not None:
        provider.service_type = body.service_type
    if body.city is not None:
        provider.city = body.city
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
    if body.years_experience is not None:
        provider.years_experience = body.years_experience

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

