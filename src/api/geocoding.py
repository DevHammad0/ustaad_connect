"""
geocoding.py — Reverse geocode (lat, lng) → canonical city slug.

Uses Nominatim (free, no API key) with:
- Upstash Redis cache (7-day TTL) to avoid hammering the free service
- AsyncRateLimiter (1 req/sec) to respect Nominatim's usage policy
- Silent fallback: returns None on any error — callers handle None gracefully
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

load_dotenv()

logger = logging.getLogger(__name__)

UPSTASH_REDIS_REST_URL: str = os.getenv("UPSTASH_REDIS_REST_URL", "")
GEOCACHE_TTL = 60 * 60 * 24 * 7  # 7 days in seconds

# ---------------------------------------------------------------------------
# Nominatim setup
# ---------------------------------------------------------------------------

_geolocator = Nominatim(user_agent="ustaad-connect/1.0")
_reverse_rate_limited = RateLimiter(_geolocator.reverse, min_delay_seconds=1)

# ---------------------------------------------------------------------------
# Canonical city slug map
# Normalises the many ways Nominatim labels Pakistani cities.
# ---------------------------------------------------------------------------

CITY_SLUG_MAP: dict[str, str] = {
    "islamabad": "islamabad",
    "islamabad capital territory": "islamabad",
    "rawalpindi": "rawalpindi",
    "lahore": "lahore",
    "lahore district": "lahore",
    "karachi": "karachi",
    "karachi city": "karachi",
    "faisalabad": "faisalabad",
    "faisalabad district": "faisalabad",
    "multan": "multan",
    "peshawar": "peshawar",
    "peshawar city tehsil": "peshawar",
    "peshawar district": "peshawar",
    "quetta": "quetta",
}


def _get_redis_client():
    """Lazy Redis client — only imported/created if Upstash configuration is available."""
    if not UPSTASH_REDIS_REST_URL:
        return None
    try:
        from upstash_redis import Redis
        return Redis.from_env()
    except Exception as exc:
        logger.warning("Could not connect to Redis for geocode cache: %s", exc)
        return None


import json

async def reverse_geocode_city(lat: float, lng: float) -> dict[str, str | None]:
    """
    Returns a dictionary containing the canonical city slug and the full display address.
    """
    cache_key = f"geocache_v2:{lat:.4f}:{lng:.4f}"

    # --- Cache read ---
    redis = _get_redis_client()
    if redis:
        try:
            cached = redis.get(cache_key)
            if cached is not None:
                logger.debug("Geocache v2 hit for %s,%s", lat, lng)
                return json.loads(cached)
        except Exception as exc:
            logger.warning("Redis geocache read failed: %s", exc)

    slug = None
    display_name = None

    # --- Nominatim lookup ---
    try:
        location = _reverse_rate_limited(
            (lat, lng),
            exactly_one=True,
            language="en",
        )
        if location is not None:
            raw = location.raw.get("address", {})
            display_name = location.raw.get("display_name")
            # Nominatim returns city/town/village in priority order
            city_raw = (
                raw.get("city")
                or raw.get("town")
                or raw.get("municipality")
                or raw.get("county")
                or ""
            ).lower().strip()
            slug = CITY_SLUG_MAP.get(city_raw)
            logger.info("Nominatim resolved (%s, %s) → '%s' → slug '%s'", lat, lng, city_raw, slug)
    except Exception as exc:
        logger.warning("Nominatim lookup failed for (%s, %s): %s", lat, lng, exc)

    result = {"slug": slug, "address": display_name}

    # --- Cache write ---
    if redis:
        try:
            redis.set(cache_key, json.dumps(result), ex=GEOCACHE_TTL)
        except Exception as exc:
            logger.warning("Redis geocache write failed: %s", exc)

    return result
