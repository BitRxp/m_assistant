from __future__ import annotations

from .base import WakeDetectionResult, WakeWordDetector


class StubWakeWordDetector(WakeWordDetector):
    """Deterministic stub for testing wake-word flows.
    
    Detects when audio buffer exceeds a threshold size, simulating
    a wake-word trigger without actual keyword detection.
    """

    def __init__(self, *, trigger_threshold_bytes: int = 32000) -> None:
        """
        Args:
            trigger_threshold_bytes: Bytes of audio to accumulate before triggering.
                Default 32000 = ~1 second at 16kHz mono PCM16.
        """
        self._threshold = trigger_threshold_bytes
        self._buffer = bytearray()

    def process_audio(self, *, pcm16_mono_16khz: bytes) -> WakeDetectionResult:
        self._buffer.extend(pcm16_mono_16khz)
        
        if len(self._buffer) >= self._threshold:
            self._buffer.clear()
            return WakeDetectionResult(detected=True, confidence=1.0, keyword="stub")
        
        return WakeDetectionResult(detected=False)

    def reset(self) -> None:
        self._buffer.clear()
