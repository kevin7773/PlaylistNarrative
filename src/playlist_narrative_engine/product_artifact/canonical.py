from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel

from playlist_narrative_engine.product_artifact.schemas import (
    FinalProductArtifact,
    FinalProductContent,
)


def serialize_final_product_content(content: FinalProductContent) -> bytes:
    return _canonical_bytes(asdict(content))


def final_product_content_sha256(content: FinalProductContent) -> str:
    return hashlib.sha256(serialize_final_product_content(content)).hexdigest()


def serialize_final_product_artifact(artifact: FinalProductArtifact) -> bytes:
    return _canonical_bytes(asdict(artifact))


def verify_final_product_digest(artifact: FinalProductArtifact) -> bool:
    return artifact.canonical_sha256 == final_product_content_sha256(
        artifact.content
    )


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


def _json_default(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"unsupported final-product value: {type(value)!r}")
