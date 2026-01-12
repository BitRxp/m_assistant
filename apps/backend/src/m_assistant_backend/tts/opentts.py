from __future__ import annotations

import httpx

from ..settings import settings
from .base import TTSAdapter, TTSResult


class OpenTTSAdapter(TTSAdapter):
    def __init__(self, base_url: str | None = None, voice: str | None = None):
        self._base_url = (base_url or settings.opentts_base_url).rstrip("/")
        self._voice = voice or settings.opentts_voice

    def synthesize_wav(self, *, text: str) -> TTSResult:
        # OpenTTS: GET /api/tts?voice=...&text=...
        with httpx.Client(timeout=15.0) as client:
            r = client.get(
                f"{self._base_url}/api/tts",
                params={"voice": self._voice, "text": text},
            )
            r.raise_for_status()
            return TTSResult(audio_wav=r.content)
