from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..repo import create_embedding, list_embeddings
from ..models import Embedding
from ..embeddings.base import Embedder
from .context import build_context
from .index import HnswIndex, pack_f32_vector, unpack_f32_vector


@dataclass(frozen=True)
class RetrievalResult:
    hits: list[tuple[Embedding, float]]
    context: str


class RetrievalService:
    def __init__(self, *, embedder: Embedder) -> None:
        self._embedder = embedder

    def upsert_embedding(
        self,
        *,
        session: Session,
        entity_type: str,
        entity_id: int,
        text: str,
    ) -> Embedding:
        vec = self._embedder.embed(texts=[text])[0]
        return create_embedding(
            session=session,
            entity_type=entity_type,
            entity_id=entity_id,
            model=vec.model,
            dims=vec.dims,
            vector=pack_f32_vector(vec.vector),
            text=text,
        )

    def retrieve(
        self,
        *,
        session: Session,
        query: str,
        model: str,
        top_k: int,
        max_chars: int,
    ) -> RetrievalResult:
        rows = list_embeddings(session=session, model=model)
        if not rows:
            return RetrievalResult(hits=[], context="")

        dims = rows[0].dims
        index = HnswIndex(dims=dims)
        items: list[tuple[int, list[float], str]] = []
        for r in rows:
            if r.dims != dims:
                continue
            items.append((r.id, unpack_f32_vector(r.vector), r.text))
        index.build(items=items)

        qvec = self._embedder.embed(texts=[query])[0]
        if qvec.dims != dims:
            return RetrievalResult(hits=[], context="")

        hits = index.search(query=qvec.vector, k=top_k)
        id_to_row = {r.id: r for r in rows}
        paired: list[tuple[Embedding, float]] = []
        for h in hits:
            row = id_to_row.get(h.embedding_id)
            if row is None:
                continue
            paired.append((row, h.score))

        # best-first order (already) -> context
        context_texts = [row.text for row, _ in paired]
        context = build_context(texts=context_texts, max_chars=max_chars)
        return RetrievalResult(hits=paired, context=context)
