from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Engine, inspect, select

from playlist_narrative_engine.research_store.database import ResearchBase
from playlist_narrative_engine.research_store.models import SchemaVersion

CURRENT_SCHEMA_VERSION = 1


def get_schema_version(engine: Engine) -> int:
    if "schema_version" not in inspect(engine).get_table_names():
        return 0
    with engine.connect() as connection:
        versions = list(connection.scalars(select(SchemaVersion.version)))
    return max(versions, default=0)


def migrate_research_database(engine: Engine) -> int:
    current = get_schema_version(engine)
    if current > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Research database schema {current} is newer than supported "
            f"schema {CURRENT_SCHEMA_VERSION}"
        )
    if current == 0:
        # Version 1 is the complete initial research schema. create_all is used only
        # against the research-only metadata and is enclosed with its version record.
        ResearchBase.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                SchemaVersion.__table__.insert().values(
                    version=1, applied_at=datetime.now(timezone.utc)
                )
            )
        current = 1
    return current
