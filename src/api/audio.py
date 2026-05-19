"""
audio.py — OpenAI Speech-to-Text and Google Gemini Text-to-Speech integration.
"""

import io
import logging
import os
import asyncio
import tempfile

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# The API key will be automatically picked up from the OPENAI_API_KEY env var
openai_client = AsyncOpenAI()

_genai_client = None

def get_genai_client():
    """
    Lazily initializes the Google GenAI Client.
    Supports GEMINI_API_KEY and GOOGLE_API_KEY, strips trailing/leading whitespaces,
    and falls back to Vertex AI if running on Cloud Run without an API key.
    """
    global _genai_client
    if _genai_client is None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            # If no API key is provided, check if we are in Cloud Run to try Vertex AI
            if os.getenv("K_SERVICE"):
                try:
                    from google import genai
                    _genai_client = genai.Client(vertexai=True)
                    logger.info("Initialized Gemini Client with Vertex AI using Service Account.")
                except Exception as e:
                    logger.error("Failed to initialize Gemini Client with Vertex AI: %s", e)
                    return None
            else:
                logger.error("Gemini API key is missing. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
                return None
        else:
            try:
                from google import genai
                _genai_client = genai.Client(api_key=api_key.strip())
                logger.info("Initialized Gemini Client with provided API key.")
            except Exception as e:
                logger.error("Failed to initialize Gemini Client with API key: %s", e)
                return None
    return _genai_client


async def convert_pcm_to_ogg(pcm_bytes: bytes) -> bytes | None:
    """
    Converts raw PCM (s16le, 24000Hz, 1 channel) to OGG Opus format using ffmpeg.
    """
    if not pcm_bytes:
        return None

    # Create temporary files
    in_file = tempfile.NamedTemporaryFile(suffix=".pcm", delete=False)
    try:
        in_file.write(pcm_bytes)
        in_file.flush()
        in_path = in_file.name
    finally:
        in_file.close()

    out_path = in_path + ".ogg"
    
    try:
        # Run ffmpeg command asynchronously to convert PCM to OGG Opus
        cmd = [
            "ffmpeg", "-y",
            "-f", "s16le",
            "-ar", "24000",
            "-ac", "1",
            "-i", in_path,
            "-c:a", "libopus",
            "-b:a", "24k",
            "-f", "ogg",
            out_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error("FFmpeg conversion failed with return code %d: %s", proc.returncode, stderr.decode())
            return None
            
        with open(out_path, "rb") as f:
            return f.read()
            
    except Exception as e:
        logger.error("Failed to convert PCM to OGG via ffmpeg: %s", e)
        return None
    finally:
        # Clean up temporary files
        try:
            if os.path.exists(in_path):
                os.remove(in_path)
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """
    Transcribes audio bytes to text using Google Gemini Multimodal model.
    Falls back to OpenAI Whisper if Gemini is unavailable or fails.
    """
    # 1. Try Gemini Multimodal STT first
    client = get_genai_client()
    if client:
        try:
            logger.info("Attempting audio transcription using Gemini model...")
            from google.genai import types
            
            prompt = (
                "You are an expert audio transcriber for a Pakistani home services app called Ustaad Connect. "
                "Your job is to transcribe the provided audio input accurately into text. "
                "Follow these language rules strictly:\n"
                "1. Do NOT translate the spoken audio. Transcribe it in the exact language and script it was spoken.\n"
                "2. If spoken in Urdu script (Arabic alphabet), output in Urdu script (e.g., 'میرا اے سی خراب ہو گیا ہے').\n"
                "3. If spoken in Roman Urdu (Urdu words written using the English alphabet), output in Roman Urdu (e.g., 'mera ac kharab ho gaya hai').\n"
                "4. If spoken in English, output in English.\n"
                "5. Under no circumstances should you ever use Hindi/Devanagari script characters (e.g., 'काफी', 'थी'). "
                "If the spoken language is Urdu, transcribe it using the Urdu script (e.g., 'بہت اچھی سروس تھی') or Roman Urdu, NEVER Devanagari.\n"
                "6. Output ONLY the transcription text. Do not include any intros, explanations, or notes."
            )
            
            # Determine mime type from filename extension
            mime_type = "audio/ogg"
            if filename.endswith(".wav"):
                mime_type = "audio/wav"
            elif filename.endswith(".mp3"):
                mime_type = "audio/mp3"
            elif filename.endswith(".aac"):
                mime_type = "audio/aac"
            elif filename.endswith(".flac"):
                mime_type = "audio/flac"

            def _call_gemini_stt():
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type=mime_type,
                        ),
                    ],
                )
                return response.text

            transcription = await asyncio.to_thread(_call_gemini_stt)
            if transcription and transcription.strip():
                result = transcription.strip()
                logger.info("Gemini audio transcription successful: %s", result)
                return result
            else:
                logger.warning("Gemini audio transcription returned empty text. Falling back to Whisper...")
        except Exception as e:
            logger.error("Failed to transcribe audio with Gemini: %s. Falling back to Whisper...", e)

    # 2. Fallback to OpenAI Whisper
    try:
        logger.info("Using Whisper fallback for audio transcription...")
        # Create a file-like object from bytes
        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = filename
        
        response = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=file_obj,
            prompt="Assalam-o-Alaikum! Hello! السلام علیکم۔ Mujhe AC repair, plumbing ya electrician chahiye. Mera AC kharab ho gaya hai. Plumber ko bhej dein. Very good service, thank you. بہت اچھی سروس تھی، شکریہ۔"
        )
        return response.text
    except Exception as e:
        logger.error("Failed to transcribe audio with Whisper fallback: %s", e)
        return ""


async def synthesize_speech(text: str) -> bytes | None:
    """
    Synthesizes speech from text using Google Gemini TTS.
    Returns OGG Opus formatted bytes suitable for WhatsApp.
    """
    if not text or not text.strip():
        return None
        
    client = get_genai_client()
    if not client:
        logger.error("Gemini genai Client is not initialized. Cannot synthesize speech.")
        return None

    # Format prompt to explicitly instruct speech synthesis
    prompt = f"Please synthesize the following text into spoken audio:\n\n{text}"

    from google.genai import types

    def _call_gemini_tts():
        response = client.models.generate_content(
            model="gemini-3.1-flash-tts-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore",
                        )
                    )
                ),
            )
        )
        return response.candidates[0].content.parts[0].inline_data.data

    # Implement automated retry logic in case of transient errors or text token returns
    pcm_bytes = None
    for attempt in range(3):
        try:
            pcm_bytes = await asyncio.to_thread(_call_gemini_tts)
            if pcm_bytes:
                break
        except Exception as e:
            if attempt == 2:
                logger.error("Gemini TTS synthesis failed after 3 attempts: %s", e)
                return None
            logger.warning("Gemini TTS attempt %d failed, retrying... Error: %s", attempt + 1, e)
            await asyncio.sleep(1)

    if not pcm_bytes:
        return None

    # Convert raw PCM (s16le) to OGG Opus
    ogg_bytes = await convert_pcm_to_ogg(pcm_bytes)
    return ogg_bytes
