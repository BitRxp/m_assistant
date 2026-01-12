import base64

from fastapi.testclient import TestClient

from m_assistant_backend.main import app
from m_assistant_backend.settings import settings


def test_ws_dialog_manager_v0_stub_llm_and_tts() -> None:
    client = TestClient(app)

    prev_dialog_enabled = settings.dialog_enabled
    prev_llm_backend = settings.llm_backend

    settings.dialog_enabled = True
    settings.llm_backend = "stub"

    try:
        pcm16 = b"\x00\x00" * 160  # 10ms of silence at 16kHz mono, 16-bit

        with client.websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "type": "audio.chunk",
                    "session_id": "s1",
                    "seq": 1,
                    "codec": "pcm16",
                    "sample_rate": 16000,
                    "payload_base64": base64.b64encode(pcm16).decode("ascii"),
                }
            )
            msg1 = ws.receive_json()
            assert msg1["type"] == "stt.partial"

            ws.send_json({"type": "control.end_of_utterance", "session_id": "s1"})

            msg2 = ws.receive_json()
            assert msg2["type"] == "stt.final"

            msg3 = ws.receive_json()
            assert msg3["type"] == "assistant.text"
            assert "stub" in msg3["text"]

            # Then: TTS stream for assistant response
            msg4 = ws.receive_json()
            assert msg4["type"] in {"tts.metrics", "tts.chunk"}

            chunks = []
            ended = False

            for i in range(60):
                msg = msg4 if i == 0 else ws.receive_json()
                if msg["type"] == "tts.metrics":
                    assert isinstance(msg.get("ttfb_ms"), int)
                    continue
                if msg["type"] == "tts.chunk":
                    chunks.append(base64.b64decode(msg["payload_base64"]))
                    continue
                if msg["type"] == "tts.end":
                    ended = True
                    break

            assert ended is True
            audio = b"".join(chunks)
            assert audio.startswith(b"RIFF")

    finally:
        settings.dialog_enabled = prev_dialog_enabled
        settings.llm_backend = prev_llm_backend
