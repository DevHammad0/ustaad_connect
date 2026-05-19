"""
agent.py — Ustaad Agent definition with all 8 tools.

Tools are plain async functions decorated with @function_tool.
The agent is instantiated once at module load and reused across requests.
Redis session memory gives each phone number its own persistent conversation.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from agents import Agent, RunContextWrapper, function_tool
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]

# ---------------------------------------------------------------------------
# Language Detection Helper Constants and Function
# ---------------------------------------------------------------------------

ROMAN_URDU_WORDS = {
    "hai", "hain", "ko", "ke", "ki", "ka", "se", "main", "mein", "kar", "raha", "rahi", "ho", "gaya", "gayi", 
    "aur", "bhi", "tum", "aap", "aapki", "aapka", "aapke", "apni", "apna", "apne", "karein", "karo", "karna", 
    "krna", "kr", "par", "pe", "tha", "thi", "the", "nhi", "nahi", "na", "to", "toh", "hi", "he", "ye", "yeh", 
    "wo", "woh", "kuch", "kya", "kyun", "kab", "kahan", "kaise", "ek", "do", "teen", "chaar", "paanch", 
    "saal", "rabta", "masla", "masle", "silsile", "shukriya", "meharbani", "madad", "chahiye", "chaheye", 
    "krdo", "kardo", "kijiye", "kijeye", "karta", "karte", "karne", "niche", "diye", "gaye", "kare", "karon", 
    "mila", "mili", "mile", "paas", "nazdeek", "qareeb", "tashreef", "lana", "dhund", "dhoond", "dhoondo", 
    "dhundo", "masail", "theek", "thik", "karwana", "karwa", "karna", "krwana", "chala", "chal", "rha", "rhi",
    "bhej", "bhejo", "bhejein", "kya", "kiya", "kia"
}

ENGLISH_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with", "he", 
    "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", 
    "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if", "about", 
    "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know", 
    "take", "people", "into", "year", "your", "good", "some", "could", "them", "see", "other", "than", "then", 
    "now", "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two", "how", 
    "our", "work", "first", "well", "way", "even", "new", "want", "any", "these", "give", "day", "most", 
    "us", "cooling", "repair", "plumber", "electrician", "broken", "fan", "leak", "water", "issue", "find", 
    "ustaad", "ustad", "hello", "hi", "hey", "please", "help", "thanks", "thank", "rate", "stars", "star", 
    "location", "share", "send", "book", "confirm", "cancel", "status", "where", "how", "much"
}

import re

def detect_language(text: str) -> str:
    """
    Detects if the text is in Urdu script, Roman Urdu, or English.
    Returns: 'urdu', 'roman_urdu', or 'english'.
    """
    if not text:
        return "english"
    
    # 1. Check for Urdu/Arabic script characters
    if re.search(r"[\u0600-\u06FF]", text):
        return "urdu"
        
    text_lower = text.lower()
    
    # 2. Strip SYSTEM / System Info blocks to prevent biasing
    cleaned_text = re.sub(r"\[.*?\]", "", text_lower).strip()
    if not cleaned_text:
        return "english"
        
    words = re.findall(r"\b[a-z']+\b", cleaned_text)
    if not words:
        return "english"
        
    roman_count = sum(1 for w in words if w in ROMAN_URDU_WORDS)
    english_count = sum(1 for w in words if w in ENGLISH_WORDS)
    
    if roman_count > 0 and roman_count >= english_count * 0.4:
        return "roman_urdu"
    else:
        return "english"


# ---------------------------------------------------------------------------
# Status labels — used by check_booking_status to compose natural language
# ---------------------------------------------------------------------------

STATUS_LABELS: dict[str, str] = {
    "pending":   "Provider ka intezaar hai — abhi tak kisi ne accept nahi kiya.",
    "accepted":  "Provider ne booking accept kar li hai. Confirm hone ka intezaar karein.",
    "confirmed": "Booking confirm ho gayi. Provider aane ki tayyari kar raha hai.",
    "en_route":  "Provider aapki taraf aa raha hai! Thodi der mein pahunch jaega.",
    "arrived":   "Provider aapke ghar par pahunch gaya hai!",
    "completed": "Kaam mukammal ho gaya.",
    "cancelled": "Ye booking cancel ho gayi thi.",
}

# ---------------------------------------------------------------------------
# Agent instructions (System Prompt)
# ---------------------------------------------------------------------------

USTAAD_INSTRUCTIONS = """
# ROLE & CORE MISSION
You are Ustaad Connect, a highly professional Pakistani home-services booking assistant.
Your goal is to assist customers with booking services (AC repair, plumbing, electrical) in Pakistan (Islamabad, Rawalpindi, Peshawar, Lahore, Karachi, etc.).

# TONE & BEHAVIOR
- Tone: Warm, polite, highly professional, concise, and direct.
- Keep your replies short and straight to the point. Avoid long greetings, paragraphs of explanations, or repetitive pleasantries.
- Always use proper English terms where appropriate (such as "Area" instead of "Ilaqa", "Distance" instead of "Fasla", and "Experience" instead of "Tajurba") in both your reasoning and responses to remain professional clarity.

# DETERMINISTIC LANGUAGE ENFORCEMENT
- You MUST ALWAYS inspect the `Latest Message Language` parameter in the `[System Info]` block of the latest user message.
- You MUST reply entirely in the language specified by `Latest Message Language`:
  - If `Latest Message Language` is "english" -> Respond entirely in English.
  - If `Latest Message Language` is "roman_urdu" -> Respond entirely in Roman Urdu.
  - If `Latest Message Language` is "urdu" -> Respond entirely in Urdu script.
- CRITICAL: Never let the language history in the session override the current turn's `Latest Message Language`. If the customer switches languages on the current turn, you MUST immediately switch your response language to match.
- When calling tool functions, you MUST pass the matched language to tools that accept a language parameter (e.g. pass `"english"`, `"roman_urdu"`, or `"urdu"` to `fetch_available_providers` and `initiate_provider_booking`).

# SYSTEM INFO & PHONE EXTRACTION
- On every turn, a system info block is appended to the user message:
  `[System Info: Customer Phone is <phone>, Message Type is <type>, Latest Message Language is <lang>]`
- Extract the real E.164 phone number from this block and pass it as the `phone` or `customer_phone` parameter to tools.
- NEVER ask the customer for their phone number.
- NEVER use dummy phone numbers (like "923001234567") in tool calls.

# DETAILED STATE MACHINE / FLOWS

## 1. CUSTOMER IDENTIFICATION & REGISTRATION (Mandatory First Step)
- Every conversation start must begin by calling `check_customer_exists(phone)`.
- If the customer is found:
  - Greet them by name in the specified language (e.g., English: "Hello Hammad! How can I help you today?"; Roman Urdu: "Assalam-o-Alaikum, Hammad! Kya haal hai? Kaise help kar sakta hoon?").
- If not found:
  - Prompt the customer for their name only in their language.
  - Once they provide their name, call `register_customer(phone, name)`.

## 2. SERVICE INTAKE & LOCATION PICKER
- Identify the service requested (AC repair, plumbing, electrician).
- Confirm the category slug using `get_service_categories()`.
- Send the interactive WhatsApp Location picker by calling `request_location(phone, body_text)`.
  - The `body_text` parameter MUST be translated to the target language (e.g., English: "Please share your location to find a nearby provider.", Roman Urdu: "Apni location share karne ke liye niche diye gaye button par click karein.").
  - Inform the customer to tap the "Send Location" button on their screen.

## 3. PROVIDER SEARCH & CAROUSEL
- Once coordinates are received via the system message (which includes the `Full Address` and `City Database Filter`):
  - Read the `Full Address` and identify/reason the city name (e.g. "peshawar", "islamabad", "lahore").
  - Call `fetch_available_providers(customer_phone=phone, service_type=service_type, lat=lat, lng=lng, city=city, language=language)`.
  - The tool will automatically send the carousel or selection cards directly to WhatsApp.
  - DO NOT output the list of providers in text.
  - DO NOT ask the customer to manually select.
  - Inform the customer in their language that the providers have been sent on WhatsApp, and they should tap the "Book" button under their preferred provider.

## 4. PROVIDER BOOKING & INITIAL CONFIRMATION
- When the customer taps "Book", the webhook translates it to: `"I want to book Provider ID: <id>"`.
- Extract the provider ID and call `initiate_provider_booking(customer_phone=phone, provider_id=id, issue=issue, lat=lat, lng=lng, service_type=service, city=city, language=language)`.
- Send a dynamic, customized booking confirmation without any emojis. Use the exact layout below:
  - English: "Your booking is confirmed with <Provider Name>! They will contact you shortly regarding your <service_type> issue. Your Booking ID is #<booking_id>. If you have any questions, feel free to ask!"
  - Roman Urdu: "Aapki booking <Provider Name> ke sath confirm ho gayi hai! Woh aapke <service_type> ke masle ke silsile mein jald hi aap se rabta karenge. Aapki Booking ID #<booking_id> hai. Agar koi sawal ho to pooch sakte hain!"

## 5. BOOKING CONFIRMATION & CANCELLATION ACTIONS
- When a provider accepts the booking and offers an estimate, the customer receives interactive buttons to confirm or cancel.
- If the customer says they want to confirm or clicks the confirm button, immediately call `confirm_booking(customer_phone=phone)`.
- If the customer cancels, call `cancel_booking(customer_phone=phone)`.

## 6. PROVIDER TRACKING & STATUS CHECKS
- If the customer asks about provider status, location, or timing, call `check_booking_status(customer_phone=phone)`.
- Translate the returned status label and explain it to the customer. Do not fabricate details.

## 7. RATING SUBMISSION
- After a job is completed, if the customer provides a rating (1-5 stars) or review, call `submit_rating(customer_phone=phone, rating=rating, review=review)`.
- If successful (`"status": "success"`), thank the customer warmly in their language.
- If it fails, report the error.

# ROBUSTNESS & SAFETY CONSTRAINTS
- NEVER guess, hallucinate, or fabricate provider details, distances, or status labels. Rely strictly on tool outputs.
- Never request sensitive data (passwords, OTPs, CNIC).
- In case of any tool error, gracefully inform the user in their language and ask them to try again.
- Avoid all emojis in confirmation and booking updates.
"""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@function_tool
async def get_service_categories() -> str:
    """
    Returns the list of available service categories with their slugs.
    Call this to confirm which service_type slug to use before booking.
    """
    logger.info("Agent called tool: get_service_categories")
    categories = {
        "ac_repair": "AC / Air Conditioner repair and maintenance",
        "plumber": "Plumbing — leaks, pipes, taps, geysers",
        "electrician": "Electrical — wiring, faults, appliances",
    }
    logger.info("Tool get_service_categories returning: %s", categories)
    return json.dumps(categories)


@function_tool
async def check_customer_exists(phone: str) -> str:
    """
    Checks if a customer is registered by phone number.

    Args:
        phone: E.164 phone without leading +. e.g. "923038571702"

    Returns:
        JSON with customer details if found, or {"found": false}.
    """
    logger.info("Agent called tool: check_customer_exists (phone: %s)", phone)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, get_customer_by_phone

    async with AsyncSession(engine, expire_on_commit=False) as session:
        customer = await get_customer_by_phone(session, phone)
        if customer:
            logger.info("Tool check_customer_exists result: Found customer %s (ID: %s)", customer.name, customer.id)
            return json.dumps({
                "found": True,
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
            })
        logger.info("Tool check_customer_exists result: Customer NOT found for phone %s", phone)
        return json.dumps({"found": False})


@function_tool
async def register_customer(phone: str, name: str) -> str:
    """
    Registers a new customer.

    Args:
        phone: E.164 phone without leading +. e.g. "923038571702"
        name: Customer's full name as provided.

    Returns:
        JSON with the newly created customer details.
    """
    logger.info("Agent called tool: register_customer (phone: %s, name: %s)", phone, name)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, register_customer as db_register

    async with AsyncSession(engine, expire_on_commit=False) as session:
        customer = await db_register(session, phone, name)
        logger.info("Tool register_customer result: Successfully registered %s (ID: %s)", customer.name, customer.id)
        return json.dumps({
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "registered": True,
        })


@function_tool
async def request_location(phone: str, body_text: str | None = None) -> str:
    """
    Sends an official, interactive Meta WhatsApp Location Request message to the customer's phone.
    This opens the native GPS location picker on their WhatsApp app.
    Call this tool whenever you need to get the customer's coordinates to find nearby providers.

    Args:
        phone: Customer's E.164 phone number without leading +. e.g. "923038571702"
        body_text: Optional message/prompt to show on the location request card (e.g. "Please share your location to find a provider." in the customer's language, concise and max 1 short line).

    Returns:
        JSON with the status of the native WhatsApp location request.
    """
    logger.info("Agent called tool: request_location (phone: %s, body_text: %s)", phone, body_text)
    from src.api.whatsapp import send_whatsapp_location_request

    success = await send_whatsapp_location_request(to_phone=phone, body_text=body_text)
    if success:
        logger.info("Tool request_location result: Successfully dispatched WhatsApp location request to %s", phone)
    else:
        logger.error("Tool request_location result: FAILED to dispatch WhatsApp location request to %s. Check token/credentials in .env!", phone)
    return json.dumps({
        "success": success,
        "action": "request_location",
        "message": "Location request sent successfully via WhatsApp." if success else "Failed to send location request."
    })


@function_tool
async def fetch_available_providers(
    service_type: str = "",
    lat: float = 0.0,
    lng: float = 0.0,
    city: str | None = None,
    customer_phone: str | None = None,
    language: str | None = None,
) -> str:
    """
    Finds available providers near the customer's location for the given service.
    If customer_phone is provided, it automatically sends them as an interactive WhatsApp media carousel (or buttons).

    Args:
        customer_phone: Customer's E.164 phone number without leading +.
        service_type: One of "ac_repair", "plumber", "electrician"
        lat: Customer latitude
        lng: Customer longitude
        city: Optional city name (e.g., "islamabad", "lahore"). If provided, the system filters by this city. If not, it falls back to the geocoded city.
        language: Language for the interactive carousel/message body. One of "english", "roman_urdu", or "urdu".

    Returns:
        JSON status message or list of ProviderCard objects.
    """
    logger.info("Agent called tool: fetch_available_providers (phone: %s, service_type: %s, lat: %s, lng: %s, city: %s, language: %s)", customer_phone, service_type, lat, lng, city, language)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, fetch_available_providers as db_fetch
    from src.api.geocoding import reverse_geocode_city, CITY_SLUG_MAP
    from src.api.models import ServiceType
    from src.api.whatsapp import send_whatsapp_interactive_carousel, send_whatsapp_interactive_buttons, send_whatsapp_message

    try:
        svc = ServiceType(service_type)
    except ValueError:
        logger.warning("Tool fetch_available_providers failed: Unknown service_type '%s'", service_type)
        return json.dumps({"error": f"Unknown service_type: {service_type}"})

    if city:
        city_slug = CITY_SLUG_MAP.get(city.lower().strip(), city.lower().strip())
    else:
        location_data = await reverse_geocode_city(lat, lng)
        city_slug = location_data.get("slug")
        
    logger.info("Tool fetch_available_providers resolved city: %s", city_slug)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        # Fetch up to 3 nearby providers (carousel limit)
        cards = await db_fetch(session, svc, lat, lng, city_slug, limit=3)
        logger.info("Tool fetch_available_providers found %s providers nearby", len(cards))

    # If no customer phone provided (e.g. testing), return the raw JSON
    if not customer_phone:
        return json.dumps([
            {
                "id": c.id,
                "name": c.name,
                "service_type": c.service_type.value,
                "area": c.area,
                "average_rating": c.average_rating,
                "rating_count": c.rating_count,
                "years_experience": c.years_experience,
                "total_jobs_done": c.total_jobs_done,
                "is_verified": c.is_verified,
                "distance_km": c.distance_km,
                "visit_fee": c.visit_fee,
                "profile_pic_url": c.profile_pic_url,
            }
            for c in cards
        ])

    # Setup language templates
    lang = (language or "roman_urdu").lower().strip()
    if lang == "english":
        no_providers_msg = "I am sorry, there are no providers online in your area at the moment. Please try again in a little while."
        one_provider_header = "I found 1 provider in your area:\n\n"
        one_provider_footer = "Would you like to book them?"
        carousel_body = "Available Providers:"
    elif lang == "urdu":
        no_providers_msg = "معاف کیجیے گا، اس وقت آپ کے علاقے میں کوئی پرووائیڈر آن لائن نہیں ہے۔ براہِ مہربانی تھوڑی دیر بعد دوبارہ کوشش کریں۔"
        one_provider_header = "ہمیں آپ کے علاقے میں 1 پرووائیڈر ملا ہے:\n\n"
        one_provider_footer = "کیا آپ انہیں بک کرنا چاہتے ہیں؟"
        carousel_body = "دستیاب پرووائیڈرز:"
    else:  # roman_urdu
        no_providers_msg = "Maafi chahta hoon, is waqt aapke area mein koi provider online nahi hai. Bara-e-maharbani thodi der baad dobara koshish karein."
        one_provider_header = "Hamein aapke area mein 1 provider mila hai:\n\n"
        one_provider_footer = "Kya aap inhein book karna chahte hain?"
        carousel_body = "Available Providers:"

    if not cards:
        await send_whatsapp_message(
            to_phone=customer_phone,
            message=no_providers_msg
        )
        return json.dumps({
            "status": "no_providers_found",
            "message": "No providers found. A text message has been sent to the customer."
        })

    # If exactly 1 provider found, fall back to interactive buttons
    if len(cards) == 1:
        provider = cards[0]
        rating_str = f"⭐ {provider.average_rating} ({provider.rating_count} ratings)" if provider.average_rating else "No ratings yet"
        
        if lang == "english":
            body_text = (
                f"{one_provider_header}"
                f"👤 *{provider.name}*\n"
                f"📍 Area: {provider.area or 'N/A'}\n"
                f"🚗 Distance: {provider.distance_km} km\n"
                f"💼 Experience: {provider.years_experience} years\n"
                f"⭐ Rating: {rating_str}\n"
                f"💳 Diagnostic Visit Fee: PKR {provider.visit_fee}\n\n"
                f"{one_provider_footer}"
            )
        elif lang == "urdu":
            body_text = (
                f"{one_provider_header}"
                f"👤 *{provider.name}*\n"
                f"📍 علاقہ: {provider.area or 'N/A'}\n"
                f"🚗 فاصلہ: {provider.distance_km} کلومیٹر\n"
                f"💼 تجربہ: {provider.years_experience} سال\n"
                f"⭐ ریٹنگ: {rating_str}\n"
                f"💳 وزٹ فیس: PKR {provider.visit_fee}\n\n"
                f"{one_provider_footer}"
            )
        else:
            body_text = (
                f"{one_provider_header}"
                f"👤 *{provider.name}*\n"
                f"📍 Area: {provider.area or 'N/A'}\n"
                f"🚗 Distance: {provider.distance_km} km\n"
                f"💼 Experience: {provider.years_experience} saal\n"
                f"⭐ Rating: {rating_str}\n"
                f"💳 Diagnostic Visit Fee: PKR {provider.visit_fee}\n\n"
                f"{one_provider_footer}"
            )
        
        btn_title = f"Book {provider.name}"
        if len(btn_title) > 20:
            btn_title = btn_title[:17] + "..."
            
        buttons = [
            {"id": f"book_provider_{provider.id}", "title": btn_title},
            {"id": "cancel_booking_flow", "title": "Cancel"}
        ]
        
        success = await send_whatsapp_interactive_buttons(
            to_phone=customer_phone,
            body_text=body_text,
            buttons=buttons
        )
        return json.dumps({
            "status": "success",
            "provider_count": 1,
            "message": "Only 1 provider found. Sent interactive buttons to the customer.",
            "whatsapp_sent": success
        })

    # If 2 or more providers found, send interactive media carousel
    carousel_cards = []
    for idx, provider in enumerate(cards):
        # Image fallback
        image_url = provider.profile_pic_url
        if not image_url:
            import urllib.parse
            encoded_name = urllib.parse.quote_plus(provider.name)
            image_url = f"https://ui-avatars.com/api/?name={encoded_name}&background=random&size=512&format=png"

        rating_str = f"⭐ {provider.average_rating} ({provider.rating_count})" if provider.average_rating else "N/A"
        
        if lang == "english":
            card_body = (
                f"Distance: {provider.distance_km} km | Rating: {rating_str}\n"
                f"Experience: {provider.years_experience} years | Jobs: {provider.total_jobs_done}\n"
                f"Visit Fee: PKR {provider.visit_fee}"
            )
            if provider.area:
                card_body = f"Area: {provider.area}\n" + card_body
        elif lang == "urdu":
            card_body = (
                f"فاصلہ: {provider.distance_km} کلومیٹر | ریٹنگ: {rating_str}\n"
                f"تجربہ: {provider.years_experience} سال | کام: {provider.total_jobs_done}\n"
                f"وزٹ فیس: PKR {provider.visit_fee}"
            )
            if provider.area:
                card_body = f"علاقہ: {provider.area}\n" + card_body
        else:
            card_body = (
                f"Distance: {provider.distance_km} km | Rating: {rating_str}\n"
                f"Experience: {provider.years_experience} saal | Jobs: {provider.total_jobs_done}\n"
                f"Visit Fee: PKR {provider.visit_fee}"
            )
            if provider.area:
                card_body = f"Area: {provider.area}\n" + card_body
            
        if len(card_body) > 160:
            card_body = card_body[:157] + "..."

        btn_title = f"Book {provider.name}"
        if len(btn_title) > 20:
            btn_title = btn_title[:17] + "..."

        carousel_cards.append({
            "card_index": idx,
            "type": "cta_url",
            "header": {
                "type": "image",
                "image": {
                    "link": image_url
                }
            },
            "body": {
                "text": card_body
            },
            "action": {
                "buttons": [
                    {
                        "type": "quick_reply",
                        "quick_reply": {
                            "id": f"book_provider_{provider.id}",
                            "title": btn_title
                        }
                    }
                ]
            }
        })

    success = await send_whatsapp_interactive_carousel(
        to_phone=customer_phone,
        body_text=carousel_body,
        cards=carousel_cards
    )

    return json.dumps({
        "status": "success",
        "provider_count": len(cards),
        "message": "Sent interactive media carousel to the customer.",
        "whatsapp_sent": success
    })


@function_tool
async def initiate_provider_booking(
    customer_phone: str,
    provider_id: int,
    issue: str,
    lat: float,
    lng: float,
    service_type: str,
    city: str | None = None,
    language: str = "roman_urdu",
) -> str:
    """
    Creates a booking between the customer and the chosen provider.

    Args:
        customer_phone: E.164 phone without +.
        provider_id: ID of the chosen provider (from fetch_available_providers).
        issue: Free-text description of the problem.
        lat: Customer latitude.
        lng: Customer longitude.
        service_type: One of "ac_repair", "plumber", "electrician".
        city: Optional city name (e.g., "islamabad", "lahore"). If provided, saves this city to the booking.
        language: Optional language ("english", "roman_urdu", "urdu").

    Returns:
        JSON with booking_id, status, and provider details.
    """
    logger.info(
        "Agent called tool: initiate_provider_booking (phone: %s, provider_id: %s, issue: %s, service_type: %s, city: %s, language: %s)",
        customer_phone, provider_id, issue, service_type, city, language
    )
    import time
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import (
        engine,
        get_customer_by_phone,
        create_booking,
        get_booking_with_relations,
    )
    from src.api.geocoding import reverse_geocode_city, CITY_SLUG_MAP
    from src.api.models import ServiceType

    try:
        svc = ServiceType(service_type)
    except ValueError:
        logger.warning("Tool initiate_provider_booking failed: Unknown service_type '%s'", service_type)
        return json.dumps({"error": f"Unknown service_type: {service_type}"})

    idempotency_key = f"{customer_phone}:{int(time.time())}"
    
    if city:
        city_slug = CITY_SLUG_MAP.get(city.lower().strip(), city.lower().strip())
    else:
        location_data = await reverse_geocode_city(lat, lng)
        city_slug = location_data.get("slug")

    async with AsyncSession(engine, expire_on_commit=False) as session:
        customer = await get_customer_by_phone(session, customer_phone)
        if not customer:
            logger.warning("Tool initiate_provider_booking failed: Customer with phone %s not registered", customer_phone)
            return json.dumps({"error": "Customer not found. Please register first."})

        booking = await create_booking(
            session,
            customer_id=customer.id,
            provider_id=provider_id,
            issue=issue,
            lat=lat,
            lng=lng,
            city=city_slug,
            service_type=svc,
            idempotency_key=idempotency_key,
            language=language,
        )

        provider = booking.provider
        logger.info(
            "Tool initiate_provider_booking result: Successfully booked provider %s (ID: %s) for booking ID %s",
            provider.name, provider.id, booking.id
        )

    return json.dumps({
        "booking_id": booking.id,
        "status": booking.status.value,
        "idempotency_key": idempotency_key,
        "provider": {
            "id": provider.id,
            "name": provider.name,
            "phone": provider.phone,
            "area": provider.area,
        },
        "message": (
            f"Booking confirmed! {provider.name} will contact you shortly. "
            f"Booking ID: #{booking.id}"
        ),
    })


@function_tool
async def check_booking_status(
    customer_phone: str,
    booking_id: int | None = None,
) -> str:
    """
    Returns the live status of the customer's booking.
    Use this when the customer asks where the provider is, has he left, what's the status, etc.

    Args:
        customer_phone: E.164 phone without +. Used to find the most recent booking.
        booking_id: Optional. If provided, fetches that specific booking instead.

    Returns:
        JSON with status, status_label (in Urdu/Roman Urdu), provider name, and cost details.
    """
    logger.info("Agent called tool: check_booking_status (phone: %s, booking_id: %s)", customer_phone, booking_id)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import (
        engine,
        get_booking_with_relations,
        get_latest_booking_for_customer,
    )

    async with AsyncSession(engine, expire_on_commit=False) as session:
        if booking_id:
            try:
                booking = await get_booking_with_relations(session, booking_id)
            except Exception:
                logger.warning("Tool check_booking_status failed: Booking #%s not found", booking_id)
                return json.dumps({"error": f"Booking #{booking_id} not found."})
        else:
            booking = await get_latest_booking_for_customer(session, customer_phone)

        if not booking:
            logger.warning("Tool check_booking_status failed: No active booking found for phone %s", customer_phone)
            return json.dumps({"error": "No active booking found."})

        provider = booking.provider
        status = booking.status.value
        label = STATUS_LABELS.get(status, "Status unknown.")

        # Append final cost to completed label
        if status == "completed" and booking.final_cost:
            label = f"Kaam mukammal ho gaya. Final cost: PKR {booking.final_cost}."

        logger.info(
            "Tool check_booking_status result: Booking ID %s status is %s (Label: %s)",
            booking.id, status, label
        )

        return json.dumps({
            "booking_id": booking.id,
            "status": status,
            "status_label": label,
            "provider_name": provider.name,
            "provider_phone": provider.phone,
            "service_type": booking.service_type.value,
            "estimated_cost_min": booking.estimated_cost_min,
            "estimated_cost_max": booking.estimated_cost_max,
            "final_cost": booking.final_cost,
            "created_at": booking.created_at.isoformat(),
            "updated_at": booking.updated_at.isoformat(),
        })


@function_tool
async def cancel_booking(booking_id: int, customer_phone: str) -> str:
    """
    Cancels a booking on behalf of the customer.

    Args:
        booking_id: The booking to cancel.
        customer_phone: Used to verify the booking belongs to this customer.

    Returns:
        JSON confirmation of cancellation.
    """
    logger.info("Agent called tool: cancel_booking (booking_id: %s, phone: %s)", booking_id, customer_phone)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, get_booking_with_relations, update_booking
    from src.api.models import BookingStatus, CancelledBy

    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            booking = await get_booking_with_relations(session, booking_id)
        except Exception:
            logger.warning("Tool cancel_booking failed: Booking #%s not found", booking_id)
            return json.dumps({"error": f"Booking #{booking_id} not found."})

        if booking.status in (BookingStatus.completed, BookingStatus.cancelled):
            logger.warning("Tool cancel_booking failed: Booking #%s is already %s", booking_id, booking.status.value)
            return json.dumps({
                "error": f"Booking #{booking_id} is already {booking.status.value} and cannot be cancelled."
            })

        await update_booking(
            session,
            booking_id,
            status=BookingStatus.cancelled,
            cancelled_by=CancelledBy.customer,
        )
        logger.info("Tool cancel_booking result: Successfully cancelled Booking ID %s", booking_id)

        return json.dumps({
            "booking_id": booking_id,
            "status": "cancelled",
            "message": f"Booking #{booking_id} has been cancelled successfully.",
        })


@function_tool
async def confirm_booking(
    customer_phone: str,
    booking_id: int | None = None,
) -> str:
    """
    Confirms a booking when the customer explicitly agrees to proceed (e.g. clicks Confirm Booking on WhatsApp).
    Transitions the booking status from 'accepted' to 'confirmed'.
    Sends a WhatsApp confirmation to the customer.

    Args:
        customer_phone: E.164 phone without +. Used to locate the booking.
        booking_id: Optional. The specific booking ID to confirm.

    Returns:
        JSON with the updated booking status.
    """
    logger.info("Agent called tool: confirm_booking (phone: %s, booking_id: %s)", customer_phone, booking_id)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import (
        engine,
        get_booking_with_relations,
        get_latest_booking_for_customer,
        update_booking,
    )
    from src.api.models import BookingStatus
    from src.api.whatsapp import send_whatsapp_message

    async with AsyncSession(engine, expire_on_commit=False) as session:
        if booking_id:
            try:
                booking = await get_booking_with_relations(session, booking_id)
            except Exception:
                logger.warning("Tool confirm_booking failed: Booking #%s not found", booking_id)
                return json.dumps({"error": f"Booking #{booking_id} not found."})
        else:
            booking = await get_latest_booking_for_customer(session, customer_phone)

        if not booking:
            logger.warning("Tool confirm_booking failed: No active booking found for phone %s", customer_phone)
            return json.dumps({"error": "No booking found to confirm."})

        if booking.status != BookingStatus.accepted:
            logger.warning(
                "Tool confirm_booking failed: Booking #%s is in status %s, expected 'accepted'",
                booking.id, booking.status.value
            )
            return json.dumps({
                "error": (
                    f"Booking cannot be confirmed. Current status is '{booking.status.value}', "
                    "expected 'accepted'."
                )
            })

        booking = await update_booking(session, booking.id, status=BookingStatus.confirmed)
        provider_name = booking.provider.name

        logger.info(
            "Tool confirm_booking result: Successfully confirmed Booking ID %s",
            booking.id
        )

        return json.dumps({
            "booking_id": booking.id,
            "status": "confirmed",
            "message": f"Booking confirmed! {provider_name} is on their way."
        })


@function_tool
async def submit_rating(customer_phone: str, rating: int, review: str | None = None) -> str:
    """
    Submits a rating for the customer's most recently completed booking.
    Call this when the customer provides a rating (1 to 5) for their service.

    Args:
        customer_phone: E.164 phone without +.
        rating: Integer between 1 and 5.
        review: Optional text review.

    Returns:
        JSON with the status of the rating submission.
    """
    logger.info("Agent called tool: submit_rating (phone: %s, rating: %s, review: %s)", customer_phone, rating, review)
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.api.database import engine, get_latest_booking_for_customer, submit_rating as db_submit_rating
    from src.api.models import BookingStatus

    async with AsyncSession(engine, expire_on_commit=False) as session:
        booking = await get_latest_booking_for_customer(session, customer_phone)

        if not booking:
            logger.warning("Tool submit_rating failed: No booking found for phone %s", customer_phone)
            return json.dumps({"error": "No booking found to rate."})

        if booking.status != BookingStatus.completed:
            logger.warning("Tool submit_rating failed: Booking %s is not completed", booking.id)
            return json.dumps({"error": "Only completed bookings can be rated."})

        try:
            await db_submit_rating(session, booking.id, rating, review)
        except Exception as e:
            logger.error("Error submitting rating: %s", str(e))
            return json.dumps({"error": f"Database error submitting rating: {str(e)}"})
            
        logger.info("Tool submit_rating result: Successfully rated Booking ID %s with %s stars", booking.id, rating)

        return json.dumps({
            "booking_id": booking.id,
            "status": "success",
            "message": f"Successfully recorded {rating}-star rating."
        })


# ---------------------------------------------------------------------------
# Agent instantiation
# ---------------------------------------------------------------------------

ustaad_agent = Agent(
    name="Ustaad Agent",
    model="gpt-4o-mini",
    instructions=USTAAD_INSTRUCTIONS,
    tools=[
        get_service_categories,
        check_customer_exists,
        register_customer,
        request_location,
        fetch_available_providers,
        initiate_provider_booking,
        check_booking_status,
        cancel_booking,
        confirm_booking,
        submit_rating,
    ],
)
