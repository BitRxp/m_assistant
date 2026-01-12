import base64

from fastapi.testclient import TestClient

from m_assistant_backend.main import app


def test_ws_audio_to_stt_final_stub() -> None:
    client = TestClient(app)

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
        assert "stub transcript" in msg2["text"]
