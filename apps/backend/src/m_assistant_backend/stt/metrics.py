from __future__ import annotations

from prometheus_client import Histogram

stt_latency_ms = Histogram(
    "stt_latency_ms",
    "Latency of STT transcription in milliseconds",
    buckets=(25, 50, 100, 200, 400, 800, 1600, 3200, 6400),
)
