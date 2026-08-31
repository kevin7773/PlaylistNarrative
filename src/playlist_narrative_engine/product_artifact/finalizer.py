from __future__ import annotations

import hashlib

from playlist_narrative_engine.candidate_formation import (
    CANDIDATE_FORMATION_SCHEMA_VERSION,
    CANDIDATE_FORMATION_SCHEMA_VERSION_V2,
    CandidateEligibilityState,
    CandidateFormationArtifact,
    FormedCandidateEntry,
    FormedCandidatePoolView,
    derive_formed_candidate_pool,
    serialize_candidate_formation,
)
from playlist_narrative_engine.evaluation import (
    EVALUATION_SCHEMA_VERSION,
    EvaluationDisposition,
    EvaluationReport,
    evaluation_report_matches_inputs,
    evaluation_report_sha256,
)
from playlist_narrative_engine.journey import (
    JOURNEY_PLAN_SCHEMA_VERSION,
    JourneyPlanArtifact,
    serialize_journey_plan_artifact,
)
from playlist_narrative_engine.product_artifact.canonical import (
    final_product_content_sha256,
    verify_final_product_digest,
)
from playlist_narrative_engine.product_artifact.schemas import (
    FINAL_PRODUCT_SCHEMA_VERSION,
    ConstituentAuthority,
    FinalProductArtifact,
    FinalProductContent,
    PlacementAuthorityReference,
    RefinementDisposition,
)
from playlist_narrative_engine.sequencing import (
    ConstructionPolicy,
    ConstructionResult,
    ConstructionStatus,
    construction_policy_sha256,
    construction_result_matches_inputs,
    construction_result_sha256,
)
from playlist_narrative_engine.sequencing.constructor import (
    CONSTRUCTION_POLICY_SCHEMA_VERSION,
    CONSTRUCTION_RESULT_SCHEMA_VERSION,
)


class FinalProductFinalizer:
    """Bind already-authoritative product results without executing them."""

    __slots__ = ()

    def finalize(
        self,
        *,
        artifact_id: str,
        journey_plan: JourneyPlanArtifact,
        candidate_formation: CandidateFormationArtifact,
        formed_pool: FormedCandidatePoolView,
        construction_policy: ConstructionPolicy,
        construction_result: ConstructionResult,
        evaluation_report: EvaluationReport,
        refinement_disposition: RefinementDisposition = (
            RefinementDisposition.NOT_PERFORMED
        ),
    ) -> FinalProductArtifact:
        self._require_supported_inputs(
            artifact_id=artifact_id,
            journey_plan=journey_plan,
            candidate_formation=candidate_formation,
            formed_pool=formed_pool,
            construction_policy=construction_policy,
            construction_result=construction_result,
            evaluation_report=evaluation_report,
            refinement_disposition=refinement_disposition,
        )
        formation_sha256 = _sha256(
            serialize_candidate_formation(candidate_formation)
        )
        self._validate_authority(
            journey_plan=journey_plan,
            candidate_formation=candidate_formation,
            formed_pool=formed_pool,
            formation_sha256=formation_sha256,
            construction_policy=construction_policy,
            construction_result=construction_result,
            evaluation_report=evaluation_report,
        )
        placement_authorities = self._resolve_placements(
            construction_result,
            candidate_formation,
        )
        self._validate_construction_disposition(construction_result)
        self._validate_evaluation_disposition(
            construction_result,
            evaluation_report,
        )
        content = FinalProductContent(
            schema_version=FINAL_PRODUCT_SCHEMA_VERSION,
            artifact_kind="playlist_narrative_final_product",
            artifact_id=artifact_id,
            journey_authority=ConstituentAuthority(
                identity=journey_plan.journey_id,
                schema_version=journey_plan.schema_version,
                canonical_sha256=_sha256(
                    serialize_journey_plan_artifact(journey_plan)
                ),
            ),
            formation_authority=ConstituentAuthority(
                identity=candidate_formation.request_id,
                schema_version=candidate_formation.schema_version,
                canonical_sha256=formation_sha256,
            ),
            construction_policy_authority=ConstituentAuthority(
                identity="construction_policy",
                schema_version=CONSTRUCTION_POLICY_SCHEMA_VERSION,
                canonical_sha256=construction_policy_sha256(
                    construction_policy
                ),
            ),
            construction_authority=ConstituentAuthority(
                identity=candidate_formation.request_id,
                schema_version=construction_result.schema_version,
                canonical_sha256=construction_result_sha256(
                    construction_result
                ),
            ),
            evaluation_authority=ConstituentAuthority(
                identity=candidate_formation.request_id,
                schema_version=evaluation_report.schema_version,
                canonical_sha256=evaluation_report_sha256(evaluation_report),
            ),
            construction_result=construction_result,
            evaluation_report=evaluation_report,
            placement_authorities=placement_authorities,
            final_status=construction_result.summary.status,
            refinement_disposition=refinement_disposition,
        )
        return FinalProductArtifact(
            content=content,
            canonical_sha256=final_product_content_sha256(content),
        )

    @staticmethod
    def _require_supported_inputs(**values: object) -> None:
        expected_types = {
            "artifact_id": str,
            "journey_plan": JourneyPlanArtifact,
            "candidate_formation": CandidateFormationArtifact,
            "formed_pool": FormedCandidatePoolView,
            "construction_policy": ConstructionPolicy,
            "construction_result": ConstructionResult,
            "evaluation_report": EvaluationReport,
            "refinement_disposition": RefinementDisposition,
        }
        for name, expected in expected_types.items():
            if not isinstance(values[name], expected):
                raise TypeError(f"{name} must be {expected.__name__}")
        artifact_id = values["artifact_id"]
        if not artifact_id or artifact_id != artifact_id.strip():
            raise ValueError("final product artifact identity must be nonblank and exact")
        journey = values["journey_plan"]
        formation = values["candidate_formation"]
        result = values["construction_result"]
        report = values["evaluation_report"]
        if journey.schema_version != JOURNEY_PLAN_SCHEMA_VERSION:
            raise ValueError("unsupported journey artifact schema version")
        if formation.schema_version not in {
            CANDIDATE_FORMATION_SCHEMA_VERSION,
            CANDIDATE_FORMATION_SCHEMA_VERSION_V2,
        }:
            raise ValueError("unsupported Candidate Formation schema version")
        if result.schema_version != CONSTRUCTION_RESULT_SCHEMA_VERSION:
            raise ValueError("unsupported construction-result schema version")
        if report.schema_version != EVALUATION_SCHEMA_VERSION:
            raise ValueError("unsupported evaluation-report schema version")

    @staticmethod
    def _validate_authority(
        *,
        journey_plan: JourneyPlanArtifact,
        candidate_formation: CandidateFormationArtifact,
        formed_pool: FormedCandidatePoolView,
        formation_sha256: str,
        construction_policy: ConstructionPolicy,
        construction_result: ConstructionResult,
        evaluation_report: EvaluationReport,
    ) -> None:
        expected_pool = derive_formed_candidate_pool(candidate_formation)
        if formed_pool != expected_pool:
            raise ValueError(
                "formed pool must be the exact authenticated formation projection"
            )
        if formed_pool.trace.parent_artifact_sha256 != formation_sha256:
            raise ValueError("Candidate Formation digest mismatch")
        if (
            candidate_formation.journey_id != journey_plan.journey_id
            or candidate_formation.objective_id
            != journey_plan.objective.objective_id
            or candidate_formation.objective_statement
            != journey_plan.objective.statement
            or candidate_formation.accepted_objective_artifact_id
            != journey_plan.objective_safety_artifact_id
        ):
            raise ValueError("journey and Candidate Formation authority mismatch")
        if not construction_result_matches_inputs(
            construction_result,
            journey_plan=journey_plan,
            formed_pool=formed_pool,
            construction_policy=construction_policy,
        ):
            raise ValueError("construction binding/digest authority mismatch")
        if not evaluation_report_matches_inputs(
            evaluation_report,
            construction_result=construction_result,
            journey_plan=journey_plan,
            construction_policy=construction_policy,
        ):
            raise ValueError("evaluation binding/digest authority mismatch")

    @staticmethod
    def _resolve_placements(
        construction_result: ConstructionResult,
        candidate_formation: CandidateFormationArtifact,
    ) -> tuple[PlacementAuthorityReference, ...]:
        formed_by_id = {
            entry.candidate.track_id: entry for entry in candidate_formation.formed
        }
        references: list[PlacementAuthorityReference] = []
        for placement in construction_result.tracks:
            entry = formed_by_id.get(placement.candidate.track_id)
            if entry is None:
                raise ValueError("final placement is absent from authenticated formed pool")
            FinalProductFinalizer._require_eligible_entry(entry)
            if entry.candidate != placement.candidate:
                raise ValueError("final placement candidate differs from formed authority")
            references.append(
                PlacementAuthorityReference(
                    position=placement.position,
                    track_id=placement.candidate.track_id,
                    formed_ordinal=entry.ordinal,
                )
            )
        return tuple(references)

    @staticmethod
    def _require_eligible_entry(entry: FormedCandidateEntry) -> None:
        for result in entry.constraint_eligibility:
            if result.state is CandidateEligibilityState.UNKNOWN:
                raise ValueError("UNKNOWN hard-constraint candidate cannot be finalized")
            if result.state is CandidateEligibilityState.INELIGIBLE:
                raise ValueError("INELIGIBLE hard-constraint candidate cannot be finalized")
            if result.state is not CandidateEligibilityState.ELIGIBLE:
                raise ValueError("unsupported candidate eligibility state")

    @staticmethod
    def _validate_construction_disposition(result: ConstructionResult) -> None:
        tracks = result.tracks
        summary = result.summary
        if summary.achieved_track_count != len(tracks):
            raise ValueError("construction summary does not match final placements")
        if tuple(item.position for item in tracks) != tuple(
            range(1, len(tracks) + 1)
        ):
            raise ValueError("final placement order must be contiguous and exact")
        if summary.status is ConstructionStatus.COMPLETE:
            valid = summary.achieved_track_count == summary.requested_track_count
        elif summary.status is ConstructionStatus.PARTIAL:
            valid = 0 < summary.achieved_track_count < summary.requested_track_count
        elif summary.status is ConstructionStatus.INFEASIBLE:
            valid = summary.achieved_track_count == 0 and not tracks
        else:
            valid = False
        if not valid:
            raise ValueError("construction disposition is inconsistent")

    @staticmethod
    def _validate_evaluation_disposition(
        result: ConstructionResult,
        report: EvaluationReport,
    ) -> None:
        expected = {
            ConstructionStatus.COMPLETE: EvaluationDisposition.COMPLETE_EVALUATED,
            ConstructionStatus.PARTIAL: EvaluationDisposition.PARTIAL_EVALUATED,
            ConstructionStatus.INFEASIBLE: EvaluationDisposition.INCONCLUSIVE,
        }[result.summary.status]
        if report.construction_status is not result.summary.status:
            raise ValueError("evaluation construction status mismatch")
        if report.disposition is not expected:
            raise ValueError("evaluation disposition mismatch")


def verify_final_product_artifact(
    artifact: FinalProductArtifact,
    *,
    journey_plan: JourneyPlanArtifact,
    candidate_formation: CandidateFormationArtifact,
    formed_pool: FormedCandidatePoolView,
    construction_policy: ConstructionPolicy,
) -> bool:
    if not isinstance(artifact, FinalProductArtifact):
        return False
    if not verify_final_product_digest(artifact):
        return False
    content = artifact.content
    try:
        reproduced = FinalProductFinalizer().finalize(
            artifact_id=content.artifact_id,
            journey_plan=journey_plan,
            candidate_formation=candidate_formation,
            formed_pool=formed_pool,
            construction_policy=construction_policy,
            construction_result=content.construction_result,
            evaluation_report=content.evaluation_report,
            refinement_disposition=content.refinement_disposition,
        )
    except (TypeError, ValueError):
        return False
    return reproduced == artifact


def resolve_final_placement_authorities(
    artifact: FinalProductArtifact,
    candidate_formation: CandidateFormationArtifact,
) -> tuple[FormedCandidateEntry, ...]:
    if artifact.content.formation_authority.canonical_sha256 != _sha256(
        serialize_candidate_formation(candidate_formation)
    ):
        raise ValueError("Candidate Formation authority does not match final product")
    by_ordinal = {entry.ordinal: entry for entry in candidate_formation.formed}
    placements_by_position = {
        placement.position: placement
        for placement in artifact.content.construction_result.tracks
    }
    resolved: list[FormedCandidateEntry] = []
    for reference in artifact.content.placement_authorities:
        entry = by_ordinal.get(reference.formed_ordinal)
        if entry is None or entry.candidate.track_id != reference.track_id:
            raise ValueError("final placement authority reference cannot be resolved")
        placement = placements_by_position.get(reference.position)
        if placement is None or placement.candidate != entry.candidate:
            raise ValueError("final placement differs from formed candidate authority")
        FinalProductFinalizer._require_eligible_entry(entry)
        resolved.append(entry)
    if len(resolved) != len(artifact.content.construction_result.tracks):
        raise ValueError("final placement authority references are incomplete")
    return tuple(resolved)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
