import pytest
import json
import asyncio
from httpx import AsyncClient, ASGITransport
from src.api.main import app

@pytest.mark.asyncio
async def test_webhook_urdu_audio_override(db_setup, monkeypatch):
    """Verify that when incoming message is audio and transcribed as Urdu, preference is overridden to roman_urdu."""
    captured_input = []

    async def mock_download_whatsapp_media(audio_id):
        return b"dummy_audio_bytes"

    async def mock_transcribe_audio(audio_bytes):
        return "مجھے اے سی ٹھیک کروانا ہے"

    async def mock_runner_run(*args, **kwargs):
        captured_input.append(kwargs.get("input"))
        class MockResult:
            final_output = "__NO_RESPONSE__"
        return MockResult()

    monkeypatch.setattr("src.api.routes.webhook.download_whatsapp_media", mock_download_whatsapp_media)
    monkeypatch.setattr("src.api.routes.webhook.transcribe_audio", mock_transcribe_audio)
    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)

    # WhatsApp payload for audio
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {"name": "Hammad"},
                                    "wa_id": "923001234567"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.audio123",
                                    "timestamp": "1715971200",
                                    "audio": {"id": "media_id_123"},
                                    "type": "audio"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.text == "OK"

    # Wait briefly for background asyncio task execution
    await asyncio.sleep(0.5)

    assert len(captured_input) == 1
    assert "Message Type is audio" in captured_input[0]


@pytest.mark.asyncio
async def test_webhook_english_audio_no_override(db_setup, monkeypatch):
    """Verify that when incoming message is audio and transcribed as English, preference remains english."""
    captured_input = []

    async def mock_download_whatsapp_media(audio_id):
        return b"dummy_audio_bytes"

    async def mock_transcribe_audio(audio_bytes):
        return "my AC is broken"

    async def mock_runner_run(*args, **kwargs):
        captured_input.append(kwargs.get("input"))
        class MockResult:
            final_output = "__NO_RESPONSE__"
        return MockResult()

    monkeypatch.setattr("src.api.routes.webhook.download_whatsapp_media", mock_download_whatsapp_media)
    monkeypatch.setattr("src.api.routes.webhook.transcribe_audio", mock_transcribe_audio)
    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)

    # WhatsApp payload for audio
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {"name": "Hammad"},
                                    "wa_id": "923001234567"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.audio124",
                                    "timestamp": "1715971200",
                                    "audio": {"id": "media_id_123"},
                                    "type": "audio"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.text == "OK"

    # Wait briefly for background asyncio task execution
    await asyncio.sleep(0.5)

    assert len(captured_input) == 1
    assert "Message Type is audio" in captured_input[0]


@pytest.mark.asyncio
async def test_webhook_no_response_suppressed(db_setup, monkeypatch):
    """Verify that when final response is __NO_RESPONSE__, we do not send any message to WhatsApp."""
    captured_messages = []

    async def mock_runner_run(*args, **kwargs):
        class MockResult:
            final_output = "__NO_RESPONSE__"
        return MockResult()

    async def mock_send_reply(to_phone, text):
        captured_messages.append(text)

    async def mock_send_whatsapp_audio(to_phone, media_id):
        captured_messages.append("AUDIO_REPLY")

    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)
    monkeypatch.setattr("src.api.routes.webhook._send_reply", mock_send_reply)
    monkeypatch.setattr("src.api.routes.webhook.send_whatsapp_audio", mock_send_whatsapp_audio)

    # WhatsApp payload for text
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {"name": "Hammad"},
                                    "wa_id": "923001234567"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.HBgLOTIzMDAxMjM0NTY3",
                                    "timestamp": "1715971200",
                                    "text": {"body": "Mujhe AC theek karwana hai"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.text == "OK"

    # Wait briefly for background asyncio task execution
    await asyncio.sleep(0.5)

    assert len(captured_messages) == 0


@pytest.mark.asyncio
async def test_audio_input_short_response_sends_audio_only(db_setup, monkeypatch):
    """Verify that a short response to audio input is sent as audio only, skipping text."""
    captured_messages = []

    async def mock_download_whatsapp_media(audio_id):
        return b"dummy_audio_bytes"

    async def mock_transcribe_audio(audio_bytes):
        return "Salam"

    async def mock_runner_run(*args, **kwargs):
        class MockResult:
            final_output = "Walaikum Assalam, mein aapki kya madad kar sakta hoon?"
        return MockResult()

    async def mock_synthesize_speech(text):
        return b"dummy_speech_bytes"

    async def mock_upload_whatsapp_media(media_bytes, mime_type):
        return "new_media_id_456"

    async def mock_send_whatsapp_audio(to_phone, media_id):
        captured_messages.append(("audio", media_id))

    async def mock_send_reply(to_phone, text):
        captured_messages.append(("text", text))

    monkeypatch.setattr("src.api.routes.webhook.download_whatsapp_media", mock_download_whatsapp_media)
    monkeypatch.setattr("src.api.routes.webhook.transcribe_audio", mock_transcribe_audio)
    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)
    monkeypatch.setattr("src.api.routes.webhook.synthesize_speech", mock_synthesize_speech)
    monkeypatch.setattr("src.api.routes.webhook.upload_whatsapp_media", mock_upload_whatsapp_media)
    monkeypatch.setattr("src.api.routes.webhook.send_whatsapp_audio", mock_send_whatsapp_audio)
    monkeypatch.setattr("src.api.routes.webhook._send_reply", mock_send_reply)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [{"profile": {"name": "Hammad"}, "wa_id": "923001234567"}],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.audio_short",
                                    "timestamp": "1715971200",
                                    "audio": {"id": "media_id_123"},
                                    "type": "audio"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200

    # Wait briefly for background execution to complete
    await asyncio.sleep(0.5)

    # Should only contain audio message, no text message
    assert len(captured_messages) == 1
    assert captured_messages[0] == ("audio", "new_media_id_456")


@pytest.mark.asyncio
async def test_audio_input_long_response_sends_text_only(db_setup, monkeypatch):
    """Verify that a long response (>250 chars) to audio input is sent as text only, skipping audio."""
    captured_messages = []

    async def mock_download_whatsapp_media(audio_id):
        return b"dummy_audio_bytes"

    async def mock_transcribe_audio(audio_bytes):
        return "Salam"

    # Very long response > 250 characters
    long_response = "A" * 260

    async def mock_runner_run(*args, **kwargs):
        class MockResult:
            final_output = long_response
        return MockResult()

    async def mock_synthesize_speech(text):
        return b"dummy_speech_bytes"

    async def mock_upload_whatsapp_media(media_bytes, mime_type):
        return "new_media_id_456"

    async def mock_send_whatsapp_audio(to_phone, media_id):
        captured_messages.append(("audio", media_id))

    async def mock_send_reply(to_phone, text):
        captured_messages.append(("text", text))

    monkeypatch.setattr("src.api.routes.webhook.download_whatsapp_media", mock_download_whatsapp_media)
    monkeypatch.setattr("src.api.routes.webhook.transcribe_audio", mock_transcribe_audio)
    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)
    monkeypatch.setattr("src.api.routes.webhook.synthesize_speech", mock_synthesize_speech)
    monkeypatch.setattr("src.api.routes.webhook.upload_whatsapp_media", mock_upload_whatsapp_media)
    monkeypatch.setattr("src.api.routes.webhook.send_whatsapp_audio", mock_send_whatsapp_audio)
    monkeypatch.setattr("src.api.routes.webhook._send_reply", mock_send_reply)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [{"profile": {"name": "Hammad"}, "wa_id": "923001234567"}],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.audio_long",
                                    "timestamp": "1715971200",
                                    "audio": {"id": "media_id_123"},
                                    "type": "audio"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200

    # Wait briefly for background execution to complete
    await asyncio.sleep(0.5)

    # Should only contain text message, no audio message
    assert len(captured_messages) == 1
    assert captured_messages[0] == ("text", long_response)


@pytest.mark.asyncio
async def test_audio_input_failed_synthesis_falls_back_to_text(db_setup, monkeypatch):
    """Verify that if voice note synthesis fails, it falls back to sending the text message."""
    captured_messages = []

    async def mock_download_whatsapp_media(audio_id):
        return b"dummy_audio_bytes"

    async def mock_transcribe_audio(audio_bytes):
        return "Salam"

    async def mock_runner_run(*args, **kwargs):
        class MockResult:
            final_output = "Walaikum Assalam"
        return MockResult()

    async def mock_synthesize_speech(text):
        # Trigger failure/error
        raise Exception("OpenAI TTS Service Unavailable")

    async def mock_send_whatsapp_audio(to_phone, media_id):
        captured_messages.append(("audio", media_id))

    async def mock_send_reply(to_phone, text):
        captured_messages.append(("text", text))

    monkeypatch.setattr("src.api.routes.webhook.download_whatsapp_media", mock_download_whatsapp_media)
    monkeypatch.setattr("src.api.routes.webhook.transcribe_audio", mock_transcribe_audio)
    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)
    monkeypatch.setattr("src.api.routes.webhook.synthesize_speech", mock_synthesize_speech)
    monkeypatch.setattr("src.api.routes.webhook.send_whatsapp_audio", mock_send_whatsapp_audio)
    monkeypatch.setattr("src.api.routes.webhook._send_reply", mock_send_reply)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [{"profile": {"name": "Hammad"}, "wa_id": "923001234567"}],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.audio_fail",
                                    "timestamp": "1715971200",
                                    "audio": {"id": "media_id_123"},
                                    "type": "audio"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200

    # Wait briefly for background execution to complete
    await asyncio.sleep(0.5)

    # Should fall back to text message
    assert len(captured_messages) == 1
    assert captured_messages[0] == ("text", "Walaikum Assalam")


@pytest.mark.asyncio
async def test_webhook_structured_output_suppressed(db_setup, monkeypatch):
    """Verify that when final output has send_reply=False, no response is sent to WhatsApp."""
    from src.api.agent import UstaadAgentOutput
    captured_messages = []

    async def mock_runner_run(*args, **kwargs):
        class MockResult:
            final_output = UstaadAgentOutput(
                send_reply=False,
                message_type="text",
                message_to_send=""
            )
        return MockResult()

    async def mock_send_reply(to_phone, text):
        captured_messages.append(("text", text))

    async def mock_send_whatsapp_audio(to_phone, media_id):
        captured_messages.append(("audio", media_id))

    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)
    monkeypatch.setattr("src.api.routes.webhook._send_reply", mock_send_reply)
    monkeypatch.setattr("src.api.routes.webhook.send_whatsapp_audio", mock_send_whatsapp_audio)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [{"profile": {"name": "Hammad"}, "wa_id": "923001234567"}],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.structured_suppress",
                                    "timestamp": "1715971200",
                                    "text": {"body": "I am sending standard message"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200

    await asyncio.sleep(0.5)
    assert len(captured_messages) == 0


@pytest.mark.asyncio
async def test_webhook_structured_output_voice(db_setup, monkeypatch):
    """Verify that when final output has message_type='voice', a voice note is sent."""
    from src.api.agent import UstaadAgentOutput
    captured_messages = []

    async def mock_runner_run(*args, **kwargs):
        class MockResult:
            final_output = UstaadAgentOutput(
                send_reply=True,
                message_type="voice",
                message_to_send="Aapka kaam ho gaya hai"
            )
        return MockResult()

    async def mock_synthesize_speech(text):
        return b"dummy_speech_bytes"

    async def mock_upload_whatsapp_media(media_bytes, mime_type):
        return "new_media_id_789"

    async def mock_send_whatsapp_audio(to_phone, media_id):
        captured_messages.append(("audio", media_id))

    async def mock_send_reply(to_phone, text):
        captured_messages.append(("text", text))

    monkeypatch.setattr("src.api.routes.webhook.Runner.run", mock_runner_run)
    monkeypatch.setattr("src.api.routes.webhook.synthesize_speech", mock_synthesize_speech)
    monkeypatch.setattr("src.api.routes.webhook.upload_whatsapp_media", mock_upload_whatsapp_media)
    monkeypatch.setattr("src.api.routes.webhook.send_whatsapp_audio", mock_send_whatsapp_audio)
    monkeypatch.setattr("src.api.routes.webhook._send_reply", mock_send_reply)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [{"profile": {"name": "Hammad"}, "wa_id": "923001234567"}],
                            "messages": [
                                {
                                    "from": "923001234567",
                                    "id": "wamid.structured_voice",
                                    "timestamp": "1715971200",
                                    "text": {"body": "Voice test"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/webhook", json=payload)
    assert response.status_code == 200

    await asyncio.sleep(0.5)
    # Should only contain audio message, no text message
    assert len(captured_messages) == 1
    assert captured_messages[0] == ("audio", "new_media_id_789")
