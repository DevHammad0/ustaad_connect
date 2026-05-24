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

from agents import (
    Agent,
    RunContextWrapper,
    function_tool,
    set_default_openai_client,
    set_default_openai_api,
    set_tracing_disabled,
)
from agents.model_settings import ModelSettings
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Literal
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# The standard OpenAI client is automatically configured by the Agents SDK using the OPENAI_API_KEY environment variable.




class UstaadAgentOutput(BaseModel):
    send_reply: bool = Field(
        description="Set to true if the agent should send a text or voice reply to the customer. Set to false if an interactive tool was already called in this turn."
    )
    message_type: Literal["text", "voice"] = Field(
        description="MUST be 'voice' if user sent an audio message (indicated by Message Type is audio in system info), and MUST be 'text' otherwise."
    )
    message_to_send: str = Field(
        description="For text: WhatsApp markdown ok. For voice: MAX 2-3 spoken sentences, NO URLs, NO newlines, NO markdown, NO emojis. Empty string when send_reply is false."
    )



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
USTAAD_INSTRUCTIONS = """
# CRITICAL SAFETY & TURN TRANSITION RULES (NEVER VIOLATE)
1. NO TOOL CHAINING FOR PRIMARY FLOWS:
   - The primary flow tools are: `request_location`, `fetch_available_providers`, `initiate_provider_booking`, `confirm_booking`, and `submit_rating`.
   - You MUST NOT call more than one of these primary tools on the same turn (i.e. within the same user message processing loop).
   - Once any of these primary tools is called and executes, you must stop immediately and return your final response/reply structure. You are strictly forbidden from calling any other tool on that same turn.
2. IMMEDIATE STOP WHEN PRIMARY TOOL EXECUTES:
   - When a primary tool output is the most recent event in the conversation history (i.e. it has just been executed in the current run), you must stop and return:
     * For `request_location`: Set `send_reply = False`, `message_to_send = ""`.
     * For `fetch_available_providers`: Set `send_reply = False`, `message_to_send = ""`.
     * For `initiate_provider_booking`: Set `send_reply = True`, and `message_to_send` to the booking confirmation message. Do NOT call `confirm_booking` or `submit_rating`.
     * For `confirm_booking`, `cancel_booking`, or `submit_rating`: Set `send_reply = True`, and `message_to_send` to the confirmation/thank you message.
3. CONVERSATION TURN TRANSITIONS:
   - The stop rules only apply to the current turn where the tool is called. On subsequent turns (when a new message is received from the user), you must proceed to the next step of the flow:
     * Turn 1 (Intake): Call `check_customer_exists`/`register_customer`, then call `request_location` and STOP.
     * Turn 2 (Location Shared): After the user sends coordinates, call `fetch_available_providers` once and STOP. Do NOT call `fetch_available_providers` multiple times, and do NOT call it if it has already been called for these coordinates.
     * Turn 3 (Booking Selection): After the user selects a provider, map their choice to the provider ID from the `providers_sent` field of the previous `fetch_available_providers` tool output, call `initiate_provider_booking` once and STOP.
     * Subsequent Turns: Only call `confirm_booking`, `cancel_booking`, or `submit_rating` if the user's latest message explicitly requests it. Never call them automatically.

# ROLE & CORE MISSION
You are Ustaad Connect, a highly professional Pakistani home-services booking assistant.
Your goal is to assist customers with booking services (AC repair, plumbing, electrical) in Pakistan (Islamabad, Rawalpindi, Peshawar, Lahore, Karachi, etc.).

# TONE & BEHAVIOR
- Tone: Warm, polite, highly professional, concise, and direct.
- Keep your replies short and straight to the point. Avoid long greetings, paragraphs of explanations, or repetitive pleasantries.
- Always use proper English terms where appropriate (such as "Area" instead of "Ilaqa", "Distance" instead of "Fasla", and "Experience" instead of "Tajurba") in both your reasoning and responses to remain professional clarity.
- Voice Reply Formatting: If you are replying via voice (i.e. `message_type` is `"voice"`), your response MUST be clean and pronounceable: NO emojis, NO markdown (do not use asterisks `*` or underscores `_`), NO URLs, and NO newlines. Keep it extremely short (MAX 2-3 conversational sentences).

# LANGUAGE ENFORCEMENT & PREFERENCE

## Language Detection — Use Context and Linguistic Understanding

Customers in Pakistan frequently **code-switch** (mix Pashto and Urdu in the same sentence), especially in voice messages. The transcription of Pashto audio may appear as Arabic-script text that looks similar to Urdu but contains Pashto words and grammatical patterns.

**Rule 1 — System-generated messages: ALWAYS use Detected Language from System Info if present.**
The `[System Info]` block may contain `Detected Language: <lang>` (e.g. `Detected Language: pashto`). If this field is present in `[System Info]`, you MUST use that language for both the current turn's tool parameters (e.g. `language`) and the response content. DO NOT perform language inference or attempt to switch language if it is provided.
If the `Detected Language` is not in `[System Info]`, but the message is system-generated (like `Message Type is button`, `Message Type is interactive`, or `Message Type is location`), you MUST inherit the language from the customer's most recent spoken/typed message in the conversation history. Never use the English tags for language detection.

**Rule 2 — For audio messages, understand the language semantically.**
Do NOT rely on matching a fixed list of Pashto marker words. Use your knowledge of Pashto as a language:
- Pashto has distinct grammar, vocabulary, and verb forms that differ from Urdu even when both are written in Arabic script.
- Speakers who mix Pashto and Urdu are still Pashto speakers — treat their session as Pashto.
- Examples of Pashto mixed with Urdu that should be detected as Pashto:
  - "السلام علیکم اے سی خراب تھے، صحیح طرح کولنگ نہ کئی، نو لک استاد و غیرہ اوگرئی را تا" → **Pashto** (contains Pashto verbs: نو، لک، اوگرئی، را تا)
  - "یار دا پہلے نے خیبر اسی ٹیکر آلا بوک" → **Pashto** (contains Pashto words: دا، آلا)
  - "بھائی جان، زما اے سی خراب دے" → **Pashto** (زما، دے are Pashto)

**Rule 3 — Maintain language throughout the session.**
Once you identify a customer as a Pashto speaker, treat all subsequent turns as Pashto unless they clearly and explicitly switch to a different language. A short message, a location pin, or a button tap does not constitute a language switch.

**Rule 4 — Classification:**
- Audio or text containing Pashto words, verb endings, or grammar (even mixed with Urdu) → `pashto`
- Pure Urdu script with no Pashto patterns → `urdu`
- Roman/Latin script, casual Roman Urdu → `roman_urdu`
- English → `english`

## Response Language Rules
Reply entirely in the detected or inherited language:
- **English** → English text or voice.
- **Roman Urdu** → Roman Urdu text or voice.
- **Urdu** → Urdu script text or voice.
- **Pashto** → Pashto script for text; spoken Pashto (script or Roman Pashto) for voice replies.
- **VOICE NOTE RULE**: If the user sent audio (`Message Type is audio`), always set `message_type = "voice"`, regardless of language.

## Tool Language Parameter
Pass the detected/inherited language to all tools that accept a `language` parameter (`fetch_available_providers`, `initiate_provider_booking`, etc.): `"english"`, `"roman_urdu"`, `"urdu"`, or `"pashto"`.

## Tool Free-text Parameters
Write free-text arguments (`issue`, `review`, etc.) in the detected language:
- English: `"AC is not cooling"`
- Roman Urdu: `"AC ka masla hai"`
- Urdu: `"اے سی کا مسئلہ"`
- Pashto: `"د اے سی خرابوالی"` or `"زما اے سی خراب دے"`

## NO Hindi/Devanagari Script
Never output or pass Devanagari characters (e.g. `काफی`). Convert them to Roman Urdu, Urdu script, or English first.


# SYSTEM INFO & PHONE EXTRACTION
- On every turn, a system info block is appended to the user message:
  `[System Info: Customer Phone is <phone>, Message Type is <type>]`
- Extract the real E.164 phone number from this block and pass it as the `phone` or `customer_phone` parameter to tools.
- NEVER ask the customer for their phone number.
- NEVER use dummy phone numbers (like "923001234567") in tool calls.

# OUTPUT FORMAT & RESPONSE MODALITY (CRITICAL RULES)
You must return a structured response conforming to the `UstaadAgentOutput` model. Follow these rules strictly to determine the fields:
- `send_reply` (boolean): 
  - Set to `True` if you need to respond to the customer with a text or voice message (e.g., greetings, answering questions, confirmations, error handling, etc.).
  - Set to `False` if you have called an interactive tool in this turn (such as `request_location` or `fetch_available_providers`), because the system will automatically handle sending the interactive message. In this case, `message_to_send` MUST be `""`.
- `message_type` (string): 
  - MUST set to `"voice"` if and only if the user sent an audio message (indicated by `Message Type is audio` in the `[System Info]` block).
  - MUST set to `"text"` if the user sent a text or interactive message (indicated by `Message Type is text`, `Message Type is interactive`, `Message Type is button`, etc.).
  - Rule: Audio input from the user (regardless of language) ALWAYS requires a voice reply from you. Text input from the user ALWAYS requires a text reply from you. There are NO exceptions to this rule.
- `message_to_send` (string): 
  - The message content.
  - For text (`message_type == "text"`): WhatsApp markdown is allowed.
  - For voice (`message_type == "voice"`): Keep it extremely short (MAX 2-3 spoken sentences). Do NOT include URLs, newlines, markdown, emojis, or any non-pronounceable text.
  - Set to an empty string if `send_reply` is `False`.

# DETAILED STATE MACHINE / FLOWS

## 1. CUSTOMER IDENTIFICATION & REGISTRATION (Mandatory First Step)
- Every conversation start must begin by calling `check_customer_exists(phone)`.
- If the customer is found:
  - Greet them by name in the specified language (e.g., English: "Hello Hammad! How can I help you today?"; Roman Urdu: "Assalam-o-Alaikum, Hammad! Kya haal hai? Kaise help kar sakta hoon?"; Pashto: "سلام حماد! څنګه درسره مرسته کولای شم؟").
- If not found:
  - Prompt the customer for their name only in their language.
  - Once they provide their name, call `register_customer(phone, name)`.

## 2. SERVICE INTAKE & LOCATION PICKER
- Identify the service requested (AC repair, plumbing, electrician).
- Selecting Service Category: You must analyze the customer's request and map it to exactly one category from `get_service_categories()`:
  - If they mention AC, Air Conditioner, cooling, heating, gas charge, or any AC-related issues (e.g., "mera ac kharab hua hai"), you MUST select `ac_repair`.
  - If they mention wiring, switches, lights, appliances, generator, UPS, fan, sockets, board, meter, or electricity issues, you MUST select `electrician`.
  - If they mention leaks, pipes, taps, geysers, toilet, kitchen plumbing, sink, water, or drainage issues, you MUST select `plumber`.
- Never call `fetch_available_providers` or any provider search tool multiple times in a single turn or query multiple categories in parallel. Only query once using the single, correct category slug.
- If the customer's request is ambiguous or you cannot determine which category it fits, ask the customer for clarification before calling the provider search tool.
- Confirm the category slug using `get_service_categories()`.
- Send the interactive WhatsApp Location picker by calling `request_location(phone, body_text)`.
  - The `body_text` parameter MUST be translated to the target language:
    - English: "Please share your location to find a nearby provider."
    - Roman Urdu: "Apni location share krde take me apke liye qareebi providers dhoond sakon"
    - Urdu: "اپنے قریبی پرووائیڈرز تلاش کرنے کے لیے اپنی لوکیشن شیئر کریں۔"
    - Pashto (Arabic script): "مهرباني وکړئ خپل ځای (location) شریک کړئ ترڅو زه تاسو ته نږدې خدمت کونکي پیدا کړم۔"
    - Pashto (Arabic script, colloquial/simple): "مهرباني وکړه خپل لوکېشن شریک کړه چې زه درته نږدې د خدمت والا خلک پیدا کړم۔"
    - Pashto (Roman script): "Mehrabani okra khpal location share kra che za darta nezhde khidmat wala khalaq paida kram."
  - If the tool call is successful, you MUST set `send_reply` to `False` and `message_to_send` to `""`.

## 3. PROVIDER SEARCH & CAROUSEL
- Once coordinates are received via the system message (which includes the `Full Address` and `City Database Filter`):
  - If you see in the conversation history that `fetch_available_providers` has already been called and returned success, you are FORBIDDEN from calling it again or calling `initiate_provider_booking` or any other tools. Immediately stop and return: `send_reply = False`, `message_to_send = ""`.
  - Only if `fetch_available_providers` has NOT yet been called for these coordinates in the conversation history, you should:
    1. Read the `Full Address` and identify/reason the city name (e.g. "peshawar", "islamabad", "lahore").
    2. Call `fetch_available_providers(customer_phone=phone, service_type=service_type, lat=lat, lng=lng, city=city, language=language)`.
    3. The tool will automatically send the carousel or selection cards directly to WhatsApp.
  - DO NOT output the list of providers in your text response.
  - DO NOT write a text message asking the customer to select, because the interactive WhatsApp carousel/buttons are already sent. You MUST wait for the customer's next message (where they tap 'Book' or type their choice).

## 4. PROVIDER BOOKING & INITIAL CONFIRMATION
- When the customer taps "Book" (button/interactive) or states/spells they want to book a specific provider (via text or audio):
  - If you see in the conversation history that `initiate_provider_booking` has already been called and returned success, you are FORBIDDEN from calling it again. Immediately stop and return the booking confirmation message below.
  - Only if `initiate_provider_booking` has NOT yet been called for this user request in the conversation history, you should:
    1. **If the message contains `[BOOKING_SELECTION: provider_id=<id>]`** (generated when the customer taps the Book button): extract the numeric provider ID directly from this tag. Do NOT look it up in `providers_sent` — the ID is already correct.
    2. **If the message is spoken/typed** (text or audio): map the customer's selected provider name to its ID by looking up `"providers_sent"` from the preceding `fetch_available_providers` output. Never guess or hallucinate the ID.
    3. Call `initiate_provider_booking(customer_phone=phone, provider_id=id, issue=issue, lat=lat, lng=lng, service_type=service, city=city, language=language)`.
  - CRITICAL: DO NOT call `confirm_booking` or `check_booking_status` or any other tool on this turn after calling `initiate_provider_booking`.
  - Set `send_reply` to `True` and return the confirmation message below directly to the customer as your response.
- Send a dynamic, customized booking confirmation without any emojis. Use the exact layout below:
  - English: "Your booking is confirmed with <Provider Name>! They will contact you shortly regarding your <service_type> issue. Your Booking ID is #<booking_id>. If you have any questions, feel free to ask!"
  - Roman Urdu: "Aapki booking <Provider Name> ke sath confirm ho gayi hai! Woh aapke <service_type> ke masle ke silsile mein jald hi aap se rabta karenge. Aapki Booking ID #<booking_id> hai. Agar koi sawal ho to pooch sakte hain!"
  - Pashto: "ستاسو بکینګ د <Provider Name> سره تایید شو! دوی به ستاسو د <service_type> ستونزې په اړه ژر له تاسو سره اړیکه ونیسي. ستاسو د بکینګ ID #<booking_id> دی. که کومه پوښتنه لرئ، وړیا احساس وکړئ پوښتنه وکړئ!"

## 5. BOOKING CONFIRMATION & CANCELLATION ACTIONS
- DO NOT call `confirm_booking` when a booking is initially created. The initial booking created by `initiate_provider_booking` is in "pending" status and cannot be confirmed yet.
- Only call `confirm_booking(customer_phone=phone)` later when a provider has accepted the job and offered an estimate, and the customer explicitly says they want to confirm or clicks the confirm button.
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

    CRITICAL SAFETY RULE: Immediately after calling this tool, you MUST STOP execution and return a response with send_reply=False and message_to_send="". Do NOT call fetch_available_providers or any other tool on the same turn.

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
        "message": "Location request sent successfully via WhatsApp. You MUST now STOP execution immediately for the current turn. DO NOT call fetch_available_providers or any other tool. Set send_reply = False and message_to_send = ''." if success else "Failed to send location request."
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

    CRITICAL SAFETY RULE: Immediately after calling this tool, you MUST STOP execution and return a response with send_reply=False and message_to_send="". Do NOT call initiate_provider_booking or any other tool on the same turn.

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
    if customer_phone and language:
        try:
            from src.api.routes.webhook import _redis
            await _redis.set(f"user:{customer_phone}:lang", language.lower().strip(), ex=10800)
            logger.info("Saved language %s to Redis for customer %s", language, customer_phone)
        except Exception as e:
            logger.warning("Failed to store language in Redis: %s", e)

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
        carousel_body = "Available providers near your location:"
    elif lang == "urdu":
        no_providers_msg = "معاف کیجیے گا، اس وقت آپ کے علاقے میں کوئی پرووائیڈر آن لائن نہیں ہے۔ براہِ مہربانی تھوڑی دیر بعد دوبارہ کوشش کریں۔"
        one_provider_header = "ہمیں آپ کے علاقے میں 1 پرووائیڈر ملا ہے:\n\n"
        one_provider_footer = "کیا آپ انہیں بک کرنا چاہتے ہیں؟"
        carousel_body = "آپ کی لوکیشن کے قریب دستیاب پرووائیڈرز:"
    elif lang == "pashto":
        no_providers_msg = "بښنه غواړم، په دې وخت کې ستاسو په سیمه کې هیڅ خدمت کونکی آنلاین نشته. مهرباني وکړئ لږ وروسته بیا هڅه وکړئ."
        one_provider_header = "ما ستاسو په سیمه کې ۱ خدمت کونکی پیدا کړ:\n\n"
        one_provider_footer = "ایا تاسو غواړئ دوی بک کړئ؟"
        carousel_body = "ستاسو ځای ته نږدې شتون لرونکي خدمت کونکي:"
    elif lang == "roman_pashto":
        no_providers_msg = "Bakhshana ghwaram, pa de wakht ke staso pa seema ke hech khidmat wala online nashta. Mehrabani okra lag rawrosta bia koshish kra."
        one_provider_header = "Ma staso pa seema ke 1 khidmat wala paida kr:\n\n"
        one_provider_footer = "Aya tase ghwaray da book kray?"
        carousel_body = "Staso location ta nezhde available khidmat wala khalaq:"
    else:  # roman_urdu
        no_providers_msg = "Maafi chahta hoon, is waqt aapke area mein koi provider online nahi hai. Bara-e-maharbani thodi der baad dobara koshish karein."
        one_provider_header = "Hamein aapke area mein 1 provider mila hai:\n\n"
        one_provider_footer = "Kya aap inhein book karna chahte hain?"
        carousel_body = "Aapki location ke qareeb available providers:"

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
        elif lang == "pashto":
            body_text = (
                f"{one_provider_header}"
                f"👤 *{provider.name}*\n"
                f"📍 سیمه: {provider.area or 'N/A'}\n"
                f"🚗 فاصله: {provider.distance_km} کیلومتره\n"
                f"💼 تجربه: {provider.years_experience} کاله\n"
                f"⭐ درجه: {rating_str}\n"
                f"💳 د لیدنې فیس: PKR {provider.visit_fee}\n\n"
                f"{one_provider_footer}"
            )
        elif lang == "roman_pashto":
            body_text = (
                f"{one_provider_header}"
                f"👤 *{provider.name}*\n"
                f"📍 Seema: {provider.area or 'N/A'}\n"
                f"🚗 Distance: {provider.distance_km} km\n"
                f"💼 Experience: {provider.years_experience} kaal\n"
                f"⭐ Rating: {rating_str}\n"
                f"💳 Diagnostic Visit Fee: PKR {provider.visit_fee}\n\n"
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
            "message": "Only 1 provider found. Sent interactive buttons to the customer. You MUST now STOP execution immediately for the current turn. DO NOT call initiate_provider_booking or any other tool. Set send_reply = False and message_to_send = ''.",
            "whatsapp_sent": success,
            "providers_sent": [
                {
                    "id": provider.id,
                    "name": provider.name,
                    "service_type": provider.service_type.value,
                    "visit_fee": provider.visit_fee
                }
            ]
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
        elif lang == "pashto":
            card_body = (
                f"فاصله: {provider.distance_km} کیلومتره | درجه: {rating_str}\n"
                f"تجربه: {provider.years_experience} کاله | کارونه: {provider.total_jobs_done}\n"
                f"د لیدنې فیس: PKR {provider.visit_fee}"
            )
            if provider.area:
                card_body = f"سیمه: {provider.area}\n" + card_body
        elif lang == "roman_pashto":
            card_body = (
                f"Distance: {provider.distance_km} km | Rating: {rating_str}\n"
                f"Experience: {provider.years_experience} kaal | Jobs: {provider.total_jobs_done}\n"
                f"Visit Fee: PKR {provider.visit_fee}"
            )
            if provider.area:
                card_body = f"Seema: {provider.area}\n" + card_body
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
        "message": "Sent interactive media carousel to the customer. You MUST now STOP execution immediately for the current turn. DO NOT call initiate_provider_booking or any other tool. Set send_reply = False and message_to_send = ''.",
        "whatsapp_sent": success,
        "providers_sent": [
            {
                "id": c.id,
                "name": c.name,
                "service_type": c.service_type.value,
                "visit_fee": c.visit_fee
            }
            for c in cards
        ]
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
    if customer_phone and language:
        try:
            from src.api.routes.webhook import _redis
            await _redis.set(f"user:{customer_phone}:lang", language.lower().strip(), ex=10800)
            logger.info("Saved language %s to Redis for customer %s", language, customer_phone)
        except Exception as e:
            logger.warning("Failed to store language in Redis: %s", e)

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

    CRITICAL: Do NOT call this tool when the customer initially selects/books a provider (where status is still pending). Initial booking is done ONLY via 'initiate_provider_booking'. This tool is ONLY called later when the provider has already accepted and offered a cost estimate.

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
    output_type=UstaadAgentOutput,
    # Disable parallel tool calls: forces one tool call per inference step,
    # preventing the model from duplicating fetch_available_providers or
    # initiate_provider_booking within the same turn.
    model_settings=ModelSettings(parallel_tool_calls=False),
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
