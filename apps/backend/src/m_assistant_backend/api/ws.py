from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..settings import settings
from ..stt.stub import StubSTTAdapter

router = APIRouter()


@dataclass
class AudioState:
    pcm16_mono_16khz: bytearray


def _get_stt_adapter():
    # Best practice: keep heavy deps optional.
    if settings.stt_backend == "stub":
        return StubSTTAdapter()

    if settings.stt_backend == "faster-whisper":
        from ..stt.faster_whisper_adapter import FasterWhisperSTTAdapter

        return FasterWhisperSTTAdapter(model=settings.stt_model, device=settings.stt_device)

    raise ValueError(f"Unknown STT_BACKEND: {settings.stt_backend}")


@router.websocket("/ws")
async def ws_gateway(ws: WebSocket) -> None:
    await ws.accept()

    stt = _get_stt_adapter()
    state = AudioState(pcm16_mono_16khz=bytearray())

    try:
        while True:
            raw = await ws.receive_text()
            msg: dict[str, Any] = json.loads(raw)
            msg_type: str = msg.get("type", "")

            if msg_type == "audio.chunk":
                payload_b64 = msg.get("payload_base64")
                if not isinstance(payload_b64, str) or not payload_b64:
                    await ws.send_json({"type": "error", "code": "bad_request", "message": "missing payload_base64"})
                    continue

                try:
                    chunk = base64.b64decode(payload_b64)
                except Exception:  # noqa: BLE001
                    await ws.send_json({"type": "error", "code": "bad_request", "message": "invalid base64"})
                    continue

                state.pcm16_mono_16khz.extend(chunk)
                # PoC: we do not generate real partials yet.
                await ws.send_json({"type": "stt.partial", "text": "…", "stability": 0.0})
                continue

            if msg_type == "control.end_of_utterance":
                result = stt.transcribe_pcm16(bytes(state.pcm16_mono_16khz))
                state.pcm16_mono_16khz.clear()
                await ws.send_json({"type": "stt.final", "text": result.text})
                continue

            await ws.send_json({"type": "error", "code": "bad_request", "message": f"unknown type: {msg_type}"})

    except WebSocketDisconnect:
        return
