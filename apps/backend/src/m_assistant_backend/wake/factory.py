from __future__ import annotations

from ..settings import settings
from .base import WakeWordDetector
from .porcupine_adapter import PorcupineWakeWordDetector
from .stub import StubWakeWordDetector


def create_wake_detector_from_settings() -> WakeWordDetector:
    if settings.wake_backend == "stub":
        return StubWakeWordDetector()

    if settings.wake_backend == "porcupine":
        keywords = [k.strip() for k in settings.wake_porcupine_keywords.split(",") if k.strip()]
        if not keywords:
            keywords = ["computer"]
        
        return PorcupineWakeWordDetector(
            access_key=settings.wake_porcupine_access_key,
            keywords=keywords,
            sensitivity=settings.wake_porcupine_sensitivity,
        )

    raise ValueError(f"Unknown WAKE_BACKEND: {settings.wake_backend}")
