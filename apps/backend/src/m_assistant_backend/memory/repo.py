from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Fact, Summary, Turn


def create_turn(*, session: Session, session_id: str, user_text: str, assistant_text: str) -> Turn:
    turn = Turn(session_id=session_id, user_text=user_text, assistant_text=assistant_text)
    session.add(turn)
    session.commit()
    session.refresh(turn)
    return turn


def list_turns(*, session: Session, session_id: str, limit: int = 50) -> list[Turn]:
    stmt = select(Turn).where(Turn.session_id == session_id).order_by(Turn.id.desc()).limit(limit)
    return list(session.execute(stmt).scalars())


def upsert_fact(*, session: Session, key: str, value: str, turn_id: int | None = None) -> Fact:
    existing = session.execute(select(Fact).where(Fact.key == key)).scalar_one_or_none()
    if existing is None:
        fact = Fact(key=key, value=value, turn_id=turn_id)
        session.add(fact)
        session.commit()
        session.refresh(fact)
        return fact

    existing.value = value
    existing.turn_id = turn_id
    session.commit()
    session.refresh(existing)
    return existing


def list_facts(*, session: Session, limit: int = 100) -> list[Fact]:
    stmt = select(Fact).order_by(Fact.id.desc()).limit(limit)
    return list(session.execute(stmt).scalars())


def create_summary(*, session: Session, session_id: str, text: str, scope: str = "session") -> Summary:
    summary = Summary(session_id=session_id, text=text, scope=scope)
    session.add(summary)
    session.commit()
    session.refresh(summary)
    return summary


def list_summaries(*, session: Session, session_id: str, limit: int = 50) -> list[Summary]:
    stmt = select(Summary).where(Summary.session_id == session_id).order_by(Summary.id.desc()).limit(limit)
    return list(session.execute(stmt).scalars())
