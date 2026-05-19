"""
database.py — Async engine, session factory, table creation, seed data,
and all query helper functions.

Uses SQLAlchemy 2.x AsyncSession API (session.execute(), not session.exec()).
Requires DATABASE_URL=postgresql+asyncpg://...
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, select

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)

# ---------------------------------------------------------------------------
# Models imported after engine to avoid circular imports
# ---------------------------------------------------------------------------
from src.api.models import (  # noqa: E402
    Booking,
    BookingStatus,
    CancelledBy,
    Customer,
    Provider,
    ProviderCard,
    ServiceType,
)


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------


async def init() -> None:
    """Called once at app startup via lifespan. Creates tables and seeds data."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    await seed_providers_if_empty()


async def close() -> None:
    """Called at app shutdown."""
    await engine.dispose()


# ---------------------------------------------------------------------------
# Session dependency
# ---------------------------------------------------------------------------


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


# ---------------------------------------------------------------------------
# Seed data — 15 providers across 5 cities
# ---------------------------------------------------------------------------

SEED_PROVIDERS = [
    # Islamabad
    dict(name="Ustad Riaz Ahmed",      phone="923011111101", service_type="ac_repair",   city="islamabad",  area="G-13",             lat=33.6938, lng=73.0512, years_experience=12, profile_pic_url="https://randomuser.me/api/portraits/men/32.jpg"),
    dict(name="Ustad Khalid Mehmood",  phone="923011111102", service_type="ac_repair",   city="islamabad",  area="E-11",             lat=33.7050, lng=73.0234, years_experience=8,  profile_pic_url="https://randomuser.me/api/portraits/men/44.jpg"),
    dict(name="Ustad Farooq Ahmad",    phone="923011111103", service_type="plumber",     city="islamabad",  area="F-11",             lat=33.6981, lng=73.0601, years_experience=15, profile_pic_url="https://randomuser.me/api/portraits/men/22.jpg"),
    dict(name="Ustad Imtiaz Khan",     phone="923011111104", service_type="electrician", city="islamabad",  area="G-11",             lat=33.7102, lng=73.0389, years_experience=10, profile_pic_url="https://randomuser.me/api/portraits/men/11.jpg"),
    dict(name="Ustad Nadeem Akhtar",   phone="923011111105", service_type="plumber",     city="islamabad",  area="F-8",              lat=33.7215, lng=73.0267, years_experience=6,  profile_pic_url="https://randomuser.me/api/portraits/men/67.jpg"),
    # Lahore
    dict(name="Ustad Zafar Iqbal",     phone="923021111106", service_type="ac_repair",   city="lahore",     area="DHA Phase 5",      lat=31.5204, lng=74.3587, years_experience=14, profile_pic_url="https://randomuser.me/api/portraits/men/51.jpg"),
    dict(name="Ustad Bilal Hussain",   phone="923021111107", service_type="ac_repair",   city="lahore",     area="Gulberg III",      lat=31.5497, lng=74.3436, years_experience=9,  profile_pic_url="https://randomuser.me/api/portraits/men/78.jpg"),
    dict(name="Ustad Tariq Mahmood",   phone="923021111108", service_type="plumber",     city="lahore",     area="Model Town",       lat=31.5321, lng=74.3290, years_experience=11, profile_pic_url="https://randomuser.me/api/portraits/men/29.jpg"),
    dict(name="Ustad Asif Raza",       phone="923021111109", service_type="electrician", city="lahore",     area="Johar Town",       lat=31.4697, lng=74.4078, years_experience=7,  profile_pic_url="https://randomuser.me/api/portraits/men/33.jpg"),
    dict(name="Ustad Hamid Ali",       phone="923021111110", service_type="plumber",     city="lahore",     area="Bahria Town",      lat=31.4834, lng=74.3251, years_experience=5,  profile_pic_url="https://randomuser.me/api/portraits/men/41.jpg"),
    # Karachi
    dict(name="Ustad Saleem Baig",     phone="923211111111", service_type="ac_repair",   city="karachi",    area="Clifton",          lat=24.8607, lng=67.0011, years_experience=16, profile_pic_url="https://randomuser.me/api/portraits/men/15.jpg"),
    dict(name="Ustad Jameel Shah",     phone="923211111112", service_type="electrician", city="karachi",    area="Gulshan-e-Iqbal",  lat=24.9056, lng=67.0822, years_experience=10, profile_pic_url="https://randomuser.me/api/portraits/men/82.jpg"),
    dict(name="Ustad Waqar Ahmed",     phone="923211111113", service_type="plumber",     city="karachi",    area="PECHS",            lat=24.8772, lng=67.0650, years_experience=8,  profile_pic_url="https://randomuser.me/api/portraits/men/60.jpg"),
    # Rawalpindi
    dict(name="Ustad Asghar Butt",     phone="923011111114", service_type="ac_repair",   city="rawalpindi", area="Saddar",           lat=33.5651, lng=73.0169, years_experience=13, profile_pic_url="https://randomuser.me/api/portraits/men/91.jpg"),
    dict(name="Ustad Munir Hassan",    phone="923011111115", service_type="electrician", city="rawalpindi", area="Bahria Town Rwp",  lat=33.5984, lng=73.0479, years_experience=9,  profile_pic_url="https://randomuser.me/api/portraits/men/3.jpg"),
]


async def seed_providers_if_empty() -> None:
    """Seeds 15 providers if the providers table is empty. Safe to call every startup."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await session.execute(select(Provider).limit(1))
        existing = result.scalars().first()
        if existing is not None:
            return  # Already seeded — skip

        for data in SEED_PROVIDERS:
            provider = Provider(
                name=data["name"],
                phone=data["phone"],
                service_type=ServiceType(data["service_type"]),
                city=data["city"],
                area=data["area"],
                lat=data["lat"],
                lng=data["lng"],
                years_experience=data["years_experience"],
                is_active=True,
                is_verified=False,
                rating_total=0.0,
                rating_count=0,
                total_jobs_done=0,
            )
            session.add(provider)

        await session.commit()


# ---------------------------------------------------------------------------
# Query helpers (all use session.execute() — SQLAlchemy 2.x AsyncSession API)
# ---------------------------------------------------------------------------


async def get_customer_by_phone(session: AsyncSession, phone: str) -> Customer | None:
    """Looks up a customer by E.164 phone. Returns None if not found."""
    result = await session.execute(select(Customer).where(Customer.phone == phone))
    return result.scalars().first()


async def register_customer(session: AsyncSession, phone: str, name: str) -> Customer:
    """Creates and persists a new customer row."""
    customer = Customer(phone=phone, name=name)
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer


async def fetch_available_providers(
    session: AsyncSession,
    service_type: ServiceType,
    lat: float,
    lng: float,
    city: str | None,
    limit: int = 5,
) -> list[ProviderCard]:
    """
    Finds active, unoccupied providers using Haversine distance ranking.

    Strategy:
    1. If city is provided → city-scoped query first.
    2. If city is None OR city-scoped result is empty → distance-only fallback.
    """
    active_statuses = ("pending", "accepted", "confirmed", "en_route", "arrived")
    placeholders = ", ".join(f"'{s}'" for s in active_statuses)

    base_select = f"""
        SELECT
            p.id,
            p.name,
            p.service_type,
            p.area,
            p.rating_total,
            p.rating_count,
            p.years_experience,
            p.total_jobs_done,
            p.is_verified,
            p.visit_fee,
            p.profile_pic_url,
            (6371 * acos(
                GREATEST(-1.0, LEAST(1.0,
                    cos(radians(:lat)) * cos(radians(p.lat)) *
                    cos(radians(p.lng) - radians(:lng)) +
                    sin(radians(:lat)) * sin(radians(p.lat))
                ))
            )) AS distance_km
        FROM providers p
        WHERE p.is_active = TRUE
          AND p.service_type = :service_type
          AND p.id NOT IN (
              SELECT provider_id FROM bookings
              WHERE status IN ({placeholders})
          )
    """

    params: dict = {
        "lat": lat,
        "lng": lng,
        "service_type": service_type.value,
        "limit": limit,
    }

    rows = []

    # City-scoped attempt
    if city:
        city_query = base_select + " AND p.city = :city ORDER BY distance_km LIMIT :limit"
        result = await session.execute(text(city_query), {**params, "city": city})
        rows = result.mappings().all()

    # Fallback: distance-only
    if not rows:
        fallback_query = base_select + " ORDER BY distance_km LIMIT :limit"
        result = await session.execute(text(fallback_query), params)
        rows = result.mappings().all()

    cards: list[ProviderCard] = []
    for row in rows:
        rating_total = row["rating_total"] or 0.0
        rating_count = row["rating_count"] or 0
        average_rating = (
            round(rating_total / rating_count, 1) if rating_count > 0 else None
        )
        cards.append(
            ProviderCard(
                id=row["id"],
                name=row["name"],
                service_type=ServiceType(row["service_type"]),
                area=row["area"],
                average_rating=average_rating,
                rating_count=rating_count,
                years_experience=row["years_experience"],
                total_jobs_done=row["total_jobs_done"],
                is_verified=bool(row["is_verified"]),
                distance_km=round(float(row["distance_km"]), 2),
                visit_fee=row["visit_fee"],
                profile_pic_url=row["profile_pic_url"],
            )
        )
    return cards


async def create_booking(
    session: AsyncSession,
    customer_id: int,
    provider_id: int,
    issue: str,
    lat: float,
    lng: float,
    city: str | None,
    service_type: ServiceType,
    idempotency_key: str,
    language: str = "roman_urdu",
) -> Booking:
    """
    Creates a booking with idempotency protection.
    Uses INSERT ... ON CONFLICT (idempotency_key) DO NOTHING.
    Returns the booking (existing or newly created).
    """
    if session.bind.dialect.name == "sqlite":
        # Check if booking already exists by idempotency key
        existing = await session.execute(
            select(Booking).where(Booking.idempotency_key == idempotency_key)
        )
        booking = existing.scalars().first()
        if booking:
            return await get_booking_with_relations(session, booking.id)

        # Create new booking
        booking = Booking(
            customer_id=customer_id,
            provider_id=provider_id,
            issue=issue,
            customer_lat=lat,
            customer_lng=lng,
            customer_city=city,
            service_type=service_type,
            status=BookingStatus.pending,
            idempotency_key=idempotency_key,
            language=language,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(booking)
        await session.flush()
        booking_id = booking.id
        await session.commit()
        return await get_booking_with_relations(session, booking_id)

    insert_sql = text("""
        INSERT INTO bookings
            (customer_id, provider_id, issue, customer_lat, customer_lng,
             customer_city, service_type, status, idempotency_key, language, created_at, updated_at)
        VALUES
            (:customer_id, :provider_id, :issue, :lat, :lng,
             :city, :service_type, 'pending', :idempotency_key, :language, NOW(), NOW())
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING id
    """)
    result = await session.execute(
        insert_sql,
        dict(
            customer_id=customer_id,
            provider_id=provider_id,
            issue=issue,
            lat=lat,
            lng=lng,
            city=city,
            service_type=service_type.value,
            idempotency_key=idempotency_key,
            language=language,
        ),
    )
    await session.commit()

    row = result.first()
    if row:
        booking_id = row[0]
    else:
        # Idempotency hit — fetch existing
        existing = await session.execute(
            select(Booking).where(Booking.idempotency_key == idempotency_key)
        )
        return existing.scalars().one()

    return await get_booking_with_relations(session, booking_id)


async def get_booking_with_relations(session: AsyncSession, booking_id: int) -> Booking:
    """Fetches a booking with customer and provider eagerly loaded."""
    result = await session.execute(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            selectinload(Booking.customer),   # type: ignore[arg-type]
            selectinload(Booking.provider),   # type: ignore[arg-type]
        )
    )
    return result.scalars().one()


async def update_booking(session: AsyncSession, booking_id: int, **kwargs) -> Booking:
    """Updates booking fields and sets updated_at to now."""
    booking = await get_booking_with_relations(session, booking_id)
    for key, value in kwargs.items():
        setattr(booking, key, value)
    booking.updated_at = datetime.utcnow()
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def submit_rating(
    session: AsyncSession, booking_id: int, rating: int, review: str | None
) -> None:
    """
    Atomically stores the customer rating on the booking and updates
    provider.rating_total and provider.rating_count.
    """
    booking = await get_booking_with_relations(session, booking_id)
    booking.customer_rating = rating
    booking.customer_review = review
    booking.updated_at = datetime.utcnow()
    session.add(booking)

    provider = booking.provider
    if provider:
        provider.rating_total = provider.rating_total + rating
        provider.rating_count = provider.rating_count + 1
        provider.updated_at = datetime.utcnow()
        session.add(provider)
    await session.commit()


async def get_latest_booking_for_customer(
    session: AsyncSession, phone: str
) -> Booking | None:
    """
    Returns the most recent non-cancelled booking for a customer phone.
    Used by the check_booking_status agent tool.
    """
    result = await session.execute(
        select(Booking)
        .join(Customer, Booking.customer_id == Customer.id)   # type: ignore[arg-type]
        .where(
            Customer.phone == phone,
            Booking.status != BookingStatus.cancelled,
        )
        .options(
            selectinload(Booking.customer),   # type: ignore[arg-type]
            selectinload(Booking.provider),   # type: ignore[arg-type]
        )
        .order_by(Booking.created_at.desc())  # type: ignore[arg-type]
        .limit(1)
    )
    return result.scalars().first()
