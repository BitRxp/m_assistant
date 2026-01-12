from __future__ import annotations

from .base import STTAdapter, STTResult


class FasterWhisperSTTAdapter(STTAdapter):
    def __init__(self, model: str, device: str):
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "faster-whisper is not installed. Install backend with: pip install -e .[stt]"
            ) from exc

        # Note: model download can be large; for CI/tests we default to stub.
        self._model = WhisperModel(model, device=device)

    def transcribe_pcm16(self, pcm16_mono_16khz: bytes) -> STTResult:
        # faster-whisper expects a path or numpy audio array; to keep this PoC light,
        # we require callers to provide WAV in future iteration.
        # For now, raise a clear message so the integration step is explicit.
        raise NotImplementedError(
            "faster-whisper adapter is wired, but raw PCM->transcribe is not implemented yet. "
            "Next step: wrap PCM into WAV or stream via ffmpeg/av, then call model.transcribe()."
        )
