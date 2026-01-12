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


async def run_turn(ws, session_id: str) -> dict[str, float]:
    metrics: dict[str, float] = {}

    chunk = b"\x00\x00" * 160  # 320 bytes
    payload = base64.b64encode(chunk).decode("ascii")

    started = _now_ms()
    await ws.send(json.dumps({"type": "audio.chunk", "session_id": session_id, "payload_base64": payload}))
    # stt.partial
    await ws.recv()

    stt_start = _now_ms()
    await ws.send(json.dumps({"type": "control.end_of_utterance", "session_id": session_id}))

    stt_final = json.loads(await ws.recv())
    assert stt_final.get("type") == "stt.final"
    metrics["stt_latency_ms"] = _now_ms() - stt_start

    asst = json.loads(await ws.recv())
    assert asst.get("type") == "assistant.text"

    # Drain TTS stream
    tts_start = _now_ms()
    while True:
        msg = json.loads(await ws.recv())
        if msg.get("type") == "tts.chunk":
            if "tts_ttfb_ms" not in metrics:
                metrics["tts_ttfb_ms"] = _now_ms() - tts_start
        if msg.get("type") == "tts.end":
            metrics.setdefault("tts_total_ms", _now_ms() - tts_start)
            break

    metrics["turn_total_ms"] = _now_ms() - started
    return metrics


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ws", default="ws://127.0.0.1:8000/ws", help="WebSocket URL")
    parser.add_argument("--turns", type=int, default=3, help="How many turns to run")
    parser.add_argument("--session", default="bench", help="Session ID")
    args = parser.parse_args()

    async with websockets.connect(args.ws) as ws:
        results: list[dict[str, float]] = []
        for i in range(args.turns):
            metrics = await run_turn(ws, args.session)
            results.append(metrics)
            print(f"turn {i+1}: {metrics}")

    def agg(key: str) -> float:
        vals = [r[key] for r in results if key in r]
        return statistics.mean(vals) if vals else float("nan")

    summary = {
        "turns": args.turns,
        "stt_latency_ms_avg": agg("stt_latency_ms"),
        "tts_ttfb_ms_avg": agg("tts_ttfb_ms"),
        "tts_total_ms_avg": agg("tts_total_ms"),
        "turn_total_ms_avg": agg("turn_total_ms"),
    }
    print("\nSummary:")
    for k, v in summary.items():
        print(f"  {k}: {v:.2f}")


if __name__ == "__main__":
    asyncio.run(main())