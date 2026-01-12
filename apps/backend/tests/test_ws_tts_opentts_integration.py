import base64
import os

import httpx
import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_OPENTTS_SMOKE") != "1",
    reason="Set RUN_OPENTTS_SMOKE=1 to run OpenTTS integration smoke test",
)


def test_opentts_container_is_up() -> None:
    base_url = os.getenv("OPENTTS_BASE_URL", "http://localhost:5500").rstrip("/")
    r = httpx.get(f"{base_url}/api/languages", timeout=5.0)
    r.raise_for_status()
    assert isinstance(r.json(), list)


def test_ws_tts_request_opentts_returns_wav() -> None:
    # These must be set in the environment BEFORE pytest imports the app.
    assert os.getenv("TTS_BACKEND") == "opentts"

    from m_assistant_backend.main import app

    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "tts.request", "text": "hello from opentts"})

        chunks: list[bytes] = []
        seen_metrics = False

        for _ in range(200):
            msg = ws.receive_json()
            if msg["type"] == "tts.metrics":
                seen_metrics = True
                assert isinstance(msg.get("ttfb_ms"), int)
                continue
            if msg["type"] == "tts.chunk":
                payload = base64.b64decode(msg["payload_base64"])
                chunks.append(payload)
                continue
            if msg["type"] == "tts.end":
                break

        assert seen_metrics is True
        audio = b"".join(chunks)
        assert audio.startswith(b"RIFF")
        assert b"WAVE" in audio[:64]
