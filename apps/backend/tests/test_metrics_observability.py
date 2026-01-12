import base64
from typing import Any

from fastapi.testclient import TestClient

from m_assistant_backend.main import app
from m_assistant_backend.settings import settings


def _drain_until(ws, stop_types: set[str]) -> None:
    for _ in range(50):  # safety cap
        msg = ws.receive_json()
        if msg.get("type") in stop_types:
            return
    raise AssertionError("Did not receive expected end message")


def test_metrics_exposed_and_counted() -> None:
    client = TestClient(app)

    prev = {
        "wake_enabled": settings.wake_enabled,
        "dialog_enabled": settings.dialog_enabled,
        "memory_enabled": settings.memory_enabled,
        "stt_backend": settings.stt_backend,
        "tts_backend": settings.tts_backend,
    }

    settings.wake_enabled = False  # simplify flow
    settings.dialog_enabled = True
    settings.memory_enabled = False
    settings.stt_backend = "stub"
    settings.tts_backend = "stub"

    try:
        chunk = b"\x00\x00" * 160
        payload = base64.b64encode(chunk).decode("ascii")

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "audio.chunk", "session_id": "test", "payload_base64": payload})
            ws.receive_json()  # stt.partial

            ws.send_json({"type": "control.end_of_utterance", "session_id": "test"})
            assert ws.receive_json()["type"] == "stt.final"
            assert ws.receive_json()["type"] == "assistant.text"
            _drain_until(ws, {"tts.end"})

            ws.send_json({"type": "tts.request", "text": "hello"})
            _drain_until(ws, {"tts.end"})

            ws.send_json({"type": "wake.report_false_positive"})
            ws.receive_json()
            ws.send_json({"type": "wake.report_false_negative"})
            ws.receive_json()

        metrics = client.get("/metrics").text
        assert "stt_latency_ms" in metrics
        assert "tts_latency_ms" in metrics
        assert "llm_latency_ms" in metrics
        assert "llm_provider_selected" in metrics
        assert "wake_fp_count" in metrics
        assert "wake_fn_count" in metrics

    finally:
        settings.wake_enabled = prev["wake_enabled"]
        settings.dialog_enabled = prev["dialog_enabled"]
        settings.memory_enabled = prev["memory_enabled"]
        settings.stt_backend = prev["stt_backend"]
        settings.tts_backend = prev["tts_backend"]
