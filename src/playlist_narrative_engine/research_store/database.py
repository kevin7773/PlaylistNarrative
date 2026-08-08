from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from playlist_narrative_engine.research_store.config import (
    default_research_database_url,
)


class ResearchBase(DeclarativeBase):
    """Metadata isolated from Penny's production persistence metadata."""


def _configure_sqlite(dbapi_connection: sqlite3.Connection, _: object) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def make_research_engine(database_url: str | None = None) -> Engine:
    url = database_url or default_research_database_url()
    parsed = make_url(url)
    if parsed.drivername != "sqlite":
        raise ValueError("The research evidence store supports SQLite only")
    if parsed.database not in (None, "", ":memory:"):
        Path(parsed.database).expanduser().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _configure_sqlite)
    return engine


def make_research_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
