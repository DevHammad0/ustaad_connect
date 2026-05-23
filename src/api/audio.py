"""
audio.py — OpenAI Speech-to-Text and OpenAI Text-to-Speech integration.
"""

import io
import logging
import os
import asyncio
import base64
import httpx

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# The API key will be automatically picked up from the OPENAI_API_KEY env var
openai_client = AsyncOpenAI()


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """
    Transcribes audio bytes to text using OpenRouter Gemini-2.0-flash-lite-001 model.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not set in environment variables")
        return ""

    try:
        logger.info("Transcribing audio using OpenRouter Gemini 2.0 Flash Lite...")
        
        # Base64 encode the audio bytes
        base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        
        # Determine file extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "ogg"
        supported_formats = {"wav", "mp3", "aac", "ogg", "flac", "m4a", "webm"}
        if ext not in supported_formats:
            ext = "ogg"
            
        prompt_text = (
            "Please transcribe this audio accurately. The audio may be in English, Urdu, or Pashto.\n"
            "Rules:\n"
            "1. If the speaker is speaking English, output standard English text.\n"
            "2. If the speaker is speaking Urdu or Pashto, output standard Arabic script (Urdu/Pashto alphabet, e.g. 'السلام علیکم'). Do NOT use Devanagari/Hindi characters (e.g. 'अस्सलाम').\n"
            "3. Output ONLY the transcription itself. No explanations, no prefixes, no suffixes."
        )

        payload = {
            "model": "google/gemini-2.0-flash-lite-001",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": base64_audio,
                                "format": ext,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt_text,
                        },
                    ],
                }
            ],
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
        logger.info("OpenRouter STT raw response: status=%s, text=%s", response.status_code, response.text)
        
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            logger.error("OpenRouter API returned an error: %s", result["error"])
            return ""
            
        transcription = result["choices"][0]["message"]["content"]
        return transcription.strip()
        
    except Exception as e:
        logger.error("Failed to transcribe audio with OpenRouter: %s", e)
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


