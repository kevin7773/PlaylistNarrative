from __future__ import annotations

import json

from journey_authority_helpers import journey_authority

from playlist_narrative_engine.candidate_formation import (
    CANDIDATE_FIELD_ORDER,
    CandidateFieldEvidence,
    CandidateFieldName,
    CandidateFormationArtifact,
    CandidateFormationSummary,
    FormationBasis,
    FormedCandidateEntry,
    FormedCandidatePoolView,
    derive_formed_candidate_pool,
)
from playlist_narrative_engine.journey import JourneyPlan, JourneyPlanArtifact
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.sequencing.schemas import TrackCandidate


OBJECTIVE = Objective(
    objective_id="objective-test",
    statement="Support a deterministic test journey.",
)


def journey_artifact(plan: JourneyPlan | None = None) -> JourneyPlanArtifact:
    artifact = journey_authority(OBJECTIVE)[2]
    if plan is not None and plan != artifact.plan:
        raise ValueError("test plan must equal authenticated planning evidence")
    return artifact


def formed_pool(
    candidates: tuple[TrackCandidate, ...] | list[TrackCandidate],
) -> FormedCandidatePoolView:
    return derive_formed_candidate_pool(formation_artifact(candidates))


def formation_artifact(
    candidates: tuple[TrackCandidate, ...] | list[TrackCandidate],
) -> CandidateFormationArtifact:
    ordered = tuple(
        sorted(tuple(candidates), key=lambda item: item.track_id.encode("utf-8"))
    )
    entries = tuple(
        _formed_entry(candidate, ordinal)
        for ordinal, candidate in enumerate(ordered, start=1)
    )
    journey = journey_artifact()
    return CandidateFormationArtifact(
        request_id="formation-test",
        accepted_objective_artifact_id=journey.objective_safety_artifact_id,
        objective_id=OBJECTIVE.objective_id,
        objective_statement=OBJECTIVE.statement,
        journey_id=journey.journey_id,
        snapshot_id="snapshot-test",
        profile_id="profile-test",
        taste_evidence_artifact_id="taste-test",
        familiarity_evidence_artifact_id="familiarity-test",
        track_feature_evidence_artifact_id="features-test",
        objective_context_evidence_artifact_id="context-test",
        policy_id="formation-policy-test",
        policy_version="1.0",
        preference_rule_name="preference-rule-test",
        preference_rule_version="1.0",
        input_track_ids=tuple(candidate.track_id for candidate in ordered),
        formed=entries,
        withheld=(),
        summary=CandidateFormationSummary(
            validated_track_count=len(entries),
            formed_count=len(entries),
            withheld_count=0,
        ),
    )


def _formed_entry(candidate: TrackCandidate, ordinal: int) -> FormedCandidateEntry:
    evidence = {
        field: _field_evidence(candidate, field) for field in CANDIDATE_FIELD_ORDER
    }
    return FormedCandidateEntry(
        ordinal=ordinal,
        candidate=candidate,
        field_evidence=tuple(evidence[field] for field in CANDIDATE_FIELD_ORDER),
    )


def _field_evidence(
    candidate: TrackCandidate,
    field: CandidateFieldName,
) -> CandidateFieldEvidence:
    value = getattr(candidate, field.value)
    source_kind, source_id = {
        CandidateFieldName.TRACK_ID: ("track_evidence_validation", "snapshot-test"),
        CandidateFieldName.TITLE: ("track_evidence_validation", "snapshot-test"),
        CandidateFieldName.ARTIST_NAME: ("track_evidence_validation", "snapshot-test"),
        CandidateFieldName.DURATION_SECONDS: (
            "track_evidence_validation",
            "snapshot-test",
        ),
        CandidateFieldName.PREFERENCE: ("local_taste_evidence", "taste-test"),
        CandidateFieldName.FAMILIARITY: (
            "familiarity_evidence",
            "familiarity-test",
        ),
        CandidateFieldName.ENERGY: ("track_feature_evidence", "features-test"),
        CandidateFieldName.INSTRUMENTALNESS: (
            "track_feature_evidence",
            "features-test",
        ),
        CandidateFieldName.LYRICAL_DISTRACTION: (
            "track_feature_evidence",
            "features-test",
        ),
        CandidateFieldName.GROOVE: ("track_feature_evidence", "features-test"),
        CandidateFieldName.CONTEXT_FIT: (
            "objective_context_evidence",
            "context-test",
        ),
    }[field]
    derived = field is CandidateFieldName.PREFERENCE
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return CandidateFieldEvidence(
        field=field,
        source_artifact_kind=source_kind,
        source_artifact_id=source_id,
        source_record_identity=(
            candidate.artist_name if derived else candidate.track_id
        ),
        source_evidence_ids=(f"evidence:{candidate.track_id}:{field.value}",),
        basis=(FormationBasis.VERSIONED_DERIVATION if derived else FormationBasis.DIRECT_EVIDENCE),
        rule_name="preference-rule-test" if derived else None,
        rule_version="1.0" if derived else None,
        serialized_inputs_json=serialized,
        result_json=serialized,
        explanation="Deterministic authenticated test evidence.",
    )
