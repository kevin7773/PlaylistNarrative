from __future__ import annotations

import json

from test_candidate_formation import observation, request
from playlist_narrative_engine.candidate_formation import (
    BooleanEvidence,
    CandidateConstraintField,
    CandidateEligibilityState,
    CandidateFormer,
    CandidateHardConstraint,
    CandidateIdentityMetadataArtifact,
    CandidateIdentityMetadataRecord,
    EvidenceState,
    ExactStringEvidence,
    WithholdingReasonCode,
    derive_formed_candidate_pool,
)
from playlist_narrative_engine.journey.schemas import JourneyContext
from playlist_narrative_engine.sequencing import (
    CandidateSelector,
    ConstructionState,
    SequentialPlaylistConstructor,
    TrackRole,
)
from cf3_test_helpers import journey_artifact


def string_evidence(value: str | None, key: str) -> ExactStringEvidence:
    return ExactStringEvidence(
        state=EvidenceState.MEASURED if value is not None else EvidenceState.UNAVAILABLE,
        value=value,
        observations=(observation(key, value),) if value is not None else (),
    )


def metadata(explicit: bool | None, *, catalog: str = "catalog:123", version: str = "release:explicit") -> CandidateIdentityMetadataArtifact:
    return CandidateIdentityMetadataArtifact(
        artifact_id="identity-metadata-001",
        track_snapshot_id="snapshot-001",
        records=(CandidateIdentityMetadataRecord(
            track_id="track-a",
            source_catalog_identity=string_evidence(catalog, "catalog"),
            release_version_identity=string_evidence(version, "version"),
            displayed_explicit=BooleanEvidence(
                state=EvidenceState.MEASURED if explicit is not None else EvidenceState.UNAVAILABLE,
                value=explicit,
                observations=(observation("explicit", explicit),) if explicit is not None else (),
            ),
        ),),
    )


NON_EXPLICIT = CandidateHardConstraint(
    constraint_key="no-explicit",
    field=CandidateConstraintField.DISPLAYED_EXPLICIT,
    expected_json="false",
)


def constrained_request(*, metadata_value, constraints=(NON_EXPLICIT,)):
    return request(
        identity_metadata=metadata_value,
        hard_constraints=constraints,
        hard_constraint_declaration_id="test-constraints",
        hard_constraint_declaration_version="1.0",
        hard_constraint_declaration_source_type="test_declaration",
        hard_constraint_declaration_source_reference="fixture:test-constraints",
    )


def test_known_compliant_candidate_is_retained_with_exact_identity_and_trace() -> None:
    artifact = CandidateFormer().form(constrained_request(metadata_value=metadata(False)))

    assert artifact.summary.formed_count == 1
    entry = artifact.formed[0]
    assert entry.identity.source_catalog_identity == "catalog:123"
    assert entry.identity.release_version_identity == "release:explicit"
    assert entry.identity.displayed_explicit is False
    assert entry.identity.source_catalog_evidence_ids == ("catalog",)
    assert entry.identity.release_version_evidence_ids == ("version",)
    assert entry.identity.displayed_explicit_evidence_ids == ("explicit",)
    assert entry.constraint_eligibility[0].state is CandidateEligibilityState.ELIGIBLE
    assert entry.constraint_eligibility[0].source_evidence_ids == ("explicit",)
    assert entry.mechanism_trace.events[-1] == "RETAINED_FOR_RANKING"
    pool = derive_formed_candidate_pool(artifact)
    assert pool.formed_entries[0].identity == entry.identity


def test_known_explicit_candidate_is_withheld_before_ranking() -> None:
    artifact = CandidateFormer().form(constrained_request(metadata_value=metadata(True)))

    assert artifact.formed == ()
    withheld = artifact.withheld[0]
    assert withheld.constraint_eligibility[0].state is CandidateEligibilityState.INELIGIBLE
    assert WithholdingReasonCode.HARD_CONSTRAINT_INELIGIBLE in {item.code for item in withheld.reasons}
    assert derive_formed_candidate_pool(artifact).candidates == ()


def test_unknown_explicit_state_is_not_silently_compliant() -> None:
    artifact = CandidateFormer().form(constrained_request(metadata_value=metadata(None)))

    result = artifact.withheld[0].constraint_eligibility[0]
    assert result.state is CandidateEligibilityState.UNKNOWN
    assert result.observed_json is None
    assert WithholdingReasonCode.HARD_CONSTRAINT_UNKNOWN in {item.code for item in artifact.withheld[0].reasons}


def test_exact_identity_is_case_sensitive_and_ambiguous_family_is_not_collapsed() -> None:
    target = CandidateHardConstraint(
        constraint_key="exact-catalog-object",
        field=CandidateConstraintField.SOURCE_CATALOG_IDENTITY,
        expected_json=json.dumps("catalog:ABC"),
    )
    artifact = CandidateFormer().form(constrained_request(
        metadata_value=metadata(False, catalog="catalog:abc"), constraints=(target,)
    ))

    assert artifact.formed == ()
    assert artifact.withheld[0].constraint_eligibility[0].state is CandidateEligibilityState.INELIGIBLE
    assert artifact.withheld[0].identity.source_catalog_identity == "catalog:abc"


def test_no_compliant_candidate_is_explicitly_unsatisfied_not_rankable() -> None:
    artifact = CandidateFormer().form(constrained_request(metadata_value=metadata(True)))
    pool = derive_formed_candidate_pool(artifact)

    assert artifact.summary.formed_count == 0
    assert artifact.summary.withheld_count == 1
    assert pool.candidates == ()


def test_legacy_request_without_constraints_preserves_existing_meaning() -> None:
    artifact = CandidateFormer().form(request())
    assert artifact.summary.formed_count == 1
    assert artifact.formed[0].constraint_eligibility == ()
    assert artifact.formed[0].identity.displayed_explicit is None


def test_ranking_preserves_identity_and_constraint_provenance_without_rescoring_it() -> None:
    pool = derive_formed_candidate_pool(CandidateFormer().form(
        constrained_request(metadata_value=metadata(False))
    ))
    ranked = CandidateSelector().select(
        context=JourneyContext.ACTIVE_FOCUS,
        previous_track=None,
        phase=journey_artifact().plan.phases[0],
        role=TrackRole.OPENING_ANCHOR,
        target_discovery_ratio=0.2,
        formed_pool=pool,
        remaining_track_ids=("track-a",),
    ).ranked_candidates[0]
    assert ranked.identity.source_catalog_identity == "catalog:123"
    assert ranked.constraint_eligibility[0].source_evidence_ids == ("explicit",)


def test_selected_candidate_exposes_post_selection_validation_and_no_refinement_claim() -> None:
    formation_request = constrained_request(metadata_value=metadata(False))
    pool = derive_formed_candidate_pool(CandidateFormer().form(formation_request))
    result = SequentialPlaylistConstructor().construct(
        journey_plan=formation_request.journey_plan,
        formed_pool=pool,
        state=ConstructionState(),
        requested_track_count=1,
    )

    assert result.tracks[0].post_selection_validation == "FORMED_HARD_ELIGIBILITY_CONFIRMED"
    assert result.tracks[0].refinement_action == "NONE"
