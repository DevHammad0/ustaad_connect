# Tasks — Ustaad Connect Backend

## Active

- [ ] **Phase 7 — Tests** - Create `tests/test_flow.py`
  - 10 test cases covering full lifecycle

## Waiting On

- [ ] **WhatsApp Webhook Integration** - Setup routes to receive messages from Meta
- [ ] **CORS Tightening** - Tighten allow_origins for production deployment

## Someday

- [ ] **Rate limiting** on `/api/customer/chat` (10 req/min per phone)
- [ ] **WhatsApp webhook signature verification** (required for Meta production approval)

## Done

- [x] **Phase 0 — Bootstrap** - Install all dependencies via `uv add`, add FastAPI entrypoint to pyproject.toml, create `.env.example` and `.env` stub
  - Installed: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `asyncpg`, `openai-agents`, `upstash-redis`, `httpx`, `python-dotenv`, `geopy`
  - Configured entrypoints and `.env.example`
- [x] **Phase 1 — Models** - Created `src/api/models.py` with SQLModel tables and Pydantic schemas
- [x] **Phase 2 — Database** - Created `src/api/database.py` with SQLAlchemy 2.0 AsyncSession, database pooler, 15 seeded providers in 5 cities, and query helpers
- [x] **Phase 3a — WhatsApp Helper** - Created `src/api/whatsapp.py` to send messages via Meta Cloud API
- [x] **Phase 3b — Geocoding** - Created `src/api/geocoding.py` with Nominatim rate-limiting and cached Canonical Pakistani City slugs (7-day TTL)
- [x] **Phase 4 — Agent** - Created `src/api/agent.py` with Ustaad Agent and 8 tools registered via `@function_tool`
- [x] **Phase 5a — Customer Route** - Created `src/api/routes/customer.py` supporting conversational agent and Upstash Redis memory persistence
- [x] **Phase 5b — Provider Routes** - Created `src/api/routes/provider.py` with active job details, booking confirmations, and status transitions
- [x] **Phase 6 — App Entry Point** - Created `src/api/main.py` with async lifespan, CORS middleware, global error handling, and `/health` check
- [x] **Real `.env` setup** - Verified Supabase session pooler, Upstash REST URL + Token integration, and OpenAI API Key connectivity
