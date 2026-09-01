from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def canonical_json_bytes(value: object, *, exclude_digest: bool = False) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(
            mode="json",
            exclude={"canonical_sha256"} if exclude_digest else None,
        )
    if isinstance(value, Enum):
        value = value.value
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_sha256(value: object, *, exclude_digest: bool = False) -> str:
    return sha256_bytes(canonical_json_bytes(value, exclude_digest=exclude_digest))


def verify_or_set_digest(model: BaseModel) -> None:
    expected = canonical_sha256(model, exclude_digest=True)
    actual = getattr(model, "canonical_sha256", None)
    if actual is None:
        object.__setattr__(model, "canonical_sha256", expected)
    elif actual != expected:
        raise ValueError("canonical SHA-256 does not match exact content")


def derived_digest(label: str, *values: str) -> str:
    return sha256_bytes("\n".join((label, *values)).encode("utf-8"))


def require_exact(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("identity must be nonblank and exact")
    value.encode("utf-8")
    return value


def reject_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result
