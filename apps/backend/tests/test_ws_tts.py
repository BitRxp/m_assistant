import base64

from fastapi.testclient import TestClient

from m_assistant_backend.main import app


def test_ws_tts_request_stub() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "tts.request", "text": "hello"})

        # First message can be metrics or chunk (depending on future changes)
        msg1 = ws.receive_json()
        assert msg1["type"] in {"tts.metrics", "tts.chunk"}

        chunks = []
        ended = False

        # Drain until tts.end
        for _ in range(50):
            msg = msg1 if _ == 0 else ws.receive_json()
            if msg["type"] == "tts.metrics":
                assert isinstance(msg.get("ttfb_ms"), int)
                continue
            if msg["type"] == "tts.chunk":
                payload = base64.b64decode(msg["payload_base64"])
                chunks.append(payload)
                continue
            if msg["type"] == "tts.end":
                ended = True
                break

        assert ended is True
        audio = b"".join(chunks)
        assert audio.startswith(b"RIFF")
