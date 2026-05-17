"""
Template: session_utils.py

Helpers for opt-in SQLite session memory.
Copy into your project (e.g. src/api/session_utils.py).

Environment variables:
    ENABLE_SESSIONS  - "true" | "false"  (default: "true")
    SESSION_DB_PATH  - file path          (default: "./conversations.db")
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from agents import SQLiteSession

logger = logging.getLogger(__name__)


def is_sessions_enabled() -> bool:
    """Return True when ENABLE_SESSIONS env var is truthy (default: True)."""
    return os.getenv("ENABLE_SESSIONS", "true").lower() in {"true", "1", "yes"}


def get_session_db_path() -> str:
    """Return SESSION_DB_PATH, creating parent directories if necessary."""
    path = os.getenv("SESSION_DB_PATH", "./conversations.db")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


def create_session_if_enabled(session_id: Optional[str]) -> Optional[SQLiteSession]:
    """
    Return an SQLiteSession if sessions are enabled and a session_id is provided.
    Returns None for stateless runs (no session_id or ENABLE_SESSIONS=false).
    """
    if not session_id or not is_sessions_enabled():
        return None

    db_path = get_session_db_path()
    logger.debug("Opening session %s at %s", session_id, db_path)
    return SQLiteSession(session_id, db_path=db_path)


async def get_session_messages(
    session_id: str,
    limit: Optional[int] = None,
) -> list[dict]:
    """
    Retrieve stored conversation items for a session.
    Returns an empty list if sessions are disabled or the session doesn't exist.
    """
    session = create_session_if_enabled(session_id)
    if session is None:
        return []

    try:
        items = await session.get_items()
        if limit is not None:
            items = items[-limit:]
        return [item if isinstance(item, dict) else item.__dict__ for item in items]
    except Exception:
        logger.exception("Failed to retrieve messages for session %s", session_id)
        return []


async def clear_session(session_id: str) -> bool:
    """
    Delete all conversation history for a session.
    Returns True on success, False if sessions are disabled or an error occurs.
    """
    if not is_sessions_enabled():
        return False

    db_path = get_session_db_path()
    try:
        session = SQLiteSession(session_id, db_path=db_path)
        await session.clear_session()
        logger.info("Cleared session %s", session_id)
        return True
    except Exception:
        logger.exception("Failed to clear session %s", session_id)
        return False


def get_session_info() -> dict:
    """Return current session configuration (safe to expose in /info)."""
    return {
        "enabled": is_sessions_enabled(),
        "db_path": get_session_db_path() if is_sessions_enabled() else None,
    }
