# Implementation Plan — Ustaad Connect

Build the **Ustaad Connect backend system** (FastAPI, Supabase PostgreSQL, Upstash Redis, OpenAI Agents SDK) using a **Single Specialized Agent (`Ustaad Agent`)** with customer registration, personalization, and real-time Meta WhatsApp Business API notifications.

---

## 🎯 Goal Description

Develop the end-to-end **Ustaad Connect** backend that:

- Receives customer requests (English / Urdu / Roman Urdu) via WhatsApp
- Dynamically checks and manages customer registration
- Greets registered customers by name
- Gathers service requirements and GPS location
- Dynamically matches unoccupied providers **within the same city first**, then ranked by Haversine distance
- Pushes bookings with GPS coordinates to the provider app
- Handles price estimates and customer confirmation
- Sends real-time WhatsApp messages to customers at every provider action (accept, en_route, arrived, completed)
- Tracks the full execution lifecycle

---

## ⚠️ User Review Required

> [!IMPORTANT]
> **1. Supabase (PostgreSQL):** Connect directly via `DATABASE_URL` in `.env`. No SQLite fallback.
>
> **2. Upstash Redis:** Use `RedisSession` from the OpenAI Agents SDK via `UPSTASH_REDIS_URL`. No local memory fallback.
>
> **3. Meta WhatsApp Business API:** All outbound messages to customers (booking confirmed, provider en route, arrived, completed) are sent via the Meta Cloud API. Requires `META_WHATSAPP_TOKEN` (Bearer token) and `META_PHONE_NUMBER_ID` in `.env`.
>
> **4. Environment Variables:** Ensure `OPENAI_API_KEY`, `DATABASE_URL`, `UPSTASH_REDIS_URL`, `META_WHATSAPP_TOKEN`, and `META_PHONE_NUMBER_ID` are all set.

---

## 📋 Environment Variables (`.env.example`)

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Supabase PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@db.supabase.co:5432/postgres

# Upstash Redis
UPSTASH_REDIS_URL=rediss://default:...@...upstash.io:6379

# Meta WhatsApp Business API
META_WHATSAPP_TOKEN=EAAxxxxxxxx
META_PHONE_NUMBER_ID=1234567890

# App
APP_SECRET=change_me_random_32_chars
```

---

## 📦 Dependencies (`pyproject.toml`)

```toml
[project]
name = "ustaad-connect"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
  "fastapi>=0.111.0",
  "uvicorn[standard]>=0.29.0",
  "sqlmodel>=0.0.19",             # SQLModel = SQLAlchemy + Pydantic in one — table models AND validation
  "asyncpg>=0.29.0",             # async PostgreSQL driver used by SQLModel's async engine
  "openai-agents>=0.0.9",         # OpenAI Agents SDK (pip name: openai-agents)
  "upstash-redis>=1.1.0",
  "httpx>=0.27.0",
  "python-dotenv>=1.0.0",
  "geopy>=2.4.1",                 # Nominatim reverse geocoding
]

# Note: SQLModel bundles SQLAlchemy 2.x and Pydantic 2.x — do NOT add them separately.
# pydantic is already a transitive dependency of sqlmodel.
```

> Run with: `uv run uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload`

---

## 🗂️ Project Structure

```
ustaad_connect/
├── src/
│   └── api/
│       ├── main.py
│       ├── models.py            # ALL SQLModel table models + Pydantic request/response schemas
│       ├── database.py          # engine, session factory, seed logic
│       ├── agent.py
│       ├── whatsapp.py          # Meta API helper
│       ├── geocoding.py         # reverse geocode lat/lng → city slug
│       └── routes/
│           ├── customer.py
│           └── provider.py
├── tests/
│   └── test_flow.py
├── .env
├── .env.example
└── pyproject.toml
```

---

## 🛠️ Proposed Changes

---

### [NEW] `src/api/whatsapp.py` — Meta WhatsApp Business API Helper

Single responsibility: send templated or freeform text messages to a customer's WhatsApp number via the Meta Cloud API.

**Functions:**

```python
async def send_whatsapp_message(to_phone: str, message: str) -> bool:
    """
    POST https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/messages
    Headers: Authorization: Bearer {META_WHATSAPP_TOKEN}
    Body: { "messaging_product": "whatsapp", "to": to_phone,
            "type": "text", "text": { "body": message } }
    Returns True on 200, logs and returns False on failure.
    Phone number must be in E.164 format: "923001234567"
    """
```

**Phone number normalisation:** Strip leading `+`, `0`, spaces. Always store and send in E.164 without the `+` (e.g. `923001234567`). Apply normalisation at registration time in `register_customer`.

**Error handling:** Wrap in `try/except httpx.HTTPError`. Log the error. Do NOT raise — a failed notification must never break the booking lifecycle.

---

### [NEW] `src/api/geocoding.py` — Reverse Geocode Coordinates → City Slug

Single responsibility: take a `(lat, lng)` pair and return a normalised city slug (e.g. `"islamabad"`, `"lahore"`, `"karachi"`) that matches the `city` column in the `providers` table.

**Implementation strategy — two-tier lookup:**

```python
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import AsyncRateLimiter

_geolocator = Nominatim(user_agent="ustaad-connect/1.0")
_reverse = AsyncRateLimiter(_geolocator.reverse, min_delay_seconds=1)

# Canonical slug map — normalise common Nominatim variants
CITY_SLUG_MAP = {
    "islamabad": "islamabad",
    "islamabad capital territory": "islamabad",
    "rawalpindi": "rawalpindi",
    "lahore": "lahore",
    "karachi": "karachi",
    "karachi city": "karachi",
    "faisalabad": "faisalabad",
    "multan": "multan",
    "peshawar": "peshawar",
    "quetta": "quetta",
}

async def reverse_geocode_city(lat: float, lng: float) -> str | None:
    """
    Returns a canonical city slug, e.g. "islamabad".
    Returns None if the city cannot be resolved or is not in CITY_SLUG_MAP.
    Caches results in Redis under key geocache:{lat:.4f}:{lng:.4f} with TTL 7 days.
    Falls back to None (triggers distance-only search) on any error.
    """
```

**Caching:** Before calling Nominatim, check Redis for `geocache:{lat:.4f}:{lng:.4f}`. On cache miss, call Nominatim, write result to Redis with `TTL=604800` (7 days). This avoids hammering the free Nominatim API on repeated requests from the same area.

**Fallback behaviour:** If reverse geocoding fails (network error, unknown city, Nominatim rate limit), `reverse_geocode_city` returns `None`. The caller (`fetch_available_providers`) must handle `None` gracefully — see query logic below.

---

### [NEW] `src/api/models.py` — SQLModel Table Models + Pydantic Schemas

All database tables are defined as **SQLModel** classes with `table=True`. Pydantic request/response schemas are plain `SQLModel` (or `BaseModel`) classes without `table=True`. One file, one source of truth.

---

#### Enums

```python
from enum import Enum

class ServiceType(str, Enum):
    ac_repair    = "ac_repair"
    plumber      = "plumber"
    electrician  = "electrician"

class BookingStatus(str, Enum):
    pending   = "pending"
    accepted  = "accepted"
    confirmed = "confirmed"
    en_route  = "en_route"
    arrived   = "arrived"
    completed = "completed"
    cancelled = "cancelled"

class CancelledBy(str, Enum):
    customer = "customer"
    provider = "provider"

# Valid forward-only transitions
BOOKING_TRANSITIONS: dict[BookingStatus, BookingStatus] = {
    BookingStatus.pending:   BookingStatus.accepted,
    BookingStatus.accepted:  BookingStatus.confirmed,
    BookingStatus.confirmed: BookingStatus.en_route,
    BookingStatus.en_route:  BookingStatus.arrived,
    BookingStatus.arrived:   BookingStatus.completed,
}
```

---

#### Table: `Customer`

```python
class Customer(SQLModel, table=True):
    __tablename__ = "customers"

    id         : int | None  = Field(default=None, primary_key=True)
    phone      : str         = Field(unique=True, index=True, max_length=20)
    # E.164 format, no leading +. e.g. "923001234567"

    name       : str         = Field(min_length=1, max_length=100)
    created_at : datetime    = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships (loaded lazily)
    bookings   : list["Booking"] = Relationship(back_populates="customer")
```

---

#### Table: `Provider`

Every field is documented — this is the most important table in the system.

```python
class Provider(SQLModel, table=True):
    __tablename__ = "providers"
    __table_args__ = (
        Index("idx_providers_city_service", "city", "service_type"),
    )

    id           : int | None  = Field(default=None, primary_key=True)

    # ── Identity ──────────────────────────────────────────────────────
    name         : str         = Field(min_length=2, max_length=100)
    phone        : str         = Field(max_length=20)
    # E.164, no +. Used to call/WhatsApp the provider directly.

    cnic         : str | None  = Field(default=None, max_length=15, unique=True)
    # Pakistani CNIC: "35202-1234567-1". Optional but recommended for identity verification.

    profile_pic_url : str | None = Field(default=None, max_length=500)
    # URL to provider's profile photo. Shown in customer-facing provider list.

    bio          : str | None  = Field(default=None, max_length=500)
    # Short self-description. e.g. "10 saal ka tajurba, G-13 mein service deta hoon"

    # ── Service & Location ────────────────────────────────────────────
    service_type : ServiceType = Field(index=True)
    # One of: ac_repair | plumber | electrician
    # A provider can only have one primary service type.
    # Multi-skill providers → separate rows (by design — simpler matching).

    city         : str         = Field(index=True, max_length=50)
    # Canonical city slug: "islamabad" | "lahore" | "karachi" | "rawalpindi" | "faisalabad"
    # Must match the slug returned by reverse_geocode_city().

    area         : str | None  = Field(default=None, max_length=100)
    # Human-readable sub-area. e.g. "G-13, Islamabad". Display only, not used for filtering.

    lat          : float       = Field()
    lng          : float       = Field()
    # Provider's home/base location. Used for Haversine distance ranking.

    # ── Availability ──────────────────────────────────────────────────
    is_active    : bool        = Field(default=True)
    # False = provider is disabled/suspended. Excluded from all availability queries.
    # Note: "busy" is NOT tracked here — it's inferred from active bookings in the query.

    # ── Ratings ───────────────────────────────────────────────────────
    rating_total    : float = Field(default=0.0)
    # Sum of all individual star ratings received (1–5 per booking).
    # Updated atomically with rating_count when a review is submitted.
    # average_rating = rating_total / rating_count  (computed, not stored)

    rating_count    : int   = Field(default=0)
    # Number of completed bookings that received a rating.
    # Use this as the denominator for average. Display as "4.7 ★ (23 reviews)".

    # ── Experience & Trust ────────────────────────────────────────────
    years_experience : int  = Field(default=0, ge=0, le=50)
    # Self-reported. Shown alongside name in provider card.

    total_jobs_done  : int  = Field(default=0)
    # Incremented automatically when a booking reaches "completed".
    # Distinct from rating_count — a job can complete without a rating.

    is_verified      : bool = Field(default=False)
    # Set to True after manual admin review of CNIC + in-person verification.
    # Shown as a "✓ Verified" badge in the app.

    # ── Timestamps ────────────────────────────────────────────────────
    joined_at    : datetime = Field(default_factory=datetime.utcnow)
    updated_at   : datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    bookings     : list["Booking"] = Relationship(back_populates="provider")

    # ── Computed property (Python-side, not stored) ───────────────────
    @property
    def average_rating(self) -> float | None:
        if self.rating_count == 0:
            return None
        return round(self.rating_total / self.rating_count, 1)
```

---

#### Table: `Booking`

```python
class Booking(SQLModel, table=True):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("idx_bookings_status", "status"),
        Index("idx_bookings_provider_status", "provider_id", "status"),
    )

    id           : int | None = Field(default=None, primary_key=True)

    # ── Relations ─────────────────────────────────────────────────────
    customer_id  : int        = Field(foreign_key="customers.id")
    provider_id  : int        = Field(foreign_key="providers.id")
    customer     : Customer   = Relationship(back_populates="bookings")
    provider     : Provider   = Relationship(back_populates="bookings")

    # ── Job Details ───────────────────────────────────────────────────
    issue        : str        = Field(max_length=500)
    # Free-text problem description from the agent conversation.
    # e.g. "AC cooling nahi kar raha, compressor ki awaz aa rahi hai"

    service_type : ServiceType = Field()
    # Denormalised from provider for faster reporting.

    # ── Location ──────────────────────────────────────────────────────
    customer_lat  : float     = Field()
    customer_lng  : float     = Field()
    customer_city : str | None = Field(default=None, max_length=50)
    # Resolved via reverse_geocode_city() at booking creation time.

    # ── Lifecycle ─────────────────────────────────────────────────────
    status        : BookingStatus = Field(default=BookingStatus.pending, index=True)

    # ── Pricing ───────────────────────────────────────────────────────
    estimated_cost_min : int | None = Field(default=None)
    estimated_cost_max : int | None = Field(default=None)
    # PKR. Set by the provider on /accept. Shown to customer for approval.

    final_cost         : int | None = Field(default=None)
    # PKR. Set by provider on /complete. The actual amount charged.
    # May differ from estimate (with customer consent).

    # ── Rating ────────────────────────────────────────────────────────
    customer_rating   : int | None = Field(default=None, ge=1, le=5)
    # 1–5 stars. Submitted by customer after job completes.
    # Triggers update of provider.rating_total and provider.rating_count.

    customer_review   : str | None = Field(default=None, max_length=300)
    # Optional text review alongside the star rating.

    # ── Idempotency ───────────────────────────────────────────────────
    idempotency_key   : str        = Field(unique=True, max_length=100)
    # Format: "{customer_phone}:{unix_timestamp}". Set by the agent at booking creation.

    # ── Timestamps ────────────────────────────────────────────────────
    created_at  : datetime = Field(default_factory=datetime.utcnow)
    updated_at  : datetime = Field(default_factory=datetime.utcnow)
```

---

#### Pydantic Request Schemas

These are **input validators** for API endpoints. They do NOT have `table=True`.

```python
# ── Customer ──────────────────────────────────────────────────────────────────

class CustomerChatRequest(SQLModel):
    phone          : str   = Field(pattern=r"^\d{10,15}$")
    # E.164 without +. Validated: 10–15 digits only.
    message        : str   = Field(max_length=2000)
    lat            : float | None = Field(default=None, ge=-90,  le=90)
    lng            : float | None = Field(default=None, ge=-180, le=180)
    idempotency_key: str | None   = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def lat_lng_both_or_neither(self) -> "CustomerChatRequest":
        if (self.lat is None) != (self.lng is None):
            raise ValueError("Provide both lat and lng, or neither.")
        return self


# ── Provider: Accept Booking ──────────────────────────────────────────────────

class BookingAcceptRequest(SQLModel):
    estimated_cost_min : int = Field(gt=0, le=1_000_000)
    estimated_cost_max : int = Field(gt=0, le=1_000_000)

    @model_validator(mode="after")
    def min_less_than_max(self) -> "BookingAcceptRequest":
        if self.estimated_cost_min > self.estimated_cost_max:
            raise ValueError("estimated_cost_min must be ≤ estimated_cost_max.")
        return self


# ── Provider: Advance Status ──────────────────────────────────────────────────

class BookingStatusRequest(SQLModel):
    status: BookingStatus
    # Only en_route | arrived | completed accepted here.
    # accepted and confirmed have their own dedicated endpoints.

    @field_validator("status")
    @classmethod
    def must_be_advanceable(cls, v: BookingStatus) -> BookingStatus:
        allowed = {BookingStatus.en_route, BookingStatus.arrived, BookingStatus.completed}
        if v not in allowed:
            raise ValueError(f"Use the dedicated endpoint for '{v}'.")
        return v


# ── Provider: Complete with Final Cost ────────────────────────────────────────

class BookingCompleteRequest(SQLModel):
    final_cost : int = Field(gt=0, le=1_000_000)
    # Actual amount charged. Required when marking a job completed.


# ── Customer: Submit Rating ───────────────────────────────────────────────────

class BookingRatingRequest(SQLModel):
    rating : int    = Field(ge=1, le=5)
    review : str | None = Field(default=None, max_length=300)


# ── Provider: Cancel Booking ──────────────────────────────────────────────────

class BookingCancelRequest(SQLModel):
    cancelled_by : CancelledBy
```

---

#### Pydantic Response Schemas

These control exactly what fields the API returns. Sensitive fields (e.g. CNIC) are excluded.

```python
# ── Provider card — shown to customer when choosing a provider ────────────────

class ProviderCard(SQLModel):
    """Minimal provider info returned in the agent's provider list."""
    id               : int
    name             : str
    service_type     : ServiceType
    area             : str | None
    average_rating   : float | None   # None if no ratings yet
    rating_count     : int
    years_experience : int
    total_jobs_done  : int
    is_verified      : bool
    distance_km      : float          # injected by fetch_available_providers query


class ProviderDetail(ProviderCard):
    """Full provider profile — returned on provider detail endpoint."""
    phone            : str
    bio              : str | None
    profile_pic_url  : str | None
    city             : str
    lat              : float
    lng              : float
    joined_at        : datetime
    # CNIC is intentionally excluded from all response schemas


# ── Booking responses ─────────────────────────────────────────────────────────

class BookingCreatedResponse(SQLModel):
    booking_id      : int
    status          : BookingStatus
    provider        : ProviderCard
    message         : str             # human-readable confirmation for the agent to relay

class BookingStatusResponse(SQLModel):
    booking_id      : int
    status          : BookingStatus
    whatsapp_sent   : bool

class ActiveJobResponse(SQLModel):
    """Returned to the provider app for the current active job."""
    booking_id           : int
    customer_name        : str
    customer_phone       : str
    issue                : str
    service_type         : ServiceType
    customer_lat         : float
    customer_lng         : float
    customer_city        : str | None
    status               : BookingStatus
    estimated_cost_min   : int | None
    estimated_cost_max   : int | None
    created_at           : datetime

class BookingAcceptResponse(SQLModel):
    booking_id           : int
    status               : BookingStatus   # "accepted"
    estimated_cost_min   : int
    estimated_cost_max   : int
    whatsapp_sent        : bool

class BookingCompleteResponse(SQLModel):
    booking_id           : int
    status               : BookingStatus   # "completed"
    final_cost           : int
    whatsapp_sent        : bool

class CustomerChatResponse(SQLModel):
    reply        : str
    session_id   : str

class ErrorResponse(SQLModel):
    error   : str
    detail  : str | None = None
```

---

### [NEW] `src/api/database.py`

Handles engine creation, session factory, table creation, and seeding. No raw SQL — uses SQLModel's `SQLModel.metadata.create_all()` for table creation and ORM inserts for seeding.

```python
from sqlmodel import create_engine, SQLModel, Session, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession

DATABASE_URL = os.environ["DATABASE_URL"]
# Must be postgresql+asyncpg://... for async support

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, pool_size=10)

async def init():
    """Called once at app startup via lifespan."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    await seed_providers_if_empty()

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
```

**Seed data** — 15 providers across 5 cities:

| name | service_type | city | area | lat | lng | years_exp |
|---|---|---|---|---|---|---|
| Ustad Riaz Ahmed | ac_repair | islamabad | G-13 | 33.6938 | 73.0512 | 12 |
| Ustad Khalid Mehmood | ac_repair | islamabad | E-11 | 33.7050 | 73.0234 | 8 |
| Ustad Farooq Ahmad | plumber | islamabad | F-11 | 33.6981 | 73.0601 | 15 |
| Ustad Imtiaz Khan | electrician | islamabad | G-11 | 33.7102 | 73.0389 | 10 |
| Ustad Nadeem Akhtar | plumber | islamabad | F-8 | 33.7215 | 73.0267 | 6 |
| Ustad Zafar Iqbal | ac_repair | lahore | DHA Phase 5 | 31.5204 | 74.3587 | 14 |
| Ustad Bilal Hussain | ac_repair | lahore | Gulberg III | 31.5497 | 74.3436 | 9 |
| Ustad Tariq Mahmood | plumber | lahore | Model Town | 31.5321 | 74.3290 | 11 |
| Ustad Asif Raza | electrician | lahore | Johar Town | 31.4697 | 74.4078 | 7 |
| Ustad Hamid Ali | plumber | lahore | Bahria Town | 31.4834 | 74.3251 | 5 |
| Ustad Saleem Baig | ac_repair | karachi | Clifton | 24.8607 | 67.0011 | 16 |
| Ustad Jameel Shah | electrician | karachi | Gulshan-e-Iqbal | 24.9056 | 67.0822 | 10 |
| Ustad Waqar Ahmed | plumber | karachi | PECHS | 24.8772 | 67.0650 | 8 |
| Ustad Asghar Butt | ac_repair | rawalpindi | Saddar | 33.5651 | 73.0169 | 13 |
| Ustad Munir Hassan | electrician | rawalpindi | Bahria Town Rwp | 33.5984 | 73.0479 | 9 |

> `seed_providers_if_empty()` runs `SELECT COUNT(*) FROM providers` first. If > 0, returns immediately — safe to call on every startup.

**Key async methods (all accept `AsyncSession`):**

- `get_customer_by_phone(session, phone)` → `Customer | None`
- `register_customer(session, phone, name)` → `Customer`
- `fetch_available_providers(session, service_type, lat, lng, city, limit=5)` → `list[ProviderCard]`
  — runs city-scoped Haversine query; falls back to city-less query if `city is None` or result set is empty
- `create_booking(session, customer_id, provider_id, issue, lat, lng, city, service_type, idempotency_key)` → `Booking`
  — uses `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING` via raw SQL for atomicity
- `get_booking_with_relations(session, booking_id)` → `Booking` with `customer` + `provider` eagerly loaded
- `update_booking(session, booking_id, **kwargs)` → `Booking` — sets `updated_at = utcnow()` automatically
- `submit_rating(session, booking_id, rating, review)` → atomically increments `provider.rating_total` and `provider.rating_count`

**Availability query (executed as raw SQL via `session.exec(text(...))`):**

```sql
-- City-scoped (used when city is not None)
SELECT p.*,
  (6371 * acos(
    cos(radians(:lat)) * cos(radians(p.lat)) *
    cos(radians(p.lng) - radians(:lng)) +
    sin(radians(:lat)) * sin(radians(p.lat))
  )) AS distance_km
FROM providers p
WHERE p.is_active = TRUE
  AND p.city = :city
  AND p.service_type = :service_type
  AND p.id NOT IN (
    SELECT provider_id FROM bookings
    WHERE status IN ('pending','accepted','confirmed','en_route','arrived')
  )
ORDER BY distance_km
LIMIT :limit;
```

> Fallback removes `AND p.city = :city`. Python selects which query to run.

---

### [NEW] `src/api/agent.py`

**Agent setup:**

```python
ustaad_agent = Agent(
    name="Ustaad Agent",
    instructions=USTAAD_INSTRUCTIONS,   # see below
    tools=[
        check_customer_exists,
        register_customer,
        get_service_categories,
        request_location,               # renamed — see note below
        fetch_available_providers,
        initiate_provider_booking,
        check_booking_status,           # tracks live provider status for the customer
        cancel_booking,
    ],
    session_factory=RedisSession(url=UPSTASH_REDIS_URL, ttl=86400),  # 24h TTL
)
```

> **Note on `request_whatsapp_location`:** Renamed to `request_location`. This tool now returns a structured response instructing the *route layer* to prompt the customer for coordinates. It does NOT call WhatsApp directly — that's the route's job. The agent's instructions tell it: "After calling `request_location`, wait for the next user message which will contain coordinates."

**Redis session key schema:** `session:{phone_number}` — one session per phone. TTL is 24 hours and resets on every message. Expired sessions restart the conversation from scratch (re-check registration).

---

#### Agent Tool: `check_booking_status`

Allows the agent to look up the **live status of the customer's most recent (or a specific) booking** so it can answer tracking questions like *"Where is the provider?"*, *"Has he left yet?"*, *"Kab tak aayega?"*.

```python
async def check_booking_status(
    booking_id: int | None = None,
    customer_phone: str | None = None,
) -> dict:
    """
    Returns the current lifecycle status of a booking plus human-readable
    context the agent can relay directly to the customer.

    Priority:
      - If booking_id is provided, fetch that specific booking.
      - If only customer_phone is provided, fetch the customer's most recent
        non-cancelled booking (ORDER BY created_at DESC LIMIT 1).

    Returns a dict with:
      {
        "booking_id"    : int,
        "status"        : str,          # one of the BookingStatus enum values
        "provider_name" : str,
        "provider_phone": str,          # E.164 for direct contact
        "service_type"  : str,
        "estimated_cost_min": int | None,
        "estimated_cost_max": int | None,
        "final_cost"    : int | None,
        "status_label"  : str,          # human-readable label in Urdu/Roman Urdu
        "created_at"    : str,          # ISO 8601
        "updated_at"    : str,          # ISO 8601 — when status last changed
      }

    status_label mapping:
      pending   → "Provider ka intezaar hai — abhi tak kisi ne accept nahi kiya."
      accepted  → "Provider ne booking accept kar li hai. Confirm hone ka intezaar karein."
      confirmed → "Booking confirm ho gayi. Provider aane ki tayyari kar raha hai."
      en_route  → "Provider aapki taraf aa raha hai! Thodi der mein pahunch jaega."
      arrived   → "Provider aapke ghar par pahunch gaya hai!"
      completed → "Kaam mukammal ho gaya. Final cost: PKR [final_cost]."
      cancelled → "Ye booking cancel ho gayi thi."

    Returns {"error": "No active booking found"} if nothing is found.
    """
```

**DB query for `customer_phone` lookup:**
```sql
SELECT b.*, p.name AS provider_name, p.phone AS provider_phone
FROM bookings b
JOIN customers c ON b.customer_id = c.id
JOIN providers p ON b.provider_id = p.id
WHERE c.phone = :phone
  AND b.status NOT IN ('cancelled')
ORDER BY b.created_at DESC
LIMIT 1;
```

> **Design decision:** The agent should always prefer resolving by `customer_phone` (available from the session context) rather than `booking_id`, since the customer never knows their booking ID. The `booking_id` param exists for precision when the agent has already stored the ID in session memory.

---

#### Provider App Button Taps → Backend API Mapping

The provider mobile app displays action buttons that change as the booking progresses. Each button tap calls the corresponding REST endpoint. The table below maps every button to its HTTP call:

| Provider App Button | HTTP Call | Request Body | Status After | WhatsApp Sent to Customer |
|---|---|---|---|---|
| **Accept Job** (with cost estimate) | `POST /api/provider/bookings/{id}/accept` | `BookingAcceptRequest` | `accepted` | ✅ Cost estimate + confirm prompt |
| **Confirm / Start Job** | `POST /api/provider/bookings/{id}/confirm` | _(none)_ | `confirmed` | 🔧 "Provider aa raha hai" |
| **I'm On My Way** | `POST /api/provider/bookings/{id}/status` | `{"status": "en_route"}` | `en_route` | 🚗 "Provider aa raha hai" |
| **I've Arrived** | `POST /api/provider/bookings/{id}/status` | `{"status": "arrived"}` | `arrived` | 📍 "Provider darwaze par hai" |
| **Mark Complete** (with final cost) | `POST /api/provider/bookings/{id}/complete` | `BookingCompleteRequest` | `completed` | ✅ Final cost + rating prompt |
| **Cancel Job** | `POST /api/provider/bookings/{id}/cancel` | `{"cancelled_by": "provider"}` | `cancelled` | ❌ Cancel notification |

> **Implementation note for the provider app:** The app should call `GET /api/provider/{provider_id}/active-job` on load to retrieve the current booking and its status, then render the appropriate next-action button based on the `status` field. Only the button for the *next valid transition* should be shown (not all buttons at once).

**Button visibility rules (client-side logic):**

| Current status from API | Button to show |
|---|---|
| `pending` | _(Booking just appeared — show Accept Job)_ |
| `accepted` | Confirm / Start Job |
| `confirmed` | I'm On My Way |
| `en_route` | I've Arrived |
| `arrived` | Mark Complete |
| `completed` | _(No action — show summary)_ |
| `cancelled` | _(No action — show cancelled notice)_ |

---

**`USTAAD_INSTRUCTIONS` (condensed spec):**

```
You are Ustaad Connect, a Pakistani home-services booking assistant.
You speak naturally in whichever language the customer uses — English, Urdu, or Roman Urdu.
You handle code-switching gracefully (e.g. "Mujhe AC ka issue hai, please help").

CUSTOMER REGISTRATION FLOW (mandatory first step):
1. On every conversation start, call check_customer_exists(phone_number).
2. If found → greet by name: "Assalam-o-Alaikum, [Name]! Kya haal hai? Kaise help kar sakta hoon?"
3. If not found → ask for name only. Then call register_customer(phone_number, name).

SERVICE BOOKING FLOW:
1. Understand the issue (AC, plumbing, electrical).
2. Call get_service_categories() to confirm the category slug.
3. Call request_location() — tell the customer to share their location pin.
4. Wait for the next message containing coordinates.
5. Call fetch_available_providers(service_type, lat, lng).
   — The system will auto-resolve the city from coordinates and filter providers accordingly.
   — If no providers found in city, the system falls back to nearest available regardless of city.
6. Present up to 3 providers with name + distance. Ask customer to choose.
7. Call initiate_provider_booking(...) with idempotency_key = f"{phone}:{timestamp}".
8. Confirm to customer: "Aapki booking ho gayi! Provider aapko jald contact karega."

PROVIDER TRACKING FLOW:
- If the customer asks anything like "provider kahan hai?", "has he left?", "kab aayega?",
  "what is the status?", "where is my ustad?" — call check_booking_status(customer_phone=phone).
- Read the returned status_label and relay it word-for-word (do not rephrase or invent details).
- If status is "en_route" or "arrived", reassure the customer: "App ne update kar diya hai, thodi
  der mein aapko WhatsApp update milegi."
- If status is "pending" for more than expected (>15 min), suggest the customer can cancel:
  "Agar zyada intezaar ho raha hai to main cancel kar sakta hoon — batayein?"

CANCELLATION:
- If the customer says "cancel", "band karo", "rehne do" — call cancel_booking(booking_id).

IMPORTANT: Never fabricate provider names, distances, or status details. Always use tool results.
```

---

### [NEW] `src/api/routes/customer.py`

**Endpoint:** `POST /api/customer/chat`

**Request body:**
```json
{
  "phone": "923001234567",
  "message": "AC theek nahi ho raha",
  "lat": null,
  "lng": null,
  "idempotency_key": "optional-client-uuid"
}
```

**Header:** `X-App-Secret: {APP_SECRET}` — validated on every request. Return 401 if missing/wrong.

**Logic:**
1. Validate `X-App-Secret` header.
2. If `lat` + `lng` are provided:
   a. Call `reverse_geocode_city(lat, lng)` → `city` slug (or `None`).
   b. Prepend a system message to agent context:
      `[SYSTEM: Location received — Lat: {lat}, Lng: {lng}, City: {city or "unknown"}]`
3. Load Redis session for `session:{phone}`.
4. Run agent with injected phone + city context.
5. Return agent text response.

**Response:**
```json
{
  "reply": "Assalam-o-Alaikum, Hammad! Kaise help kar sakta hoon?",
  "session_id": "session:923001234567"
}
```

---

### [UPDATED] `src/api/routes/provider.py`

All provider endpoints validate `X-App-Secret` header.

---

#### `GET /api/provider/{provider_id}/active-job`

Returns the current active booking for a provider (status not `completed` or `cancelled`).

Returns `ActiveJobResponse` (see models.py). Returns `404` if no active job.

---

#### `POST /api/provider/bookings/{booking_id}/accept`

Provider sets estimated cost range and accepts the booking.

**Request body:** `BookingAcceptRequest` (validated — min ≤ max, both > 0).

**Logic:**
1. Validate booking exists and status is `pending`.
2. Update booking: `status = "accepted"`, store `estimated_cost_min`, `estimated_cost_max`.
3. Fetch customer phone from booking.
4. **Call `send_whatsapp_message()`** with message:

```
✅ Aapki booking accept ho gayi!

Provider: [Provider Name]
Estimated Cost: PKR [min]–[max]
Status: Confirm karne ke liye reply karein "confirm" ya cancel karne ke liye "cancel".
```

5. Return `BookingAcceptResponse`.

---

#### `POST /api/provider/bookings/{booking_id}/confirm`

Provider confirms the job after customer acknowledges.

**Logic:**
1. Validate status is `accepted`.
2. Update status to `confirmed`.
3. **Call `send_whatsapp_message()`** with:

```
🔧 Booking confirmed! [Provider Name] aapke paas aa raha hai.
Agar koi sawal ho to humse rabta karein.
```

4. Return `BookingStatusResponse`.

---

#### `POST /api/provider/bookings/{booking_id}/status`

Provider advances lifecycle through `en_route` → `arrived`. Each triggers a WhatsApp message.

**Request body:** `BookingStatusRequest` (only `en_route` or `arrived` accepted here).

**Valid transitions and their WhatsApp messages:**

| New status | WhatsApp message to customer |
|---|---|
| `en_route` | `🚗 [Provider Name] aapki taraf aa raha hai! Thodi der mein pahunch jaenge.` |
| `arrived` | `📍 [Provider Name] aapke darwaze par hai! Darwaza khol dein.` |

**Logic:**
1. Validate the transition is legal using `BOOKING_TRANSITIONS` dict.
2. Update booking status + `updated_at`.
3. Call `send_whatsapp_message(customer_phone, message)`.
4. Return `BookingStatusResponse`.

**Rejected transitions** return `ErrorResponse` with HTTP 400.

---

#### `POST /api/provider/bookings/{booking_id}/complete`

Separated from `/status` because it requires `final_cost`.

**Request body:** `BookingCompleteRequest` (final_cost required).

**Logic:**
1. Validate status is `arrived`.
2. Update status to `completed`, store `final_cost`, increment `provider.total_jobs_done`.
3. **Call `send_whatsapp_message()`** with:

```
✅ Kaam mukammal ho gaya! [Provider Name] ne aapka masla hal kar diya.
Final Cost: PKR [final_cost]
Rating dene ke liye reply karein: "rate 5" ya "rate 4" (1–5 stars).
Shukriya Ustaad Connect use karne ka 🙏
```

4. Return `BookingCompleteResponse`.

---

#### `POST /api/customer/bookings/{booking_id}/rate`

Customer submits a star rating after job completion.

**Request body:** `BookingRatingRequest` (rating 1–5, optional review text).

**Logic:**
1. Validate booking status is `completed` and `customer_rating` is currently `None` (no double-rating).
2. Store `customer_rating` and `customer_review` on booking.
3. Call `submit_rating(session, booking_id, rating, review)` which atomically updates:
   - `provider.rating_total += rating`
   - `provider.rating_count += 1`
4. Return `BookingStatusResponse`.

---

#### `POST /api/provider/bookings/{booking_id}/cancel`

Either party cancels. Frees the provider.

**Request body:** `BookingCancelRequest` (`cancelled_by`: `"provider"` or `"customer"`).

**Logic:**
1. Validate status is not already `completed` or `cancelled`.
2. Update status to `cancelled`.
3. If `cancelled_by == "provider"`: notify customer via WhatsApp:
   `❌ Afsos, [Provider Name] aapki booking accept nahi kar saka. Hum aapko doosra provider dhundh rahe hain.`
4. If `cancelled_by == "customer"`: no WhatsApp message (they initiated it).
5. Return `BookingStatusResponse`.

---

### [NEW] `src/api/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init()          # creates tables, seeds providers if empty
    yield
    await database.close()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"])  # tighten in production
app.include_router(customer_router, prefix="/api/customer")
app.include_router(provider_router, prefix="/api/provider")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # log full traceback, return generic 500
    ...
```

---

## 📊 Booking Status Lifecycle

```
[Customer] → initiate_provider_booking → pending
                                             │
                              Provider: POST /accept          (BookingAcceptRequest)
                                             │
                                          accepted ──→ WhatsApp: cost estimate + confirm prompt
                                             │
                              Provider: POST /confirm
                                             │
                                          confirmed ──→ WhatsApp: "booking confirmed"
                                             │
                              Provider: POST /status {en_route}  (BookingStatusRequest)
                                             │
                                          en_route ──→ WhatsApp: "on the way"
                                             │
                              Provider: POST /status {arrived}   (BookingStatusRequest)
                                             │
                                          arrived ──→ WhatsApp: "at your door"
                                             │
                              Provider: POST /complete           (BookingCompleteRequest — final_cost required)
                                             │
                                          completed ──→ WhatsApp: "job done + final cost + rate prompt"
                                             │
                              Customer: POST /rate               (BookingRatingRequest — 1–5 stars)
                                             │
                                    provider.rating_total += stars
                                    provider.rating_count += 1

Any stage → POST /cancel (BookingCancelRequest) → cancelled ──→ WhatsApp (if provider cancelled)
```

---

## 🧪 Verification Plan

### Automated — `tests/test_flow.py`

1. **New customer registration**
   - POST `/api/customer/chat` `{ phone: "923001234567", message: "Hi" }`
   - Assert response asks for name
   - POST again with `{ message: "Hammad" }`
   - Assert `register_customer` was called; DB row exists

2. **Returning customer greeting**
   - POST from same number: `{ message: "AC theek nahi" }`
   - Assert reply contains "Hammad" (name personalisation)

3. **Location + city-scoped provider matching**
   - POST with `{ lat: 33.6938, lng: 73.0512, message: "" }` (Islamabad coords)
   - Assert `reverse_geocode_city` resolves to `"islamabad"`
   - Assert `fetch_available_providers` returns only providers with `city = "islamabad"`, ranked by distance
   - POST with `{ lat: 31.5204, lng: 74.3587, message: "" }` (Lahore coords)
   - Assert results contain only `city = "lahore"` providers

4. **Booking creation — idempotency**
   - Call `initiate_provider_booking` twice with same `idempotency_key`
   - Assert only one booking row created in DB

5. **Provider accept → WhatsApp sent**
   - POST `/api/provider/bookings/1/accept` with `BookingAcceptRequest { estimated_cost_min: 2000, estimated_cost_max: 4000 }`
   - Assert booking status = `accepted`
   - Assert `send_whatsapp_message` called with customer phone (mock/spy)
   - POST same request again → assert `BookingAcceptRequest` validator rejects min > max

6. **Status transitions → WhatsApp sent**
   - Advance through `en_route` → `arrived`
   - Assert WhatsApp called at each step with correct message
   - POST `/api/provider/bookings/1/complete` with `BookingCompleteRequest { final_cost: 3500 }`
   - Assert `booking.final_cost = 3500`, `provider.total_jobs_done` incremented
   - Assert WhatsApp message contains "PKR 3500"

7. **Rating flow**
   - POST `/api/customer/bookings/1/rate` with `BookingRatingRequest { rating: 5, review: "Bohat acha kaam kiya" }`
   - Assert `booking.customer_rating = 5`
   - Assert `provider.rating_total` and `provider.rating_count` updated
   - POST rating again → assert 400 (double-rating blocked)

7. **Invalid transition rejected**
   - POST status `{ status: "en_route" }` when current status is `arrived`
   - Assert `400` response

9. **Geocoding fallback**
   - Mock `reverse_geocode_city` to return `None`
   - Assert `fetch_available_providers` runs distance-only query (no city filter) and still returns results

10. **Cancellation**
    - POST `/api/provider/bookings/1/cancel` `{ cancelled_by: "provider" }`
    - Assert status = `cancelled`
    - Assert WhatsApp message sent to customer

### Multilingual test cases

- `"AC cooling nahi kar raha, G-13 mein"` — Roman Urdu
- `"مجھے پلمبر چاہیے"` — Urdu script
- `"I need an electrician please"` — English
- `"Yaar mera AC kharab hai, help karo"` — code-switched

Each should result in correct `service_type` classification by agent.

### Manual API verification

```bash
# 1. New customer
curl -X POST http://localhost:8000/api/customer/chat \
  -H "X-App-Secret: your_secret" \
  -H "Content-Type: application/json" \
  -d '{"phone":"923001234567","message":"Hi"}'

# 2. Returning customer with location (Islamabad) — resolves city, fetches city-scoped providers
curl -X POST http://localhost:8000/api/customer/chat \
  -H "X-App-Secret: your_secret" \
  -H "Content-Type: application/json" \
  -d '{"phone":"923001234567","message":"AC theek nahi","lat":33.6938,"lng":73.0512}'

# 2b. Same test from Karachi — should return only Karachi providers
curl -X POST http://localhost:8000/api/customer/chat \
  -H "X-App-Secret: your_secret" \
  -H "Content-Type: application/json" \
  -d '{"phone":"923009999999","message":"plumber chahiye","lat":24.8607,"lng":67.0011}'

# 3. Provider accepts (triggers WhatsApp to customer)
curl -X POST http://localhost:8000/api/provider/bookings/1/accept \
  -H "X-App-Secret: your_secret" \
  -H "Content-Type: application/json" \
  -d '{"estimated_cost_min":2000,"estimated_cost_max":4000}'

# 4. Provider goes en route (triggers WhatsApp)
curl -X POST http://localhost:8000/api/provider/bookings/1/status \
  -H "X-App-Secret: your_secret" \
  -H "Content-Type: application/json" \
  -d '{"status":"en_route"}'
```

---

## 🔐 Security Checklist

- [x] `X-App-Secret` header required on all endpoints
- [x] Phone number normalised to E.164 at registration (no `+`, no spaces) — `CustomerChatRequest` validates `pattern=r"^\d{10,15}$"`
- [x] `idempotency_key` on bookings prevents duplicate reservations
- [x] Provider double-booking prevented via `NOT IN (active bookings)` in availability query
- [x] City-scoped provider matching with automatic fallback to distance-only when geocoding fails
- [x] Reverse geocode results cached in Redis (`geocache:` prefix, TTL 7 days) — Nominatim rate limit protected
- [x] `send_whatsapp_message` failures are logged but never bubble up to break lifecycle
- [x] Redis session TTL = 24h (sessions auto-expire)
- [x] Only forward status transitions allowed — enforced via `BOOKING_TRANSITIONS` dict, returns `ErrorResponse` HTTP 400
- [x] `complete` endpoint separated from `status` — requires `final_cost` (validated > 0)
- [x] Double-rating blocked — `customer_rating IS NULL` checked before accepting a rating
- [x] `rating_total` / `rating_count` updated atomically — no partial updates
- [x] `BookingAcceptRequest` validates `min ≤ max` at the Pydantic layer before hitting DB
- [x] `idx_providers_city_service` composite index ensures city+service queries are fast
- [x] CNIC excluded from all Pydantic response schemas
- [ ] WhatsApp webhook signature verification (required for production Meta approval)
- [ ] Rate limiting on `/api/customer/chat` (recommended: 10 req/min per phone)