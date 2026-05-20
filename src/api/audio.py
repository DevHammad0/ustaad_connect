"""
audio.py — OpenAI Speech-to-Text and OpenAI Text-to-Speech integration.
"""

import io
import logging
import os
import asyncio

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# The API key will be automatically picked up from the OPENAI_API_KEY env var
openai_client = AsyncOpenAI()


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """
    Transcribes audio bytes to text using OpenAI Whisper API.
    """
    try:
        logger.info("Transcribing audio using OpenAI Whisper...")
        # Create a file-like object from bytes
        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = filename
        
        response = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=file_obj,
            prompt="Assalam-o-Alaikum! Hello! السلام علیکم۔ Mujhe AC repair, plumbing ya electrician chahiye. Mera AC kharab ho gaya hai. Plumber ko bhej dein. Very good service, thank you. بہت اچھی سروس تھی، شکریہ۔"
        )
        return response.text.strip()
    except Exception as e:
        logger.error("Failed to transcribe audio with OpenAI Whisper: %s", e)
        return ""


async def synthesize_speech(text: str) -> bytes | None:
    """
    Synthesizes speech from text using OpenAI TTS.
    Returns OGG Opus formatted bytes suitable for WhatsApp.
    """
    if not text or not text.strip():
        return None
        
    try:
        logger.info("Synthesizing speech using OpenAI TTS...")
        response = await openai_client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            response_format="opus"
        )
        return response.content
    except Exception as e:
        logger.error("Failed to synthesize speech with OpenAI TTS: %s", e)
        return None

