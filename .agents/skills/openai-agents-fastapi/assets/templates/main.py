"""
Template: main.py

FastAPI application entry point with lifespan, CORS, and health check.
Copy into your project (e.g. src/api/main.py) and import your agent routers.

Run:
    uvicorn src.api.main:app --reload
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Import your agent routers here, e.g.:
#   from .routers.order_bot import router as order_router
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: validate config. Shutdown: log graceful stop."""
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Add it to your .env file or export it before starting the server."
        )

    logger.info("Starting agent API server")
    yield
    logger.info("Agent API server shut down")


app = FastAPI(
    title="Agent API",
    description="FastAPI server exposing OpenAI Agents SDK agents over HTTP with SSE streaming.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — restrict allow_origins in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include agent routers, e.g.:
#   app.include_router(order_router)
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    """Health check — returns 200 when the server is running."""
    return {"status": "ok"}
