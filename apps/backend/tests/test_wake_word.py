from fastapi.testclient import TestClient

from m_assistant_backend.main import app
from m_assistant_backend.settings import settings
from m_assistant_backend.wake.metrics import wake_detections_total


def test_wake_word_stub_triggers_after_threshold() -> None:
    client = TestClient(app)

    prev_wake = settings.wake_enabled
    prev_backend = settings.wake_backend

    settings.wake_enabled = True
    settings.wake_backend = "stub"

    try:
        import base64

        # Stub triggers after 32000 bytes (~1 second of 16kHz mono PCM16)
        chunk = b"\x00\x00" * 160  # 320 bytes = 10ms

        with client.websocket_connect("/ws") as ws:
            # Send exactly 100 chunks = 32000 bytes to trigger wake
            for i in range(100):
                ws.send_json({
                    "type": "audio.chunk",
                    "session_id": "test",
                    "seq": i + 1,
                    "codec": "pcm16",
                    "sample_rate": 16000,
                    "payload_base64": base64.b64encode(chunk).decode("ascii"),
                })
            
            # After 100 chunks (32000 bytes), next chunk should trigger
            ws.send_json({
                "type": "audio.chunk",
                "session_id": "test",
                "seq": 101,
                "codec": "pcm16",
                "sample_rate": 16000,
                "payload_base64": base64.b64encode(chunk).decode("ascii"),
            })
            
            # Now we should get wake.detected
            msg = ws.receive_json()
            assert msg["type"] == "wake.detected"
            assert msg["keyword"] == "stub"
            assert msg["confidence"] == 1.0

    finally:
        settings.wake_enabled = prev_wake
        settings.wake_backend = prev_backend


def test_wake_false_positive_reporting() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "wake.report_false_positive"})
        msg = ws.receive_json()
        assert msg["type"] == "wake.report_ack"
        assert msg["reported"] == "false_positive"


def test_wake_false_negative_reporting() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "wake.report_false_negative"})
        msg = ws.receive_json()
        assert msg["type"] == "wake.report_ack"
        assert msg["reported"] == "false_negative"
