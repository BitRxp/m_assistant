#!/usr/bin/env python3
"""Simple latency benchmark for m_assistant WebSocket gateway.

Requires:
    pip install websockets

Usage:
    python scripts/bench_latency.py --ws ws://127.0.0.1:8000/ws --turns 3
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import statistics
import time
from typing import Any

import websockets


def _now_ms() -> float:
    return time.perf_counter() * 1000.0


async def _recv_json(ws, *, timeout_s: float | None = None) -> dict[str, Any]:
    if timeout_s is None:
        raw = await ws.recv()
    else:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
    return json.loads(raw)


async def measure_stt(ws, session_id: str, *, recv_timeout_s: float, verbose: bool) -> dict[str, float]:
    metrics: dict[str, float] = {}

    chunk = b"\x00\x00" * 160  # 320 bytes
    payload = base64.b64encode(chunk).decode("ascii")

    if verbose:
        print("  sending audio.chunk")
    await ws.send(json.dumps({"type": "audio.chunk", "session_id": session_id, "payload_base64": payload}))
    # stt.partial (best-effort)
    try:
        await _recv_json(ws, timeout_s=min(1.0, recv_timeout_s))
    except Exception:
        pass

    stt_start = _now_ms()
    if verbose:
        print("  sending control.end_of_utterance")
    await ws.send(json.dumps({"type": "control.end_of_utterance", "session_id": session_id}))

    # Expect stt.final
    deadline = time.perf_counter() + recv_timeout_s
    last_type: str | None = None
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            raise TimeoutError(f"Timed out waiting for stt.final (last={last_type})")
        msg = await _recv_json(ws, timeout_s=remaining)
        last_type = str(msg.get("type")) if "type" in msg else None
        if msg.get("type") == "stt.final":
            metrics["stt_latency_ms"] = _now_ms() - stt_start
            break

    # Optional: if dialog is enabled, backend may send assistant.text + tts stream
    try:
        dialog_start = _now_ms()
        msg = await _recv_json(ws, timeout_s=min(0.5, recv_timeout_s))
        if msg.get("type") == "assistant.text":
            metrics["dialog_to_assistant_ms"] = _now_ms() - dialog_start
            # Drain any automatic TTS
            tts_start = _now_ms()
            while True:
                m = await _recv_json(ws, timeout_s=recv_timeout_s)
                if m.get("type") == "tts.chunk":
                    metrics.setdefault("auto_tts_ttfb_ms", _now_ms() - tts_start)
                if m.get("type") == "tts.end":
                    metrics.setdefault("auto_tts_total_ms", _now_ms() - tts_start)
                    break
    except Exception:
        pass

    return metrics


async def measure_tts(ws, *, text: str, recv_timeout_s: float, verbose: bool) -> dict[str, float]:
    metrics: dict[str, float] = {}

    tts_start = _now_ms()
    if verbose:
        print("  sending tts.request")
    await ws.send(json.dumps({"type": "tts.request", "text": text}))

    deadline = time.perf_counter() + recv_timeout_s
    last_type: str | None = None
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            raise TimeoutError(f"Timed out waiting for tts.end (last={last_type})")
        msg = await _recv_json(ws, timeout_s=remaining)
        last_type = str(msg.get("type")) if "type" in msg else None
        if msg.get("type") == "tts.chunk":
            metrics.setdefault("tts_ttfb_ms", _now_ms() - tts_start)
        if msg.get("type") == "tts.end":
            metrics["tts_total_ms"] = _now_ms() - tts_start
            break

    return metrics


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ws", default="ws://127.0.0.1:8000/ws", help="WebSocket URL")
    parser.add_argument("--turns", type=int, default=3, help="How many turns to run")
    parser.add_argument("--session", default="bench", help="Session ID")
    parser.add_argument("--tts-text", default="hello from benchmark", help="Text for tts.request")
    parser.add_argument(
        "--recv-timeout",
        type=float,
        default=10.0,
        help="Timeout (seconds) for waiting on expected WS messages",
    )
    parser.add_argument("--connect-timeout", type=float, default=5.0, help="Timeout (seconds) for WS connect")
    parser.add_argument("--verbose", action="store_true", help="Print progress logs")
    args = parser.parse_args()

    if args.verbose:
        print(f"connecting: {args.ws}")

    try:
        async with websockets.connect(args.ws, open_timeout=args.connect_timeout) as ws:
            if args.verbose:
                print("connected")

            results: list[dict[str, float]] = []
            for i in range(args.turns):
                if args.verbose:
                    print(f"turn {i+1}/{args.turns}")

                metrics: dict[str, float] = {}
                metrics.update(
                    await measure_stt(ws, args.session, recv_timeout_s=args.recv_timeout, verbose=args.verbose)
                )
                metrics.update(
                    await measure_tts(ws, text=args.tts_text, recv_timeout_s=args.recv_timeout, verbose=args.verbose)
                )
                results.append(metrics)
                print(f"turn {i+1}: {metrics}")
    except OSError as e:
        raise SystemExit(
            "Failed to connect to backend.\n"
            f"  url: {args.ws}\n"
            f"  error: {e}\n\n"
            "Checks:\n"
            "  - Backend is running and listening on the same host/port\n"
            "  - Try: http://127.0.0.1:8000/health\n"
            "  - If backend runs in Docker/WSL, use the correct host IP and port mapping\n"
        )

    def agg(key: str) -> float:
        vals = [r[key] for r in results if key in r]
        return statistics.mean(vals) if vals else float("nan")

    summary = {
        "turns": args.turns,
        "stt_latency_ms_avg": agg("stt_latency_ms"),
        "tts_ttfb_ms_avg": agg("tts_ttfb_ms"),
        "tts_total_ms_avg": agg("tts_total_ms"),
    }
    print("\nSummary:")
    for k, v in summary.items():
        print(f"  {k}: {v:.2f}")


if __name__ == "__main__":
    asyncio.run(main())