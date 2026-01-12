from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..dialog.manager import DialogManager
from ..llm.proxy import create_llm_adapter_from_settings
from ..memory.db import create_session_factory
from ..memory.embeddings.factory import create_embedder_from_settings
from ..memory.retrieval.service import RetrievalService
from ..settings import settings
from ..stt.stub import StubSTTAdapter
from ..tts.opentts import OpenTTSAdapter
from ..tts.stub import StubTTSAdapter
from ..wake.factory import create_wake_detector_from_settings
from ..wake.metrics import (
    wake_detections_total,
    wake_false_negatives,
    wake_false_positives,
    wake_fp_count,
    wake_fn_count,
)
from ..stt.metrics import stt_latency_ms
from ..tts.metrics import tts_latency_ms

router = APIRouter()

ActivationMode = Literal["ptt", "hotword", "auto"]


@dataclass
class AudioState:
    pcm16_mono_16khz: bytearray
    wake_listening: bool = True  # Whether actively listening for wake-word
    activation_mode: ActivationMode = "auto"  # ptt, hotword, or auto
    wake_enabled_runtime: bool = True  # Runtime wake-word on/off toggle


def _get_dialog_manager() -> DialogManager:
    session_factory = None
    retrieval = None
    retrieval_model = None

    if settings.memory_enabled:
        session_factory = create_session_factory(database_url=settings.database_url)
        embedder = create_embedder_from_settings()
        retrieval = RetrievalService(embedder=embedder)
        retrieval_model = settings.embedder_model

    return DialogManager(
        llm=create_llm_adapter_from_settings(),
        memory_enabled=settings.memory_enabled,
        session_factory=session_factory,
        retrieval=retrieval,
        retrieval_model=retrieval_model,
        retrieval_top_k=settings.retrieval_top_k,
        retrieval_max_chars=settings.retrieval_max_chars,
    )


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
            tts_latency_ms.observe(ttfb_ms)
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
    wake_detector = create_wake_detector_from_settings() if settings.wake_enabled else None
    dialog = _get_dialog_manager() if settings.dialog_enabled else None
    dialog_session = None
    session_id: str | None = None
    state = AudioState(pcm16_mono_16khz=bytearray())

    try:
        while True:
            raw = await ws.receive_text()
            msg: dict[str, Any] = json.loads(raw)
            msg_type: str = msg.get("type", "")

            if session_id is None:
                sid = msg.get("session_id")
                if isinstance(sid, str) and sid.strip():
                    session_id = sid.strip()

            if dialog and dialog_session is None:
                # Default to a stable-but-generic session id when client doesn't provide it.
                dialog_session = dialog.start_session(session_id=session_id or "default")

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

                # Determine if we should process wake-word based on mode and runtime state
                should_process_wake = (
                    wake_detector 
                    and state.wake_enabled_runtime 
                    and state.activation_mode in ("hotword", "auto")
                    and state.wake_listening
                )

                # Wake-word detection if enabled
                if should_process_wake:
                    detection = wake_detector.process_audio(pcm16_mono_16khz=chunk)
                    if detection.detected:
                        wake_detections_total.labels(keyword=detection.keyword or "unknown").inc()
                        state.wake_listening = False
                        await ws.send_json({
                            "type": "wake.detected",
                            "keyword": detection.keyword,
                            "confidence": detection.confidence,
                        })
                        continue  # Don't accumulate or send stt.partial after wake
                    # Still listening for wake-word, don't accumulate audio yet
                    continue
                
                # Accumulate audio only after wake-word detected or when in PTT/auto mode without wake
                state.pcm16_mono_16khz.extend(chunk)
                # PoC: we do not generate real partials yet.
                await ws.send_json({"type": "stt.partial", "text": "…", "stability": 0.0})
                continue

            if msg_type == "control.end_of_utterance":
                stt_started = time.perf_counter()
                result = stt.transcribe_pcm16(bytes(state.pcm16_mono_16khz))
                stt_latency_ms.observe((time.perf_counter() - stt_started) * 1000.0)
                state.pcm16_mono_16khz.clear()
                
                # Reset wake-word listening after utterance
                if wake_detector:
                    state.wake_listening = True
                    wake_detector.reset()
                
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

            if msg_type == "wake.report_false_positive":
                wake_false_positives.inc()
                wake_fp_count.inc()
                await ws.send_json({"type": "wake.report_ack", "reported": "false_positive"})
                continue

            if msg_type == "wake.report_false_negative":
                wake_false_negatives.inc()
                wake_fn_count.inc()
                await ws.send_json({"type": "wake.report_ack", "reported": "false_negative"})
                continue

            if msg_type == "wake.set_mode":
                mode = msg.get("mode")
                if mode not in ("ptt", "hotword", "auto"):
                    await ws.send_json({
                        "type": "error", 
                        "code": "bad_request", 
                        "message": f"Invalid mode: {mode}. Must be 'ptt', 'hotword', or 'auto'"
                    })
                    continue
                
                state.activation_mode = mode  # type: ignore
                state.wake_listening = True  # Reset wake listening state
                if wake_detector:
                    wake_detector.reset()
                
                await ws.send_json({
                    "type": "wake.mode_changed",
                    "mode": mode,
                })
                continue

            if msg_type == "wake.enable":
                state.wake_enabled_runtime = True
                state.wake_listening = True
                if wake_detector:
                    wake_detector.reset()
                await ws.send_json({
                    "type": "wake.state_changed",
                    "enabled": True,
                })
                continue

            if msg_type == "wake.disable":
                state.wake_enabled_runtime = False
                state.wake_listening = False
                if wake_detector:
                    wake_detector.reset()
                await ws.send_json({
                    "type": "wake.state_changed",
                    "enabled": False,
                })
                continue

            if msg_type == "wake.get_status":
                await ws.send_json({
                    "type": "wake.status",
                    "enabled": state.wake_enabled_runtime,
                    "mode": state.activation_mode,
                    "listening": state.wake_listening,
                    "available": wake_detector is not None,
                })
                continue

            await ws.send_json({"type": "error", "code": "bad_request", "message": f"unknown type: {msg_type}"})

    except WebSocketDisconnect:
        return
