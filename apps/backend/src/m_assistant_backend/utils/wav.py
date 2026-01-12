from __future__ import annotations

import io
import wave


def generate_silence_wav(*, duration_ms: int, sample_rate: int = 16000) -> bytes:
    duration_ms = max(0, int(duration_ms))
    sample_rate = int(sample_rate)
    n_samples = int(sample_rate * (duration_ms / 1000.0))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_samples)

    return buf.getvalue()
