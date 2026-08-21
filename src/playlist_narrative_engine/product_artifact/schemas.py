from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from playlist_narrative_engine.evaluation import EvaluationReport
from playlist_narrative_engine.sequencing import (
    ConstructionResult,
    ConstructionStatus,
)


FINAL_PRODUCT_SCHEMA_VERSION = "1.0"


class RefinementDisposition(StrEnum):
    NOT_PERFORMED = "NOT_PERFORMED"


@dataclass(frozen=True)
class ConstituentAuthority:
    identity: str
    schema_version: str
    canonical_sha256: str


@dataclass(frozen=True)
class PlacementAuthorityReference:
    position: int
    track_id: str
    formed_ordinal: int


@dataclass(frozen=True)
class FinalProductContent:
    schema_version: str
    artifact_kind: str
    artifact_id: str
    journey_authority: ConstituentAuthority
    formation_authority: ConstituentAuthority
    construction_policy_authority: ConstituentAuthority
    construction_authority: ConstituentAuthority
    evaluation_authority: ConstituentAuthority
    construction_result: ConstructionResult
    evaluation_report: EvaluationReport
    placement_authorities: tuple[PlacementAuthorityReference, ...]
    final_status: ConstructionStatus
    refinement_disposition: RefinementDisposition


@dataclass(frozen=True)
class FinalProductArtifact:
    content: FinalProductContent
    canonical_sha256: str
