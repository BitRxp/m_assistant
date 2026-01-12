from __future__ import annotations

from prometheus_client import Histogram

tts_latency_ms = Histogram(
    "tts_latency_ms",
    "Time to first audio (TTFB) for TTS in milliseconds",
    buckets=(25, 50, 100, 200, 400, 800, 1600, 3200, 6400, 12800),
)
