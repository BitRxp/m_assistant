from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WakeDetectionResult:
    detected: bool
    confidence: float = 0.0
    keyword: str = ""


class WakeWordDetector:
    """Base interface for wake-word detection adapters."""

    def process_audio(self, *, pcm16_mono_16khz: bytes) -> WakeDetectionResult:
        """Process audio chunk and return detection result.
        
        Args:
            pcm16_mono_16khz: Raw PCM16 audio at 16kHz mono.
            
        Returns:
            WakeDetectionResult with detection status.
        """
        raise NotImplementedError
    
    def reset(self) -> None:
        """Reset internal detector state between sessions."""
        pass
