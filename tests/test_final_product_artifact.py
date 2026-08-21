from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from cf3_test_helpers import formation_artifact, journey_artifact

from playlist_narrative_engine.candidate_formation import (
    CandidateEligibilityState,
    CandidateFormationArtifact,
    derive_formed_candidate_pool,
)
from playlist_narrative_engine.evaluation import PlaylistJourneyEvaluator
from playlist_narrative_engine.product_artifact import (
    FINAL_PRODUCT_SCHEMA_VERSION,
    FinalProductFinalizer,
    RefinementDisposition,
    final_product_content_sha256,
    resolve_final_placement_authorities,
    serialize_final_product_artifact,
    serialize_final_product_content,
    verify_final_product_artifact,
    verify_final_product_digest,
)
from playlist_narrative_engine.research_store.schemas import (
    PersistedPlaylistArtifactInput,
)
from playlist_narrative_engine.sequencing import (
    ConstructionPolicy,
    ConstructionState,
    ConstructionStatus,
    SequentialPlaylistConstructor,
    TrackCandidate,
)


def candidate(track_id: str, *, preference: float = 0.8) -> TrackCandidate:
    return TrackCandidate(
        track_id=track_id,
        title=f"Title {track_id}",
        artist_name=f"Artist {track_id}",
        duration_seconds=180,
        energy=0.6,
        familiarity=0.5,
        preference=preference,
        context_fit=0.7,
        instrumentalness=0.2,
        lyrical_distraction=0.3,
        groove=0.8,
    )


def bundle(
    *,
    available: int = 2,
    requested: int = 2,
    artifact_id: str = "final-001",
    policy: ConstructionPolicy | None = None,
    journey_id: str = "journey-test",
    formation_request_id: str = "formation-test",
):
    candidates = tuple(
        candidate(f"track-{index}", preference=0.9 - index * 0.05)
        for index in range(available)
    )
    journey = journey_artifact().model_copy(update={"journey_id": journey_id})
    formation = formation_artifact(candidates).model_copy(
        update={
            "journey_id": journey_id,
            "request_id": formation_request_id,
        }
    )
    pool = derive_formed_candidate_pool(formation)
    selected_policy = policy or ConstructionPolicy()
    result = SequentialPlaylistConstructor(policy=selected_policy).construct(
        journey_plan=journey,
        formed_pool=pool,
        state=ConstructionState(),
        requested_track_count=requested,
    )
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey,
        construction_policy=selected_policy,
    )
    artifact = FinalProductFinalizer().finalize(
        artifact_id=artifact_id,
        journey_plan=journey,
        candidate_formation=formation,
        formed_pool=pool,
        construction_policy=selected_policy,
        construction_result=result,
        evaluation_report=report,
    )
    return journey, formation, pool, selected_policy, result, report, artifact


@pytest.mark.parametrize(
    ("available", "requested", "status", "track_count"),
    (
        (2, 2, ConstructionStatus.COMPLETE, 2),
        (1, 2, ConstructionStatus.PARTIAL, 1),
        (0, 2, ConstructionStatus.INFEASIBLE, 0),
    ),
)
def test_complete_partial_and_infeasible_finalize_without_reinterpretation(
    available: int,
    requested: int,
    status: ConstructionStatus,
    track_count: int,
) -> None:
    *_, result, report, artifact = bundle(
        available=available,
        requested=requested,
    )

    assert artifact.content.schema_version == FINAL_PRODUCT_SCHEMA_VERSION
    assert artifact.content.final_status is status
    assert artifact.content.refinement_disposition is RefinementDisposition.NOT_PERFORMED
    assert len(artifact.content.construction_result.tracks) == track_count
    assert artifact.content.construction_result == result
    assert artifact.content.evaluation_report == report
    assert artifact.content.construction_result.issues == result.issues
    assert verify_final_product_digest(artifact)


def test_constituent_authorities_verify_in_a_fresh_call() -> None:
    journey, formation, pool, policy, _, _, artifact = bundle()

    assert verify_final_product_artifact(
        artifact,
        journey_plan=journey,
        candidate_formation=formation,
        formed_pool=pool,
        construction_policy=policy,
    )
    assert not verify_final_product_artifact(
        artifact,
        journey_plan=journey.model_copy(update={"journey_id": "substituted"}),
        candidate_formation=formation,
        formed_pool=pool,
        construction_policy=policy,
    )
    assert not verify_final_product_artifact(
        artifact,
        journey_plan=journey,
        candidate_formation=formation,
        formed_pool=pool,
        construction_policy=ConstructionPolicy(max_tracks_per_artist=1),
    )


def test_unsupported_versions_and_refinement_dispositions_are_rejected() -> None:
    journey, formation, pool, policy, result, report, _ = bundle()

    with pytest.raises(ValueError, match="construction-result schema"):
        FinalProductFinalizer().finalize(
            artifact_id="unsupported-construction",
            journey_plan=journey,
            candidate_formation=formation,
            formed_pool=pool,
            construction_policy=policy,
            construction_result=replace(result, schema_version="unsupported"),
            evaluation_report=report,
        )
    with pytest.raises(ValueError, match="evaluation-report schema"):
        FinalProductFinalizer().finalize(
            artifact_id="unsupported-evaluation",
            journey_plan=journey,
            candidate_formation=formation,
            formed_pool=pool,
            construction_policy=policy,
            construction_result=result,
            evaluation_report=report.model_construct(
                **{**report.model_dump(), "schema_version": "unsupported"}
            ),
        )
    with pytest.raises(TypeError, match="refinement_disposition"):
        FinalProductFinalizer().finalize(
            artifact_id="unsupported-refinement",
            journey_plan=journey,
            candidate_formation=formation,
            formed_pool=pool,
            construction_policy=policy,
            construction_result=result,
            evaluation_report=report,
            refinement_disposition="PERFORMED",  # type: ignore[arg-type]
        )


def test_coherent_constituent_changes_change_the_final_digest() -> None:
    *_, baseline = bundle()
    *_, changed_journey = bundle(journey_id="journey-changed")
    *_, changed_formation = bundle(formation_request_id="formation-changed")
    *_, changed_policy = bundle(
        policy=ConstructionPolicy(max_tracks_per_artist=1)
    )

    assert changed_journey.canonical_sha256 != baseline.canonical_sha256
    assert changed_formation.canonical_sha256 != baseline.canonical_sha256
    assert changed_policy.canonical_sha256 != baseline.canonical_sha256


def test_formation_and_foreign_pool_substitution_are_rejected() -> None:
    journey, formation, pool, policy, result, report, artifact = bundle()
    foreign = formation_artifact((candidate("foreign"),)).model_copy(
        update={"journey_id": journey.journey_id}
    )
    foreign_pool = derive_formed_candidate_pool(foreign)

    with pytest.raises(ValueError, match="exact authenticated formation projection"):
        FinalProductFinalizer().finalize(
            artifact_id="bad",
            journey_plan=journey,
            candidate_formation=formation,
            formed_pool=foreign_pool,
            construction_policy=policy,
            construction_result=result,
            evaluation_report=report,
        )
    assert not verify_final_product_artifact(
        artifact,
        journey_plan=journey,
        candidate_formation=foreign,
        formed_pool=foreign_pool,
        construction_policy=policy,
    )


def test_construction_or_evaluation_from_another_run_is_rejected() -> None:
    journey, formation, pool, policy, result, report, _ = bundle()
    *_, other_result, other_report, _ = bundle(available=1, requested=2)

    with pytest.raises(ValueError, match="construction binding"):
        FinalProductFinalizer().finalize(
            artifact_id="bad-construction",
            journey_plan=journey,
            candidate_formation=formation,
            formed_pool=pool,
            construction_policy=policy,
            construction_result=replace(
                result,
                input_binding=replace(
                    result.input_binding,
                    construction_policy_sha256="0" * 64,
                ),
            ),
            evaluation_report=report,
        )
    with pytest.raises(ValueError, match="evaluation binding"):
        FinalProductFinalizer().finalize(
            artifact_id="bad-evaluation",
            journey_plan=journey,
            candidate_formation=formation,
            formed_pool=pool,
            construction_policy=policy,
            construction_result=result,
            evaluation_report=other_report,
        )
    assert other_result != result


def test_placements_resolve_to_exact_formed_entries_and_recover_provenance() -> None:
    _, formation, _, _, result, _, artifact = bundle()
    resolved = resolve_final_placement_authorities(artifact, formation)

    assert tuple(item.candidate for item in resolved) == tuple(
        item.candidate for item in result.tracks
    )
    assert tuple(item.ordinal for item in resolved) == tuple(
        reference.formed_ordinal
        for reference in artifact.content.placement_authorities
    )
    assert all(item.field_evidence for item in resolved)
    assert tuple(reference.position for reference in artifact.content.placement_authorities) == (
        1,
        2,
    )

    changed_reference = replace(
        artifact.content.placement_authorities[0],
        position=2,
    )
    tampered = replace(
        artifact,
        content=replace(
            artifact.content,
            placement_authorities=(changed_reference,)
            + artifact.content.placement_authorities[1:],
        ),
    )
    with pytest.raises(ValueError, match="differs from formed candidate authority"):
        resolve_final_placement_authorities(tampered, formation)


def test_altered_or_foreign_placement_candidate_is_rejected() -> None:
    journey, formation, pool, policy, result, _, _ = bundle()
    for replacement_candidate, message in (
        (
            result.tracks[0].candidate.model_copy(update={"title": "Altered"}),
            "differs from formed authority",
        ),
        (candidate("foreign"), "absent from authenticated formed pool"),
    ):
        changed_track = replace(
            result.tracks[0],
            candidate=replacement_candidate,
        )
        changed_result = replace(
            result,
            tracks=(changed_track,) + result.tracks[1:],
        )
        changed_report = PlaylistJourneyEvaluator().evaluate(
            construction_result=changed_result,
            journey_plan=journey,
            construction_policy=policy,
        )
        with pytest.raises(ValueError, match=message):
            FinalProductFinalizer().finalize(
                artifact_id="bad-placement",
                journey_plan=journey,
                candidate_formation=formation,
                formed_pool=pool,
                construction_policy=policy,
                construction_result=changed_result,
                evaluation_report=changed_report,
            )


@pytest.mark.parametrize(
    "state",
    (CandidateEligibilityState.UNKNOWN, CandidateEligibilityState.INELIGIBLE),
)
def test_unknown_or_ineligible_formed_candidate_is_rejected(
    state: CandidateEligibilityState,
) -> None:
    from test_candidate_constraint_eligibility import constrained_request, metadata
    from playlist_narrative_engine.candidate_formation import CandidateFormer

    request = constrained_request(metadata_value=metadata(False))
    valid = CandidateFormer().form(request)
    result_item = valid.formed[0].constraint_eligibility[0].model_copy(
        update={"state": state}
    )
    malformed_entry = valid.formed[0].model_copy(
        update={"constraint_eligibility": (result_item,)}
    )
    malformed = valid.model_copy(update={"formed": (malformed_entry,)})

    with pytest.raises(ValueError):
        derive_formed_candidate_pool(malformed)


def test_order_issues_and_all_governed_constituents_participate_in_digest() -> None:
    _, _, _, _, result, report, artifact = bundle()
    canonical = serialize_final_product_artifact(artifact)
    digest = artifact.canonical_sha256

    assert canonical == serialize_final_product_artifact(artifact)
    assert digest == final_product_content_sha256(artifact.content)
    assert artifact.content.construction_result.issues == result.issues

    changed_order = replace(
        artifact.content,
        placement_authorities=tuple(
            reversed(artifact.content.placement_authorities)
        ),
    )
    changed_evaluation = replace(
        artifact.content,
        evaluation_report=report.model_copy(
            update={"issues": tuple(reversed(report.issues))}
        ),
    )
    changed_refinement = replace(
        artifact.content,
        refinement_disposition="TAMPERED",
    )
    assert final_product_content_sha256(changed_order) != digest
    assert final_product_content_sha256(changed_evaluation) != digest
    assert final_product_content_sha256(changed_refinement) != digest


def test_digest_tampering_and_immutability_are_enforced() -> None:
    *_, artifact = bundle()
    tampered = replace(artifact, canonical_sha256="0" * 64)

    assert not verify_final_product_digest(tampered)
    with pytest.raises(FrozenInstanceError):
        artifact.canonical_sha256 = "0" * 64


def test_research_artifact_cannot_satisfy_product_finalizer_api() -> None:
    journey, _, pool, policy, result, report, _ = bundle()
    research_artifact = PersistedPlaylistArtifactInput.model_construct()

    with pytest.raises(TypeError, match="candidate_formation"):
        FinalProductFinalizer().finalize(
            artifact_id="wrong-domain",
            journey_plan=journey,
            candidate_formation=research_artifact,
            formed_pool=pool,
            construction_policy=policy,
            construction_result=result,
            evaluation_report=report,
        )


def test_product_package_has_no_research_or_workbench_coupling() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/playlist_narrative_engine/product_artifact").glob("*.py")
    )
    assert "research_store" not in source
    assert "maestro_workbench" not in source
    assert "PersistedPlaylistArtifact" not in source
