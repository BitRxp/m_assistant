from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(*, database_url: str) -> sessionmaker[Session]:
    # SQLite defaults are fine for PoC; for multithreaded FastAPI use, we set check_same_thread=False.
    connect_args = {}
    if database_url.startswith("sqlite:"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(database_url, connect_args=connect_args)
    return sessionmaker(bind=engine, expire_on_commit=False)
