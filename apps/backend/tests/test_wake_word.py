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


def test_wake_mode_switching() -> None:
    """Test switching between PTT, hotword, and auto activation modes."""
    client = TestClient(app)

    prev_wake = settings.wake_enabled
    settings.wake_enabled = True

    try:
        with client.websocket_connect("/ws") as ws:
            # Test mode change to PTT
            ws.send_json({"type": "wake.set_mode", "mode": "ptt"})
            msg = ws.receive_json()
            assert msg["type"] == "wake.mode_changed"
            assert msg["mode"] == "ptt"

            # Test mode change to hotword
            ws.send_json({"type": "wake.set_mode", "mode": "hotword"})
            msg = ws.receive_json()
            assert msg["type"] == "wake.mode_changed"
            assert msg["mode"] == "hotword"

            # Test mode change to auto
            ws.send_json({"type": "wake.set_mode", "mode": "auto"})
            msg = ws.receive_json()
            assert msg["type"] == "wake.mode_changed"
            assert msg["mode"] == "auto"

            # Test invalid mode
            ws.send_json({"type": "wake.set_mode", "mode": "invalid"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "bad_request"

    finally:
        settings.wake_enabled = prev_wake


def test_wake_runtime_enable_disable() -> None:
    """Test enabling and disabling wake-word detection at runtime."""
    client = TestClient(app)

    prev_wake = settings.wake_enabled
    settings.wake_enabled = True

    try:
        with client.websocket_connect("/ws") as ws:
            # Test disabling wake
            ws.send_json({"type": "wake.disable"})
            msg = ws.receive_json()
            assert msg["type"] == "wake.state_changed"
            assert msg["enabled"] is False

            # Test re-enabling wake
            ws.send_json({"type": "wake.enable"})
            msg = ws.receive_json()
            assert msg["type"] == "wake.state_changed"
            assert msg["enabled"] is True

    finally:
        settings.wake_enabled = prev_wake


def test_wake_get_status() -> None:
    """Test getting current wake-word status."""
    client = TestClient(app)

    prev_wake = settings.wake_enabled
    settings.wake_enabled = True

    try:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "wake.get_status"})
            msg = ws.receive_json()
            assert msg["type"] == "wake.status"
            assert "enabled" in msg
            assert "mode" in msg
            assert "listening" in msg
            assert "available" in msg
            assert msg["available"] is True  # Wake detector should be available

    finally:
        settings.wake_enabled = prev_wake


def test_wake_ptt_mode_skips_detection() -> None:
    """Test that PTT mode bypasses wake-word detection and accumulates audio immediately."""
    client = TestClient(app)

    prev_wake = settings.wake_enabled
    prev_backend = settings.wake_backend

    settings.wake_enabled = True
    settings.wake_backend = "stub"

    try:
        import base64

        chunk = b"\x00\x00" * 160  # 320 bytes

        with client.websocket_connect("/ws") as ws:
            # Set to PTT mode
            ws.send_json({"type": "wake.set_mode", "mode": "ptt"})
            msg = ws.receive_json()
            assert msg["type"] == "wake.mode_changed"
            assert msg["mode"] == "ptt"

            # Send audio chunks - should accumulate immediately, not wait for wake
            ws.send_json({
                "type": "audio.chunk",
                "session_id": "test",
                "payload_base64": base64.b64encode(chunk).decode("ascii"),
            })
            
            # Should get stt.partial, NOT wake.detected
            msg = ws.receive_json()
            assert msg["type"] == "stt.partial"

    finally:
        settings.wake_enabled = prev_wake
        settings.wake_backend = prev_backend
