from __future__ import annotations

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from playlist_narrative_engine.db import (
    initialize_database,
    make_engine,
    make_session_factory,
)


@pytest.fixture
def engine(tmp_path) -> Engine:
    value = make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    initialize_database(value)
    return value


@pytest.fixture
def session(engine: Engine) -> Session:
    factory = make_session_factory(engine)
    with factory() as value:
        yield value

