"""
whatsapp.py — Meta WhatsApp Business Cloud API helper.

Single responsibility: send a freeform text message to a phone number.
Failures are logged but never raised — a failed notification must never
break the booking lifecycle.
"""

from __future__ import annotations

import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v25.0"
META_WHATSAPP_TOKEN: str = os.getenv("META_WHATSAPP_TOKEN", "")
META_PHONE_NUMBER_ID: str = os.getenv("META_PHONE_NUMBER_ID", "")


async def send_whatsapp_message(to_phone: str, message: str) -> bool:
    """
    Sends a freeform text message to a WhatsApp number via the Meta Cloud API.

    Args:
        to_phone: E.164 format WITHOUT leading +. e.g. "923001234567"
        message:  Plain text body to send.

    Returns:
        True on HTTP 200, False on any failure (logged silently).
    """
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        logger.warning(
            "WhatsApp credentials not configured. "
            "Set META_WHATSAPP_TOKEN and META_PHONE_NUMBER_ID in .env"
        )
        return False

    url = f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info("WhatsApp message sent to %s", to_phone)
            return True

    except httpx.HTTPStatusError as exc:
        logger.error(
            "WhatsApp API returned %s for %s: %s",
            exc.response.status_code,
            to_phone,
            exc.response.text,
        )
        return False

    except httpx.HTTPError as exc:
        logger.error("WhatsApp network error for %s: %s", to_phone, exc)
        return False


async def send_whatsapp_audio(to_phone: str, media_id: str) -> bool:
    """
    Sends an audio message to a WhatsApp number via the Meta Cloud API.

    Args:
        to_phone: E.164 format WITHOUT leading +. e.g. "923001234567"
        media_id: The ID of the uploaded media on Meta's servers.

    Returns:
        True on HTTP 200, False on any failure.
    """
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        return False

    url = f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "audio",
        "audio": {"id": media_id},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info("WhatsApp audio sent to %s", to_phone)
            return True
    except httpx.HTTPError as exc:
        logger.error("WhatsApp audio send error for %s: %s", to_phone, exc)
        return False


async def download_whatsapp_media(media_id: str) -> bytes | None:
    """
    Downloads media from WhatsApp given a media ID.
    Requires two steps: 
    1. Get the media URL.
    2. Download the binary from the URL.
    """
    if not META_WHATSAPP_TOKEN:
        return None

    # Step 1: Get URL
    url = f"{META_GRAPH_URL}/{media_id}"
    headers = {"Authorization": f"Bearer {META_WHATSAPP_TOKEN}"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            media_info = response.json()
            media_url = media_info.get("url")
            
            if not media_url:
                logger.error("Media URL not found in response for media_id: %s", media_id)
                return None

            # Step 2: Download binary
            # The URL already contains access tokens, but Meta documentation 
            # specifies to include the Authorization header for this GET request as well.
            bin_response = await client.get(media_url, headers=headers)
            bin_response.raise_for_status()
            return bin_response.content
    except httpx.HTTPError as exc:
        logger.error("Failed to download media %s: %s", media_id, exc)
        return None


async def upload_whatsapp_media(file_bytes: bytes, mime_type: str = "audio/ogg") -> str | None:
    """
    Uploads media to WhatsApp and returns the new media ID.
    """
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        return None

    url = f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {META_WHATSAPP_TOKEN}"}
    
    # We must use multipart/form-data
    files = {
        "file": ("audio.ogg", file_bytes, mime_type)
    }
    data = {
        "messaging_product": "whatsapp"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, data=data, files=files)
            response.raise_for_status()
            result = response.json()
            return result.get("id")
    except httpx.HTTPError as exc:
        logger.error("Failed to upload media: %s", exc)
        return None


async def send_whatsapp_location_request(to_phone: str, body_text: str | None = None) -> bool:
    """
    Sends an interactive location request message to a WhatsApp number.
    Tapping this will open the user's location picker interface on their mobile device.

    Args:
        to_phone: E.164 format WITHOUT leading +. e.g. "923001234567"
        body_text: Custom text to display above the location button.

    Returns:
        True on success, False on failure.
    """
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        logger.warning(
            "WhatsApp credentials not configured. "
            "Set META_WHATSAPP_TOKEN and META_PHONE_NUMBER_ID in .env"
        )
        return False

    url = f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Predefined static text for all location requests if custom not provided
    if not body_text:
        body_text = "Apni location share krde take me apke liye qareebi providers dhoond sakon"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "interactive",
        "interactive": {
            "type": "location_request_message",
            "body": {
                "text": body_text
            },
            "action": {
                "name": "send_location"
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info("WhatsApp location request sent to %s", to_phone)
            return True

    except httpx.HTTPStatusError as exc:
        logger.error(
            "WhatsApp Location Request API returned %s for %s: %s",
            exc.response.status_code,
            to_phone,
            exc.response.text,
        )
        return False

    except httpx.HTTPError as exc:
        logger.error("WhatsApp Location Request network error for %s: %s", to_phone, exc)
        return False


async def send_whatsapp_interactive_buttons(
    to_phone: str,
    body_text: str,
    buttons: list[dict[str, str]],  # List of {"id": str, "title": str}
    header_text: str | None = None,
    footer_text: str | None = None,
) -> bool:
    """
    Sends interactive reply buttons to a WhatsApp user using the exact Meta Cloud API specification.
    Maximum of 3 buttons allowed.
    """
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        logger.warning(
            "WhatsApp credentials not configured. "
            "Set META_WHATSAPP_TOKEN and META_PHONE_NUMBER_ID in .env"
        )
        return False

    if not buttons or len(buttons) > 3:
        logger.error("Interactive reply buttons must contain between 1 and 3 items.")
        return False

    url = f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    # Construct standard Meta Cloud API interactive buttons payload
    interactive_payload: dict = {
        "type": "button",
        "body": {
            "text": body_text
        },
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {
                        "id": btn["id"],
                        "title": btn["title"]
                    }
                }
                for btn in buttons
            ]
        }
    }

    if header_text:
        interactive_payload["header"] = {
            "type": "text",
            "text": header_text
        }

    if footer_text:
        interactive_payload["footer"] = {
            "text": footer_text
        }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "interactive",
        "interactive": interactive_payload
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info("WhatsApp interactive buttons sent successfully to %s", to_phone)
            return True

    except httpx.HTTPStatusError as exc:
        logger.error(
            "WhatsApp Interactive Buttons API returned %s for %s: %s",
            exc.response.status_code,
            to_phone,
            exc.response.text,
        )
        return False

    except httpx.HTTPError as exc:
        logger.error("WhatsApp Interactive Buttons network error for %s: %s", to_phone, exc)
        return False


async def send_whatsapp_typing_indicator(message_id: str) -> bool:
    """Sends a 'typing...' indicator in response to a user message."""
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID or not message_id:
        return False

    url = f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
        "typing_indicator": {
            "type": "text"
        }
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, headers=headers, json=payload)
            return True
    except Exception:
        return False


async def send_whatsapp_interactive_carousel(
    to_phone: str,
    body_text: str,
    cards: list[dict],
) -> bool:
    """
    Sends an interactive media carousel message to a WhatsApp user.
    Between 2 and 10 cards must be provided.
    """
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        logger.warning(
            "WhatsApp credentials not configured. "
            "Set META_WHATSAPP_TOKEN and META_PHONE_NUMBER_ID in .env"
        )
        return False

    if not cards or len(cards) < 2 or len(cards) > 10:
        logger.error("Carousel must contain between 2 and 10 cards.")
        return False

    url = f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "interactive",
        "interactive": {
            "type": "carousel",
            "body": {
                "text": body_text
            },
            "action": {
                "cards": cards
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info("WhatsApp interactive carousel sent successfully to %s", to_phone)
            return True

    except httpx.HTTPStatusError as exc:
        logger.error(
            "WhatsApp Interactive Carousel API returned %s for %s: %s",
            exc.response.status_code,
            to_phone,
            exc.response.text,
        )
        return False

    except httpx.HTTPError as exc:
        logger.error("WhatsApp Interactive Carousel network error for %s: %s", to_phone, exc)
        return False

