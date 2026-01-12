from __future__ import annotations

import math
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchHit:
    embedding_id: int
    score: float
    text: str


def _require_hnswlib():
    try:
        import hnswlib  # type: ignore

        return hnswlib
    except Exception:
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0

    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=False):
        dot += x * y
        na += x * x
        nb += y * y

    denom = math.sqrt(na) * math.sqrt(nb)
    if denom <= 1e-12:
        return 0.0
    return dot / denom


class HnswIndex:
    def __init__(self, *, dims: int) -> None:
        hnswlib = _require_hnswlib()
        self._dims = dims
        self._hnswlib = hnswlib
        self._index = hnswlib.Index(space="cosine", dim=dims) if hnswlib else None
        self._id_to_text: dict[int, str] = {}
        self._items: list[tuple[int, list[float], str]] = []

    @property
    def dims(self) -> int:
        return self._dims

    def build(self, *, items: list[tuple[int, list[float], str]]) -> None:
        self._items = items
        self._id_to_text = {item_id: text for item_id, _, text in items}

        if self._index is None:
            return

        if not items:
            self._index.init_index(max_elements=1, ef_construction=100, M=16)
            return

        self._index.init_index(max_elements=len(items), ef_construction=200, M=16)
        ids = [item_id for item_id, _, _ in items]
        vectors = [vec for _, vec, _ in items]
        self._index.add_items(vectors, ids)
        self._index.set_ef(min(64, max(10, len(items))))

    def search(self, *, query: list[float], k: int) -> list[SearchHit]:
        if k <= 0:
            return []

        if self._index is None:
            scored: list[SearchHit] = []
            for item_id, vec, text in self._items:
                scored.append(
                    SearchHit(
                        embedding_id=item_id,
                        score=_cosine_similarity(query, vec),
                        text=text,
                    )
                )
            scored.sort(key=lambda h: h.score, reverse=True)
            return scored[: min(k, len(scored))]

        labels, distances = self._index.knn_query([query], k=min(k, len(self._id_to_text) or 1))
        hits: list[SearchHit] = []
        for item_id, dist in zip(labels[0], distances[0], strict=False):
            if item_id == -1:
                continue
            # hnswlib cosine distance = 1 - cosine_similarity
            score = 1.0 - float(dist)
            hits.append(SearchHit(embedding_id=int(item_id), score=score, text=self._id_to_text.get(int(item_id), "")))
        return hits


def pack_f32_vector(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def unpack_f32_vector(blob: bytes) -> list[float]:
    if len(blob) % 4 != 0:
        raise ValueError("invalid float32 vector blob")
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))
