"""
models.py — All SQLModel table models + Pydantic request/response schemas.
Single source of truth for the entire data layer.
"""

# NOTE: Do NOT add 'from __future__ import annotations' here.
# SQLModel's Relationship() resolves type hints at class-creation time.
# PEP 563 postponed evaluation breaks list["Booking"] resolution in SQLAlchemy 2.x.

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import field_validator, model_validator
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Index


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ServiceType(str, Enum):
    ac_repair = "ac_repair"
    plumber = "plumber"
    electrician = "electrician"
    handyman = "handyman"


class BookingStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    confirmed = "confirmed"
    en_route = "en_route"
    arrived = "arrived"
    completed = "completed"
    cancelled = "cancelled"


class CancelledBy(str, Enum):
    customer = "customer"
    provider = "provider"


# Valid forward-only transitions. Any status NOT in this dict cannot be advanced.
BOOKING_TRANSITIONS: dict[BookingStatus, BookingStatus] = {
    BookingStatus.pending: BookingStatus.accepted,
    BookingStatus.accepted: BookingStatus.confirmed,
    BookingStatus.confirmed: BookingStatus.en_route,
    BookingStatus.en_route: BookingStatus.arrived,
    BookingStatus.arrived: BookingStatus.completed,
}


# ---------------------------------------------------------------------------
# Table: customers
# ---------------------------------------------------------------------------


class Customer(SQLModel, table=True):
    __tablename__ = "customers"

    id: int | None = Field(default=None, primary_key=True)

    phone: str = Field(unique=True, index=True, max_length=20)
    # E.164 format, no leading +. e.g. "923001234567"

    name: str = Field(min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    bookings: list["Booking"] = Relationship(back_populates="customer")


# ---------------------------------------------------------------------------
# Table: providers
# ---------------------------------------------------------------------------


class Provider(SQLModel, table=True):
    __tablename__ = "providers"
    __table_args__ = (
        Index("idx_providers_city_service", "city", "service_type"),
    )

    id: int | None = Field(default=None, primary_key=True)

    # ── Identity ─────────────────────────────────────────────────────────
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(max_length=20)
    # E.164, no +. Used to call/WhatsApp the provider directly.

    cnic: str | None = Field(default=None, max_length=15, unique=True)
    # Pakistani CNIC: "35202-1234567-1". Optional but recommended.

    profile_pic_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=500)

    # ── Service & Location ────────────────────────────────────────────────
    service_type: ServiceType = Field(index=True)
    # One primary service type. Multi-skill → separate rows by design.

    city: str = Field(index=True, max_length=50)
    # Canonical slug: "islamabad" | "lahore" | "karachi" | "rawalpindi" | "faisalabad"
    # Must match the slug returned by reverse_geocode_city().

    area: str | None = Field(default=None, max_length=100)
    # Human-readable sub-area. Display only — not used for filtering.

    lat: float = Field()
    lng: float = Field()
    # Provider's home/base location. Used for Haversine distance ranking.

    visit_fee: int = Field(default=500)
    # Provider's standard diagnostic visit fee. PKR.

    # ── Availability ──────────────────────────────────────────────────────
    is_active: bool = Field(default=True)
    # False = provider is disabled/suspended.
    # "Busy" is inferred from active bookings — not stored here.

    # ── Ratings ───────────────────────────────────────────────────────────
    rating_total: float = Field(default=0.0)
    # Sum of all individual star ratings (1–5 per booking).

    rating_count: int = Field(default=0)
    # Number of completed bookings that received a rating.

    # ── Experience & Trust ────────────────────────────────────────────────
    years_experience: int = Field(default=0, ge=0, le=50)
    total_jobs_done: int = Field(default=0)
    # Incremented automatically when a booking reaches "completed".

    is_verified: bool = Field(default=False)
    # Set to True after manual admin CNIC verification.

    # ── Timestamps ────────────────────────────────────────────────────────
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    bookings: list["Booking"] = Relationship(back_populates="provider")

    # ── Computed property (Python-side, not stored) ───────────────────────
    @property
    def average_rating(self) -> float | None:
        if self.rating_count == 0:
            return None
        return round(self.rating_total / self.rating_count, 1)


# ---------------------------------------------------------------------------
# Table: bookings
# ---------------------------------------------------------------------------


class Booking(SQLModel, table=True):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("idx_bookings_status", "status"),
        Index("idx_bookings_provider_status", "provider_id", "status"),
    )

    id: int | None = Field(default=None, primary_key=True)

    # ── Relations ─────────────────────────────────────────────────────────
    customer_id: int = Field(foreign_key="customers.id")
    provider_id: int = Field(foreign_key="providers.id")
    customer: Optional["Customer"] = Relationship(back_populates="bookings")
    provider: Optional["Provider"] = Relationship(back_populates="bookings")

    # ── Job Details ───────────────────────────────────────────────────────
    issue: str = Field(max_length=500)
    # Free-text problem description. e.g. "AC cooling nahi kar raha"

    service_type: ServiceType = Field()
    # Denormalised from provider for faster reporting.

    # ── Location ──────────────────────────────────────────────────────────
    customer_lat: float = Field()
    customer_lng: float = Field()
    customer_city: str | None = Field(default=None, max_length=50)
    # Resolved via reverse_geocode_city() at booking creation time.

    # ── Lifecycle ─────────────────────────────────────────────────────────
    status: BookingStatus = Field(default=BookingStatus.pending, index=True)

    # ── Pricing ───────────────────────────────────────────────────────────
    estimated_cost_min: int | None = Field(default=None)
    estimated_cost_max: int | None = Field(default=None)
    # PKR. Set by the provider on /accept.

    final_cost: int | None = Field(default=None)
    # PKR. Set by provider on /complete. Actual amount charged.

    # ── Cancellation ──────────────────────────────────────────────────────
    cancelled_by: CancelledBy | None = Field(default=None)

    # ── Rating ────────────────────────────────────────────────────────────
    customer_rating: int | None = Field(default=None, ge=1, le=5)
    # 1–5 stars. Submitted by customer after job completes.

    customer_review: str | None = Field(default=None, max_length=300)

    # ── Idempotency ───────────────────────────────────────────────────────
    idempotency_key: str = Field(unique=True, max_length=100)
    # Format: "{customer_phone}:{unix_timestamp}". Set by agent at booking creation.

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Request Schemas (input validators — no table=True)
# ---------------------------------------------------------------------------


class CustomerChatRequest(SQLModel):
    phone: str = Field(min_length=10, max_length=15)
    # E.164 without +. 10–15 digits only — validated by model_validator below.
    message: str = Field(max_length=2000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    idempotency_key: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def lat_lng_both_or_neither(self) -> "CustomerChatRequest":
        if (self.lat is None) != (self.lng is None):
            raise ValueError("Provide both lat and lng, or neither.")
        return self


class BookingAcceptRequest(SQLModel):
    estimated_cost_min: int = Field(gt=0, le=1_000_000)
    estimated_cost_max: int = Field(gt=0, le=1_000_000)

    @model_validator(mode="after")
    def min_less_than_max(self) -> "BookingAcceptRequest":
        if self.estimated_cost_min > self.estimated_cost_max:
            raise ValueError("estimated_cost_min must be ≤ estimated_cost_max.")
        return self


class BookingStatusRequest(SQLModel):
    status: BookingStatus
    # Only en_route | arrived accepted here.
    # accepted and confirmed have dedicated endpoints.

    @field_validator("status")
    @classmethod
    def must_be_advanceable(cls, v: BookingStatus) -> BookingStatus:
        allowed = {BookingStatus.en_route, BookingStatus.arrived}
        if v not in allowed:
            raise ValueError(
                f"Use the dedicated endpoint for '{v}'. "
                "Only 'en_route' and 'arrived' are accepted here."
            )
        return v


class BookingCompleteRequest(SQLModel):
    final_cost: int = Field(gt=0, le=1_000_000)
    # Actual amount charged. Required when marking a job completed.


class BookingRatingRequest(SQLModel):
    rating: int = Field(ge=1, le=5)
    review: str | None = Field(default=None, max_length=300)


class BookingCancelRequest(SQLModel):
    cancelled_by: CancelledBy


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------


class ProviderCard(SQLModel):
    """Minimal provider info returned in the agent's provider list."""

    id: int
    name: str
    service_type: ServiceType
    area: str | None
    average_rating: float | None  # None if no ratings yet
    rating_count: int
    years_experience: int
    total_jobs_done: int
    is_verified: bool
    distance_km: float  # injected by fetch_available_providers query
    visit_fee: int


class ProviderDetail(ProviderCard):
    """Full provider profile — returned on provider detail endpoint."""

    phone: str
    is_active: bool
    bio: str | None
    profile_pic_url: str | None
    city: str
    lat: float
    lng: float
    joined_at: datetime
    # CNIC is intentionally excluded from all response schemas


class BookingCreatedResponse(SQLModel):
    booking_id: int
    status: BookingStatus
    provider: ProviderCard
    message: str  # human-readable confirmation for the agent to relay


class BookingStatusResponse(SQLModel):
    booking_id: int
    status: BookingStatus
    whatsapp_sent: bool


class ActiveJobResponse(SQLModel):
    """Returned to the provider app for the current active job."""

    booking_id: int
    customer_name: str
    customer_phone: str
    issue: str
    service_type: ServiceType
    customer_lat: float
    customer_lng: float
    customer_city: str | None
    status: BookingStatus
    estimated_cost_min: int | None
    estimated_cost_max: int | None
    created_at: datetime


class BookingAcceptResponse(SQLModel):
    booking_id: int
    status: BookingStatus  # "accepted"
    estimated_cost_min: int
    estimated_cost_max: int
    whatsapp_sent: bool


class BookingCompleteResponse(SQLModel):
    booking_id: int
    status: BookingStatus  # "completed"
    final_cost: int
    whatsapp_sent: bool


class CustomerChatResponse(SQLModel):
    reply: str
    session_id: str


class ErrorResponse(SQLModel):
    error: str
    detail: str | None = None


# ---------------------------------------------------------------------------
# Provider Auth & Profile Request Schemas
# ---------------------------------------------------------------------------


class ProviderRegisterRequest(SQLModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    service_type: ServiceType
    city: str = Field(min_length=2, max_length=50)
    area: str | None = Field(default=None, max_length=100)
    visit_fee: int = Field(gt=0, le=10000)
    years_experience: int = Field(default=0, ge=0, le=50)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    bio: str | None = Field(default=None, max_length=500)
    cnic: str | None = Field(default=None, max_length=15)
    profile_pic_url: str | None = Field(default=None, max_length=500)


class ProviderLoginRequest(SQLModel):
    phone: str = Field(min_length=10, max_length=15)


class ProviderLocationUpdateRequest(SQLModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ProviderProfileUpdateRequest(SQLModel):
    is_active: bool | None = None
    bio: str | None = None
    visit_fee: int | None = None
    area: str | None = None
    cnic: str | None = Field(default=None, max_length=15)

