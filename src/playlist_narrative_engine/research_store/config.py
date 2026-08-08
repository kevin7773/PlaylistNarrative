from __future__ import annotations

import os
from pathlib import Path


def default_research_database_url() -> str:
    configured = os.getenv("PNE_RESEARCH_DATABASE_URL")
    if configured:
        return configured
    path = Path("data") / "research" / "maestro_experiments.db"
    return f"sqlite:///{path.as_posix()}"
