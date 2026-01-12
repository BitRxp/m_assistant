from __future__ import annotations

from ..utils.wav import generate_silence_wav
from .base import TTSAdapter, TTSResult


class StubTTSAdapter(TTSAdapter):
    def synthesize_wav(self, *, text: str) -> TTSResult:
        # Deterministic small WAV; duration scales slightly with text length.
        duration_ms = 200 + min(800, len(text) * 20)
        return TTSResult(audio_wav=generate_silence_wav(duration_ms=duration_ms))
