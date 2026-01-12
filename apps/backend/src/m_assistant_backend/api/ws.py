from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..dialog.manager import DialogManager
from ..settings import settings
from ..llm.stub import StubLLMAdapter
from ..stt.stub import StubSTTAdapter
from ..tts.opentts import OpenTTSAdapter
from ..tts.stub import StubTTSAdapter

router = APIRouter()


@dataclass
class AudioState:
    pcm16_mono_16khz: bytearray


def _get_dialog_manager() -> DialogManager:
    # Dialog Manager v0 uses a stub LLM for deterministic tests.
    if settings.llm_backend == "stub":
        return DialogManager(llm=StubLLMAdapter())

    raise ValueError(f"Unknown LLM_BACKEND: {settings.llm_backend}")


async def _stream_tts(ws: WebSocket, *, tts, text: str) -> None:
    started = time.perf_counter()
    tts_result = tts.synthesize_wav(text=text)
    audio = tts_result.audio_wav

    chunk_size = 16 * 1024
    seq = 0
    for i in range(0, len(audio), chunk_size):
        seq += 1
        chunk = audio[i : i + chunk_size]
        if seq == 1:
            ttfb_ms = int((time.perf_counter() - started) * 1000)
            await ws.send_json({"type": "tts.metrics", "ttfb_ms": ttfb_ms, "bytes": len(audio)})

        await ws.send_json(
            {
                "type": "tts.chunk",
                "seq": seq,
                "codec": "wav",
                "sample_rate": 16000,
                "payload_base64": base64.b64encode(chunk).decode("ascii"),
            }
        )

    await ws.send_json({"type": "tts.end", "chunks": seq})


def _get_stt_adapter():
    # Best practice: keep heavy deps optional.
    if settings.stt_backend == "stub":
        return StubSTTAdapter()

    if settings.stt_backend == "faster-whisper":
        from ..stt.faster_whisper_adapter import FasterWhisperSTTAdapter

        return FasterWhisperSTTAdapter(model=settings.stt_model, device=settings.stt_device)

    raise ValueError(f"Unknown STT_BACKEND: {settings.stt_backend}")


def _get_tts_adapter():
    if settings.tts_backend == "stub":
        return StubTTSAdapter()

    if settings.tts_backend == "opentts":
        return OpenTTSAdapter()

    raise ValueError(f"Unknown TTS_BACKEND: {settings.tts_backend}")


@router.websocket("/ws")
async def ws_gateway(ws: WebSocket) -> None:
    await ws.accept()

    stt = _get_stt_adapter()
    tts = _get_tts_adapter()
    dialog = _get_dialog_manager() if settings.dialog_enabled else None
    dialog_session = dialog.start_session() if dialog else None
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

                if dialog and dialog_session:
                    assistant_text = dialog.handle_user_text(session=dialog_session, user_text=result.text)
                    await ws.send_json({"type": "assistant.text", "text": assistant_text})
                    await _stream_tts(ws, tts=tts, text=assistant_text)
                continue

            if msg_type == "tts.request":
                text = msg.get("text")
                if not isinstance(text, str) or not text.strip():
                    await ws.send_json({"type": "error", "code": "bad_request", "message": "missing text"})
                    continue

                await _stream_tts(ws, tts=tts, text=text)
                continue

            await ws.send_json({"type": "error", "code": "bad_request", "message": f"unknown type: {msg_type}"})

    except WebSocketDisconnect:
        return
