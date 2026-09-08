"""Local, version-dispatched compact schema-order UTF-8 JSON (no BOM/newline).

Finite integral numbers, including either signed zero, use integer JSON form.
Other floats use Python's shortest round-trip JSON representation. Parsing
requires byte equality, excluding alternate numeric spellings and whitespace.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import fields, is_dataclass

from pydantic import BaseModel

from playlist_narrative_engine.sequencing.successor_schemas import (
    ConstructionInputBindingV2, ConstructionPolicyV2, ConstructionResultV2,
    ConstructionTargetArtifact, ConstructionPrefix,
)


def _inspect(value):
    if isinstance(value, BaseModel):
        if set(value.__dict__) != set(type(value).model_fields) or value.model_extra:
            raise ValueError("unvalidated or expanded model content")
        for item in value.__dict__.values():
            _inspect(item)
    elif is_dataclass(value):
        if set(vars(value)) != {f.name for f in fields(value)}:
            raise ValueError("expanded dataclass content")
        for field in fields(value):
            _inspect(getattr(value, field.name))
    elif isinstance(value, (tuple, list)):
        for item in value:
            _inspect(item)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite numbers are not canonical")


def _zero(value):
    if isinstance(value, dict):
        return {key: _zero(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_zero(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonical_model_bytes(model: BaseModel) -> bytes:
    """Revalidate even model_construct/model_copy objects; never authorize by hash."""
    _inspect(model)
    raw = model.model_dump(mode="json")
    validated = type(model).model_validate(raw)
    normalized = validated.model_dump(mode="json")
    if json.dumps(raw, allow_nan=False) != json.dumps(normalized, allow_nan=False):
        raise ValueError("object requires normalization or discarded content")
    return json.dumps(_zero(normalized), ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def serialize_successor(artifact) -> bytes:
    if type(artifact) not in (ConstructionPolicyV2, ConstructionTargetArtifact,
                              ConstructionInputBindingV2, ConstructionResultV2):
        raise TypeError("explicit construction successor artifact required")
    return canonical_model_bytes(artifact)


def successor_sha256(artifact) -> str:
    return hashlib.sha256(serialize_successor(artifact)).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_successor(data: bytes, artifact_type):
    if artifact_type not in (ConstructionPolicyV2, ConstructionTargetArtifact,
                             ConstructionInputBindingV2, ConstructionResultV2):
        raise TypeError("unsupported successor version/type")
    return parse_canonical_model(data, artifact_type)


def parse_canonical_model(data: bytes, artifact_type):
    if type(data) is not bytes:
        raise TypeError("exact canonical bytes required")
    payload = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    model = artifact_type.model_validate(payload)
    if canonical_model_bytes(model) != data:
        raise ValueError("noncanonical, missing, expanded, or alternate JSON encoding")
    return model


def verify_successor_digest(artifact, expected: str) -> bool:
    return (isinstance(expected, str) and len(expected) == 64
            and all(c in "0123456789abcdef" for c in expected)
            and successor_sha256(artifact) == expected)


def construction_prefix_sha256(target, certificate, tracks, decisions):
    prefix = ConstructionPrefix(target_sha256=successor_sha256(target),
        formed_pool_sha256=certificate.formed_pool_sha256,
        planning_horizon=certificate.planning_horizon, tracks=tuple(tracks),
        decisions=tuple(d for d in decisions if d.position <= len(tracks)))
    return hashlib.sha256(canonical_model_bytes(prefix)).hexdigest()
