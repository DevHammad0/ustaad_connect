"""
main.py — FastAPI application entry point.

Startup:
  - Creates all DB tables via SQLModel.metadata.create_all
  - Seeds 15 providers if the providers table is empty

Routers:
  - /api/customer  (customer.py)
  - /api/provider  (provider.py)

Run:
  uv run fastapi dev src/api/main.py
  uv run fastapi dev          (if [tool.fastapi] entrypoint is set in pyproject.toml)
"""

from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import database
from src.api.models import ErrorResponse
from src.api.routes.customer import router as customer_router
from src.api.routes.provider import router as provider_router
from src.api.routes.webhook import router as webhook_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    logger.info("Starting Ustaad Connect API...")
    await database.init()  # create tables + seed providers
    logger.info("Database ready.")
    yield
    logger.info("Shutting down...")
    await database.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


app = FastAPI(
    title="Ustaad Connect API",
    description=(
        "AI-powered home-services booking backend for Pakistan. "
        "Customers book via WhatsApp; providers update status via app buttons."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# CORS — tighten allow_origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(customer_router)
app.include_router(provider_router)
app.include_router(webhook_router)


# ---------------------------------------------------------------------------
# Health check (no auth required)
# ---------------------------------------------------------------------------


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Returns 200 OK. Use for load balancer / uptime checks."""
    return {"status": "ok", "service": "ustaad-connect"}


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled exceptions, logs full traceback, returns a safe 500."""
    logger.error(
        "Unhandled exception on %s %s:\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail="An unexpected error occurred. Please try again.",
        ).model_dump(),
    )
