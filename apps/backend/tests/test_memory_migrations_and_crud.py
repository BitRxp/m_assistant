from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from m_assistant_backend.memory.repo import create_summary, create_turn, list_facts, list_summaries, list_turns, upsert_fact


def _alembic_config(*, db_url: str) -> Config:
    here = Path(__file__).resolve()
    backend_dir = here.parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.mark.parametrize("db_name", ["test_memory.sqlite"])
def test_memory_schema_migrations_and_crud(tmp_path: Path, db_name: str) -> None:
    db_path = tmp_path / db_name
    db_url = f"sqlite:///{db_path}"

    # Run migrations
    command.upgrade(_alembic_config(db_url=db_url), "head")

    # Sanity check tables exist
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("select 1"))

    # CRUD
    with Session(engine) as session:
        turn = create_turn(session=session, session_id="s1", user_text="hi", assistant_text="hello")
        assert turn.id > 0

        turns = list_turns(session=session, session_id="s1")
        assert len(turns) >= 1
        assert turns[0].session_id == "s1"

        fact1 = upsert_fact(session=session, key="name", value="Oleks", turn_id=turn.id)
        assert fact1.id > 0

        fact2 = upsert_fact(session=session, key="name", value="Oleks2", turn_id=turn.id)
        assert fact2.id == fact1.id
        assert fact2.value == "Oleks2"

        facts = list_facts(session=session)
        assert any(f.key == "name" for f in facts)

        summary = create_summary(session=session, session_id="s1", text="summary text")
        assert summary.id > 0

        summaries = list_summaries(session=session, session_id="s1")
        assert len(summaries) >= 1
        assert summaries[0].session_id == "s1"
