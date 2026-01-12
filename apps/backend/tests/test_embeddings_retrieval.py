from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from m_assistant_backend.memory.embeddings.stub import StubEmbedder
from m_assistant_backend.memory.retrieval.service import RetrievalService


def _alembic_config(*, db_url: str) -> Config:
    here = Path(__file__).resolve()
    backend_dir = here.parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_embeddings_retrieval_topk_and_context_limit(tmp_path: Path) -> None:
    db_path = tmp_path / "test_embeddings.sqlite"
    db_url = f"sqlite:///{db_path}"

    command.upgrade(_alembic_config(db_url=db_url), "head")

    engine = create_engine(db_url)
    embedder = StubEmbedder(model="stub", dims=16)
    svc = RetrievalService(embedder=embedder)

    with Session(engine) as session:
        svc.upsert_embedding(session=session, entity_type="custom", entity_id=1, text="I like pizza")
        svc.upsert_embedding(session=session, entity_type="custom", entity_id=2, text="My favorite color is blue")
        svc.upsert_embedding(session=session, entity_type="custom", entity_id=3, text="I have a cat named Miso")

        result = svc.retrieve(
            session=session,
            query="pizza",
            model="stub",
            top_k=2,
            max_chars=30,
        )

        assert len(result.hits) == 2
        assert len(result.context) <= 30
        # At least one returned item must mention pizza (basic relevance expectation)
        assert "pizza" in (result.hits[0][0].text + result.hits[1][0].text).lower()
