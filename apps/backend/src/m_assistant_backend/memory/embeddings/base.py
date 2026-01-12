from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingVector:
    model: str
    dims: int
    vector: list[float]


class Embedder:
    def embed(self, *, texts: list[str]) -> list[EmbeddingVector]:
        raise NotImplementedError
