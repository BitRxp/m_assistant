from __future__ import annotations

from ...settings import settings
from .base import Embedder
from .fastembed_adapter import FastEmbedder
from .stub import StubEmbedder


def create_embedder_from_settings() -> Embedder:
    if settings.embedder_backend == "stub":
        return StubEmbedder(model=settings.embedder_model)

    if settings.embedder_backend == "fastembed":
        return FastEmbedder(model=settings.embedder_model)

    raise ValueError(f"Unknown EMBEDDER_BACKEND: {settings.embedder_backend}")
