from __future__ import annotations

import hashlib
import re

from .base import Embedder, EmbeddingVector


class StubEmbedder(Embedder):
    """Deterministic, dependency-free embedder for unit tests.

    Not semantically meaningful, but stable and good enough to validate
    that indexing/retrieval plumbing works.
    """

    def __init__(self, *, model: str = "stub", dims: int = 16) -> None:
        self._model = model
        self._dims = dims

    def embed(self, *, texts: list[str]) -> list[EmbeddingVector]:
        out: list[EmbeddingVector] = []
        for text in texts:
            vec = self._token_hash_to_unit_vector(text)
            out.append(EmbeddingVector(model=self._model, dims=self._dims, vector=vec))
        return out

    def _token_hash_to_unit_vector(self, text: str) -> list[float]:
        # Dependency-free, deterministic bag-of-words style embedding.
        # Texts with overlapping tokens tend to be more similar.
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            tokens = [text.lower().strip()]

        floats = [0.0 for _ in range(self._dims)]
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self._dims
            sign = -1.0 if (digest[4] & 1) else 1.0
            floats[idx] += sign

        # L2 normalize
        norm = sum(x * x for x in floats) ** 0.5
        if norm <= 1e-12:
            return floats
        return [x / norm for x in floats]
