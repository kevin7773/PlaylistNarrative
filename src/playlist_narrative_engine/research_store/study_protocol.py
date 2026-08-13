from __future__ import annotations

import hashlib
import json

from playlist_narrative_engine.research_store.study_schemas import StudyProtocolInput


def canonical_protocol_bytes(
    study_key: str,
    title: str,
    protocol: StudyProtocolInput,
) -> bytes:
    """Return the exact UTF-8 JSON hashed for a registered protocol snapshot.

    Canonicalization is deliberately mechanical: Pydantic JSON-mode values,
    lexicographically sorted object keys, preserved list order, no insignificant
    whitespace, literal Unicode, and no implicit value normalization.
    """
    document = {
        "study_key": study_key,
        "title": title,
        "protocol": protocol.model_dump(mode="json"),
    }
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def protocol_registration_hash(
    study_key: str,
    title: str,
    protocol: StudyProtocolInput,
) -> str:
    return hashlib.sha256(canonical_protocol_bytes(study_key, title, protocol)).hexdigest()
