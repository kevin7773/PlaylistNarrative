from __future__ import annotations

import os
from pathlib import Path


def default_database_url() -> str:
    configured = os.getenv("PNE_DATABASE_URL")
    if configured:
        return configured
    database_path = Path("data") / "playlist_narrative.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{database_path.as_posix()}"

