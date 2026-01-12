from __future__ import annotations

from .base import Embedder, EmbeddingVector


class FastEmbedder(Embedder):
    def __init__(self, *, model: str) -> None:
        self._model = model

        try:
            from fastembed import TextEmbedding
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "fastembed is not installed. Install with: pip install -e .[memory]"
            ) from exc

        self._impl = TextEmbedding(model_name=model)

    def embed(self, *, texts: list[str]) -> list[EmbeddingVector]:
        vectors = list(self._impl.embed(texts))
        if not vectors:
            return []

        dims = len(vectors[0])
        out: list[EmbeddingVector] = []
        for v in vectors:
            out.append(EmbeddingVector(model=self._model, dims=dims, vector=[float(x) for x in v]))
        return out
