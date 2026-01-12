from __future__ import annotations

from .base import STTAdapter, STTResult


class StubSTTAdapter(STTAdapter):
    def transcribe_pcm16(self, pcm16_mono_16khz: bytes) -> STTResult:
        # Deterministic, test-friendly fallback.
        length_ms = int(len(pcm16_mono_16khz) / 2 / 16) if pcm16_mono_16khz else 0
        return STTResult(text=f"stub transcript ({length_ms}ms)")
