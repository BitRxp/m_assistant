from __future__ import annotations

from .base import WakeDetectionResult, WakeWordDetector


def _require_porcupine():
    try:
        import pvporcupine  # type: ignore
        return pvporcupine
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "pvporcupine is not installed. Install with: pip install -e .[wake]"
        ) from exc


class PorcupineWakeWordDetector(WakeWordDetector):
    """Picovoice Porcupine wake-word detector.
    
    Requires pvporcupine library and an access key from Picovoice.
    """

    def __init__(
        self,
        *,
        access_key: str,
        keywords: list[str] | None = None,
        sensitivity: float = 0.5,
    ) -> None:
        """
        Args:
            access_key: Picovoice access key.
            keywords: List of built-in keywords (e.g., ["porcupine", "computer"]).
            sensitivity: Detection sensitivity [0.0, 1.0]. Higher = more sensitive.
        """
        pvporcupine = _require_porcupine()
        
        if not keywords:
            keywords = ["computer"]
        
        # Porcupine expects sensitivity per keyword
        sensitivities = [sensitivity] * len(keywords)
        
        self._porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=keywords,
            sensitivities=sensitivities,
        )
        self._keywords = keywords
        self._frame_length = self._porcupine.frame_length
        self._sample_rate = self._porcupine.sample_rate
        self._buffer = bytearray()

    def process_audio(self, *, pcm16_mono_16khz: bytes) -> WakeDetectionResult:
        """Process audio in frames required by Porcupine (typically 512 samples = 1024 bytes)."""
        self._buffer.extend(pcm16_mono_16khz)
        
        bytes_per_frame = self._frame_length * 2  # 16-bit = 2 bytes per sample
        
        while len(self._buffer) >= bytes_per_frame:
            frame_bytes = bytes(self._buffer[:bytes_per_frame])
            self._buffer = self._buffer[bytes_per_frame:]
            
            # Convert bytes to int16 array
            import struct
            pcm = struct.unpack(f"<{self._frame_length}h", frame_bytes)
            
            keyword_index = self._porcupine.process(pcm)
            
            if keyword_index >= 0:
                detected_keyword = self._keywords[keyword_index]
                return WakeDetectionResult(
                    detected=True,
                    confidence=1.0,
                    keyword=detected_keyword,
                )
        
        return WakeDetectionResult(detected=False)

    def reset(self) -> None:
        self._buffer.clear()

    def __del__(self) -> None:
        if hasattr(self, "_porcupine"):
            self._porcupine.delete()
