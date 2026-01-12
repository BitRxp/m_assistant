from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TTSResult:
    audio_wav: bytes


class TTSAdapter:
    def synthesize_wav(self, *, text: str) -> TTSResult:
        raise NotImplementedError
