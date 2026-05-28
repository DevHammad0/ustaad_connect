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

import sys
import logging

def configure_utf8_logging():
    """Force standard streams to UTF-8 and configure logging handlers with UTF-8 encoding."""
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    if sys.stderr.encoding != 'utf-8':
        try:
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # Ensure root has handler
    if not logging.root.handlers:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.encoding = "utf-8"
        stderr_handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s — %(message)s")
        )
        logging.basicConfig(
            level=logging.INFO,
            handlers=[stderr_handler],
        )

    # Force UTF-8 on all existing logger handlers (e.g. uvicorn, httpx, etc.)
    for logger_name in list(logging.root.manager.loggerDict.keys()):
        l = logging.getLogger(logger_name)
        for handler in l.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.encoding = 'utf-8'
    for handler in logging.root.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.encoding = 'utf-8'

# Run immediately
configure_utf8_logging()

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
from src.api.routes.admin import router as admin_router

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    configure_utf8_logging()  # Run again to catch any loggers configured by server (e.g., uvicorn)
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
app.include_router(admin_router)

# ---------------------------------------------------------------------------
# Image Upload → Supabase Storage
# ---------------------------------------------------------------------------
import os
import uuid
import httpx
from fastapi import UploadFile, File, HTTPException

_SUPABASE_URL    = os.getenv("SUPABASE_URL", "")
_SUPABASE_KEY    = os.getenv("SUPABASE_ANON_KEY", "")
_STORAGE_BUCKET  = os.getenv("SUPABASE_STORAGE_BUCKET", "provider-images")

# 5 MB hard limit (enforced server-side; bucket also enforces it)
_MAX_BYTES = 5 * 1024 * 1024
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


@app.post("/api/upload", tags=["system"])
async def upload_file(file: UploadFile = File(...)):
    """
    Receives a provider image, validates its type and size, then uploads it
    to Supabase Storage (provider-images bucket).  Returns the public URL.
    """
    # 1. Validate MIME type
    ct = file.content_type or ""
    if ct not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ct}'. Allowed: jpeg, png, webp.",
        )

    # 2. Read file and enforce size limit
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(data) // 1024} KB). Maximum allowed is 5 MB.",
        )

    # 3. Build a unique storage path
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    storage_path = f"profiles/{uuid.uuid4()}.{ext}"

    # 4. Upload to Supabase Storage REST API
    upload_url = f"{_SUPABASE_URL}/storage/v1/object/{_STORAGE_BUCKET}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {_SUPABASE_KEY}",
        "apikey": _SUPABASE_KEY,
        "Content-Type": ct,
        "x-upsert": "false",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(upload_url, content=data, headers=headers)

    if resp.status_code not in (200, 201):
        logger.error("Supabase storage upload failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="Image upload to storage failed.")

    # 5. Return the permanent public URL
    public_url = f"{_SUPABASE_URL}/storage/v1/object/public/{_STORAGE_BUCKET}/{storage_path}"
    return {"url": public_url}



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
