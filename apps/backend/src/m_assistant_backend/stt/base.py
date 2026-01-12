from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class STTResult:
    text: str


class STTAdapter:
    def transcribe_pcm16(self, pcm16_mono_16khz: bytes) -> STTResult:
        raise NotImplementedError
