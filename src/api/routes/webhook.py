"""
routes/webhook.py — Production-ready Meta WhatsApp Webhook integration.

Endpoints:
  GET  /webhook → Verification handshake with Meta Developer Portal
  POST /webhook → Incoming WhatsApp messages, location updates, and button clicks
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Set

from dotenv import load_dotenv
from fastapi import APIRouter, Query, Request, Response
from agents import Runner
from agents.extensions.memory import RedisSession
from upstash_redis.asyncio import Redis as UpstashRedis


# ---------------------------------------------------------------------------
# Upstash → redis-py pipeline compatibility adapter
# RedisSession calls `await pipe.execute()` but Upstash uses `await pipe.exec()`
# ---------------------------------------------------------------------------

class _CompatiblePipeline:
    """Wraps an Upstash AsyncPipeline to expose the redis-py `.execute()` API."""

    def __init__(self, pipe) -> None:
        self._pipe = pipe

    def __getattr__(self, name: str):
        return getattr(self._pipe, name)

    async def execute(self) -> list:
        return await self._pipe.exec()


class _CompatibleRedis(UpstashRedis):
    """Upstash async Redis client whose `.pipeline()` returns a redis-py-compatible wrapper."""

    def pipeline(self):
        return _CompatiblePipeline(super().pipeline())


class UstaadRedisSession(RedisSession):
    """RedisSession subclass that removes default key prefixes and stores history directly under the phone number."""

    def __init__(self, session_id: str, *args, **kwargs) -> None:
        super().__init__(session_id, *args, **kwargs)
        self._session_key = f"{session_id}:counter"
        self._messages_key = session_id

from src.api.agent import ustaad_agent
from src.api.whatsapp import send_whatsapp_message, send_whatsapp_typing_indicator
from src.api.geocoding import reverse_geocode_city

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])

WHATSAPP_MAX_MSG_LENGTH = 4096
META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "ustaad_verify_token")

# Google Cloud Tasks Config
USE_CLOUD_TASKS: bool = os.getenv("USE_CLOUD_TASKS", "false").lower() == "true"
GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")
GCP_TASKS_QUEUE_NAME: str = os.getenv("GCP_TASKS_QUEUE_NAME", "whatsapp-queue")
WORKER_BASE_URL: str = os.getenv("WORKER_BASE_URL", "").rstrip("/")

def _enqueue_task_to_gcp(body: dict) -> None:
    """Enqueues the webhook JSON body as a task in Google Cloud Tasks."""
    from google.cloud import tasks_v2
    client = tasks_v2.CloudTasksClient()
    
    parent = client.queue_path(GCP_PROJECT_ID, GCP_REGION, GCP_TASKS_QUEUE_NAME)
    url = f"{WORKER_BASE_URL}/webhook/worker"
    
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body).encode("utf-8"),
        }
    }
    
    response = client.create_task(request={"parent": parent, "task": task})
    logger.info("Successfully enqueued task to Google Cloud Tasks: %s", response.name)

# Async Upstash Redis client — conversation history stored directly via RedisSession
_redis = _CompatibleRedis.from_env()
CONV_TTL = 10800  # 3 hours

# Simple in-memory deduplication set to prevent reprocessing duplicate webhook events
_seen_message_ids: Set[str] = set()
_MAX_SEEN = 10000


def _already_processed(msg_id: str) -> bool:
    """Returns True if we've already processed this message ID."""
    if not msg_id:
        return False
    if msg_id in _seen_message_ids:
        return True
    if len(_seen_message_ids) >= _MAX_SEEN:
        _seen_message_ids.clear()
    _seen_message_ids.add(msg_id)
    return False


# ---------------------------------------------------------------------------
# GET /webhook — Meta Verification Handshake
# ---------------------------------------------------------------------------

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> Response:
    """
    Confirms hub.verify_token matches the META_VERIFY_TOKEN env variable
    and echoes hub.challenge back to Meta to register the webhook.
    """
    if hub_mode == "subscribe" and hub_verify_token == META_VERIFY_TOKEN:
        logger.info("WhatsApp Webhook verified successfully!")
        return Response(content=hub_challenge, media_type="text/plain", status_code=200)

    logger.warning("WhatsApp Webhook verification failed — token mismatch")
    return Response(content="Forbidden", status_code=403)


# ---------------------------------------------------------------------------
# POST /webhook — Event Delivery
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def receive_webhook(request: Request) -> Response:
    """
    Acknowledge the event immediately with HTTP 200 to prevent Meta retries.
    If USE_CLOUD_TASKS is enabled, enqueues the payload to Google Cloud Tasks.
    Otherwise, processes it in the background.
    """
    try:
        body = await request.json()
    except Exception:
        logger.error("Failed to parse JSON body from incoming webhook")
        return Response(content="Invalid JSON", status_code=400)

    if USE_CLOUD_TASKS:
        try:
            _enqueue_task_to_gcp(body)
            return Response(content="OK (Queued)", status_code=200)
        except Exception:
            logger.exception("Failed to enqueue task to Cloud Tasks, falling back to direct background execution")
            # Fallback to direct background execution if Cloud Tasks enqueuing fails
            asyncio.create_task(_process_webhook_body(body))
            return Response(content="OK (Fallback Direct)", status_code=200)
    else:
        # Process in the background using asyncio.create_task to return 200 OK instantly to Meta
        asyncio.create_task(_process_webhook_body(body))
        return Response(content="OK", status_code=200)


@router.post("/webhook/worker")
async def receive_webhook_worker(request: Request) -> Response:
    """
    Background worker endpoint triggered by Google Cloud Tasks.
    Processes the WhatsApp webhook payload asynchronously relative to the client.
    """
    try:
        body = await request.json()
    except Exception:
        logger.error("Failed to parse JSON body in webhook worker")
        return Response(content="Invalid JSON", status_code=400)

    # Process in the background using asyncio.create_task to return 200 OK instantly to Cloud Tasks
    asyncio.create_task(_process_webhook_body(body))
    return Response(content="OK", status_code=200)


# ---------------------------------------------------------------------------
# Background Processing
# ---------------------------------------------------------------------------

async def _process_webhook_body(body: dict) -> None:
    """Extract messages from the WhatsApp JSON payload and process each one."""
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                if "messages" not in value:
                    continue

                contacts = {
                    c["wa_id"]: c.get("profile", {}).get("name", "Customer")
                    for c in value.get("contacts", [])
                }

                for msg in value["messages"]:
                    await _handle_message(msg, contacts)
    except Exception:
        logger.exception("Error processing WhatsApp webhook payload")


async def _handle_message(msg: dict, contacts: dict) -> None:
    """Process a single incoming WhatsApp message, location share, or button reply."""
    msg_id = msg.get("id", "")
    msg_type = msg.get("type", "")
    sender = msg.get("from", "")
    sender_name = contacts.get(sender, "Customer")

    if not sender:
        return

    if _already_processed(msg_id):
        logger.debug("Skipping duplicate WhatsApp message ID: %s", msg_id)
        return

    user_message = ""

    if msg_type == "text":
        user_message = msg.get("text", {}).get("body", "").strip()

    elif msg_type == "interactive":
        interactive = msg.get("interactive", {})
        interactive_type = interactive.get("type")

        if interactive_type == "list_reply":
            user_message = interactive.get("list_reply", {}).get("title", "")
        elif interactive_type == "button_reply":
            user_message = interactive.get("button_reply", {}).get("title", "")

    elif msg_type == "location":
        # Extract native GPS coordinates shared by tapping the button
        location_data = msg.get("location", {})
        lat = location_data.get("latitude")
        lng = location_data.get("longitude")

        if lat is not None and lng is not None:
            location_info = await reverse_geocode_city(lat, lng)
            city_slug = location_info.get("slug")
            full_address = location_info.get("address")
            
            city_label = city_slug or "unknown"
            address_label = full_address or "unknown"
            
            # Format as a system context note so the agent parses coordinates successfully
            user_message = (
                f"[SYSTEM: Location received — "
                f"Lat: {lat}, Lng: {lng}, Full Address: {address_label}, "
                f"City Database Filter: {city_label}]\n\n"
                "I have shared my current GPS location."
            )
            logger.info("GPS coordinates parsed from webhook for %s: lat=%s, lng=%s, city=%s, address=%s", sender, lat, lng, city_label, address_label)

    if not user_message:
        logger.info("Ignoring unsupported WhatsApp message type: %s from: %s", msg_type, sender)
        return

    # Dynamically inject customer phone number and message type into input
    system_info = f"[System Info: Customer Phone is {sender}, Message Type is {msg_type}]"
    user_message = f"{user_message}\n\n{system_info}"

    logger.info("WhatsApp incoming message from %s (%s): %s", sender_name, sender, user_message.replace("\n", " "))

    try:
        # Per-customer RedisSession — full history stored in Upstash, rolling 3-hour TTL
        session = UstaadRedisSession(
            session_id=sender,
            redis_client=_redis,
            ttl=CONV_TTL,
        )

        # Show typing indicator while agent thinks
        await send_whatsapp_typing_indicator(msg_id)

        # Execute conversation with Ustaad Agent
        result = await Runner.run(
            ustaad_agent,
            input=user_message,
            session=session,
            context={"phone": sender},
        )

        reply = result.final_output or "Maafi chahta hoon, kuch masla aa gaya. Dobara try karein."

    except Exception:
        logger.exception("Ustaad Agent processing failure for phone: %s", sender)
        reply = "Sorry, systems mein kuch masla aa gaya hai. Bara-e-maharbani thodi der baad dobara try karein."

    # Dispatch final response back to WhatsApp
    await _send_reply(sender, reply)


async def _send_reply(to_phone: str, text: str) -> None:
    """Send WhatsApp reply, safely splitting into multiple chunks if it exceeds Meta's limit."""
    chunks = _split_message(text, WHATSAPP_MAX_MSG_LENGTH)
    for chunk in chunks:
        try:
            await send_whatsapp_message(to_phone, chunk)
        except Exception:
            logger.exception("Failed to send WhatsApp message chunk to: %s", to_phone)


def _split_message(text: str, max_len: int) -> list[str]:
    """Split a long message into safe chunks without cutting words or newlines."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    return chunks
