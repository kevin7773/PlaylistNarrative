from __future__ import annotations

import hashlib
import json
import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class FrozenAuthorityModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def model_content(model: BaseModel) -> dict[str, object]:
    return model.model_dump(mode="json", exclude={"canonical_sha256"})


def verify_or_set_digest(model: BaseModel) -> None:
    expected = canonical_sha256(model_content(model))
    actual = getattr(model, "canonical_sha256", None)
    if actual is None:
        object.__setattr__(model, "canonical_sha256", expected)
    elif actual != expected:
        raise ValueError("canonical SHA-256 does not match exact content")


def require_exact(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("authority identities must be nonblank and exact")
    return value


def validate_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("structured parameters require finite JSON numbers")
        return value
    if isinstance(value, list):
        return [validate_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [validate_json_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) or not key for key in value):
            raise ValueError("structured parameter object keys must be nonblank strings")
        return {key: validate_json_value(item) for key, item in value.items()}
    raise ValueError("structured parameters must contain only exact JSON values")


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    return value
