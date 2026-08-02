from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.candidate_formation import (
    CANDIDATE_FIELD_ORDER,
    CandidateFormationArtifact,
    CandidateFormationPolicy,
    CandidateFormationRequest,
    CandidateFormer,
    ContextInputEvidence,
    EvidenceObservation,
    EvidenceState,
    FamiliarityEvidenceArtifact,
    FamiliarityEvidenceRecord,
    LocalTasteEvidenceArtifact,
    ObjectiveContextEvidenceArtifact,
    ObjectiveContextEvidenceRecord,
    PreferenceMappingEntry,
    PreferenceMappingRule,
    TasteEvidenceRecord,
    TrackFeatureEvidenceArtifact,
    TrackFeatureEvidenceRecord,
    UnitIntervalEvidence,
    WithholdingReasonCode,
    serialize_candidate_formation,
)
from playlist_narrative_engine.evaluation import PlaylistJourneyEvaluator
from playlist_narrative_engine.journey import (
    ActiveFocusRequest,
    JourneyPlanArtifact,
    JourneyPlanner,
)
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.sequencing import (
    CandidateSelector,
    SequentialPlaylistConstructor,
    TrackScorer,
)
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.track_evidence import (
    EvidenceProvenance,
    TrackEvidenceValidationArtifact,
    TrackEvidenceValidationSummary,
    ValidatedTrackEvidence,
)


OBJECTIVE = Objective(
    objective_id="coding-focus",
    statement="Support a focused coding session.",
)
SNAPSHOT_ID = "snapshot-001"


def observation(evidence_id: str, value: object) -> EvidenceObservation:
    return EvidenceObservation(
        evidence_id=evidence_id,
        source_type="manual_evidence",
        source_reference=f"source:{evidence_id}",
        payload_json=json.dumps(value, separators=(",", ":")),
    )


def measured(value: float, evidence_id: str) -> UnitIntervalEvidence:
    return UnitIntervalEvidence(
        state=EvidenceState.MEASURED,
        value=value,
        observations=(observation(evidence_id, value),),
    )


def validated_track(
    track_id: str = "track-a",
    artist_name: str = "Björk",
    record_id: str = "record-a",
) -> ValidatedTrackEvidence:
    return ValidatedTrackEvidence(
        ordinal=1,
        record_id=record_id,
        source_payload_json="{}",
        track_id=track_id,
        title=f"Title {track_id}",
        artist_name=artist_name,
        duration_seconds=240,
        provenance=EvidenceProvenance(
            source_type="manual_evidence",
            source_reference=f"source:{track_id}",
            rationale="Explicit track evidence.",
        ),
    )


def track_validation(
    tracks: tuple[ValidatedTrackEvidence, ...] | None = None,
) -> TrackEvidenceValidationArtifact:
    tracks = (validated_track(),) if tracks is None else tracks
    ordered = tuple(sorted(tracks, key=lambda item: item.record_id.encode("utf-8")))
    ordered = tuple(
        item.model_copy(update={"ordinal": index})
        for index, item in enumerate(ordered, start=1)
    )
    record_ids = tuple(item.record_id for item in ordered)
    return TrackEvidenceValidationArtifact(
        snapshot_id=SNAPSHOT_ID,
        objective_id=OBJECTIVE.objective_id,
        objective_statement=OBJECTIVE.statement,
        artist_inspection_scope=tuple(
            sorted({item.artist_name for item in ordered}, key=lambda item: item.encode("utf-8"))
        ),
        input_record_ids=record_ids,
        validated_records=ordered,
        rejected_records=(),
        summary=TrackEvidenceValidationSummary(
            input_record_count=len(ordered),
            validated_record_count=len(ordered),
            rejected_record_count=0,
        ),
    )


def accepted_objective() -> AcceptedObjectiveArtifact:
    return AcceptedObjectiveArtifact(
        artifact_id="accepted-001",
        request_id="safety-request",
        objective=OBJECTIVE,
        safety_policy_id="safety-policy",
        safety_policy_version="1.0",
        decision_explanation="The objective may proceed.",
    )


def journey() -> JourneyPlanArtifact:
    return JourneyPlanArtifact(
        journey_id="journey-001",
        objective=OBJECTIVE,
        objective_safety_artifact_id="accepted-001",
        plan=JourneyPlanner().plan_active_focus(ActiveFocusRequest()),
    )


def policy() -> CandidateFormationPolicy:
    return CandidateFormationPolicy(
        policy_id="candidate-policy",
        policy_version="1.0",
        preference_rule=PreferenceMappingRule(
            rule_name="categorical-preference-map",
            rule_version="1.0",
            mappings=(
                PreferenceMappingEntry(rating=Rating.MEH, value=0.4),
                PreferenceMappingEntry(rating=Rating.LOVE, value=1.0),
                PreferenceMappingEntry(rating=Rating.LIKE, value=0.8),
            ),
        ),
    )


def taste(
    rating: Rating = Rating.LOVE,
    *,
    artist_name: str = "Björk",
    state: EvidenceState = EvidenceState.MEASURED,
) -> LocalTasteEvidenceArtifact:
    observations = (
        (observation("taste", {"rating": rating.value}),)
        if state is EvidenceState.MEASURED
        else ()
    )
    return LocalTasteEvidenceArtifact(
        artifact_id="taste-001",
        profile_id="profile-001",
        records=(
            TasteEvidenceRecord(
                artist_name=artist_name,
                state=state,
                rating=rating if state is EvidenceState.MEASURED else None,
                observations=observations,
            ),
        ),
    )


def familiarity(
    evidence: UnitIntervalEvidence | None = None,
    *,
    artist_name: str = "Björk",
    track_id: str = "track-a",
) -> FamiliarityEvidenceArtifact:
    return FamiliarityEvidenceArtifact(
        artifact_id="familiarity-001",
        profile_id="profile-001",
        track_snapshot_id=SNAPSHOT_ID,
        records=(
            FamiliarityEvidenceRecord(
                track_id=track_id,
                artist_name=artist_name,
                familiarity=evidence or measured(0.7, f"familiarity-{track_id}"),
            ),
        ),
    )


def features(
    *,
    artist_name: str = "Björk",
    track_id: str = "track-a",
    energy: UnitIntervalEvidence | None = None,
) -> TrackFeatureEvidenceArtifact:
    return TrackFeatureEvidenceArtifact(
        artifact_id="features-001",
        track_snapshot_id=SNAPSHOT_ID,
        records=(
            TrackFeatureEvidenceRecord(
                track_id=track_id,
                artist_name=artist_name,
                energy=energy or measured(0.6, f"energy-{track_id}"),
                instrumentalness=measured(0.9, f"instrumentalness-{track_id}"),
                lyrical_distraction=measured(0.1, f"lyrics-{track_id}"),
                groove=measured(0.8, f"groove-{track_id}"),
            ),
        ),
    )


def context(
    *,
    artist_name: str = "Björk",
    track_id: str = "track-a",
    context_fit: UnitIntervalEvidence | None = None,
) -> ObjectiveContextEvidenceArtifact:
    return ObjectiveContextEvidenceArtifact(
        artifact_id="context-001",
        objective_id=OBJECTIVE.objective_id,
        objective_statement=OBJECTIVE.statement,
        journey_id="journey-001",
        context_id="focused-work",
        track_snapshot_id=SNAPSHOT_ID,
        records=(
            ObjectiveContextEvidenceRecord(
                track_id=track_id,
                artist_name=artist_name,
                context_fit=context_fit or measured(0.85, f"context-fit-{track_id}"),
                inputs=(
                    ContextInputEvidence(
                        input_name="listening_context",
                        state=EvidenceState.MEASURED,
                        resolved_payload_json='"Focused coding"',
                        observations=(
                            observation(f"context-input-{track_id}", "Focused coding"),
                        ),
                    ),
                ),
            ),
        ),
    )


def request(**overrides: object) -> CandidateFormationRequest:
    values = {
        "request_id": "formation-request-001",
        "accepted_objective": accepted_objective(),
        "journey_plan": journey(),
        "track_validation": track_validation(),
        "taste_evidence": taste(),
        "familiarity_evidence": familiarity(),
        "track_feature_evidence": features(),
        "objective_context_evidence": context(),
        "policy": policy(),
    }
    values.update(overrides)
    return CandidateFormationRequest(**values)


def test_complete_corresponding_evidence_forms_reproducible_candidate() -> None:
    artifact = CandidateFormer().form(request())

    assert artifact.summary.formed_count == 1
    assert artifact.summary.withheld_count == 0
    entry = artifact.formed[0]
    assert entry.candidate.preference == 1.0
    assert entry.candidate.energy == 0.6
    assert entry.candidate.context_fit == 0.85
    assert tuple(item.field for item in entry.field_evidence) == CANDIDATE_FIELD_ORDER
    preference_evidence = next(
        item for item in entry.field_evidence if item.field.value == "preference"
    )
    assert preference_evidence.rule_name == "categorical-preference-map"
    assert preference_evidence.rule_version == "1.0"
    assert artifact.hard_eligibility_evaluated is True
    assert artifact.scoring_performed is False
    assert artifact.recommendation_claims is False


def test_unknown_taste_is_withheld_without_neutral_preference() -> None:
    artifact = CandidateFormer().form(request(taste_evidence=taste(Rating.UNKNOWN)))

    assert artifact.formed == ()
    assert tuple(reason.code for reason in artifact.withheld[0].reasons) == (
        WithholdingReasonCode.DERIVATION_RULE_UNAPPROVED,
    )


def test_hard_exclusion_is_not_converted_to_scoring_penalty() -> None:
    artifact = CandidateFormer().form(request(taste_evidence=taste(Rating.FORBIDDEN)))

    assert artifact.formed == ()
    assert tuple(reason.code for reason in artifact.withheld[0].reasons) == (
        WithholdingReasonCode.HARD_ELIGIBILITY_EXCLUDED,
        WithholdingReasonCode.DERIVATION_RULE_UNAPPROVED,
    )
    assert artifact.scoring_performed is False


@pytest.mark.parametrize(
    ("state", "expected"),
    (
        (EvidenceState.UNAVAILABLE, WithholdingReasonCode.EVIDENCE_UNAVAILABLE),
        (EvidenceState.CONFLICTING, WithholdingReasonCode.EVIDENCE_CONFLICTING),
        (EvidenceState.UNSUPPORTED, WithholdingReasonCode.EVIDENCE_UNSUPPORTED),
        (
            EvidenceState.EXPLICITLY_INAPPLICABLE,
            WithholdingReasonCode.EVIDENCE_INAPPLICABLE,
        ),
    ),
)
def test_non_measured_evidence_states_remain_distinct(
    state: EvidenceState,
    expected: WithholdingReasonCode,
) -> None:
    observations = ()
    if state is EvidenceState.CONFLICTING:
        observations = (observation("a", 0.2), observation("b", 0.8))
    elif state in {EvidenceState.UNSUPPORTED, EvidenceState.EXPLICITLY_INAPPLICABLE}:
        observations = (observation("state", state.value),)
    evidence = UnitIntervalEvidence(state=state, observations=observations)

    artifact = CandidateFormer().form(
        request(familiarity_evidence=familiarity(evidence))
    )

    assert expected in tuple(reason.code for reason in artifact.withheld[0].reasons)
    assert all(item.candidate.familiarity != 0.5 for item in artifact.formed)


def test_missing_evidence_remains_explicitly_unavailable() -> None:
    missing = familiarity().model_copy(update={"records": ()})

    artifact = CandidateFormer().form(request(familiarity_evidence=missing))

    assert tuple(reason.code for reason in artifact.withheld[0].reasons) == (
        WithholdingReasonCode.EVIDENCE_UNAVAILABLE,
    )
    assert artifact.withheld[0].reasons[0].field_path == "$.familiarity"


def test_all_applicable_withholding_reasons_use_fixed_precedence() -> None:
    feature_record = TrackFeatureEvidenceRecord(
        track_id="track-a",
        artist_name="Björk",
        energy=UnitIntervalEvidence(
            state=EvidenceState.CONFLICTING,
            observations=(observation("energy-a", 0.2), observation("energy-b", 0.8)),
        ),
        instrumentalness=UnitIntervalEvidence(
            state=EvidenceState.UNSUPPORTED,
            observations=(observation("instrumentalness", "unsupported"),),
        ),
        lyrical_distraction=UnitIntervalEvidence(
            state=EvidenceState.EXPLICITLY_INAPPLICABLE,
            observations=(observation("lyrics", "inapplicable"),),
        ),
        groove=measured(0.8, "groove"),
    )
    feature_artifact = TrackFeatureEvidenceArtifact(
        artifact_id="features-001",
        track_snapshot_id=SNAPSHOT_ID,
        records=(feature_record,),
    )

    artifact = CandidateFormer().form(
        request(
            taste_evidence=taste(Rating.FORBIDDEN),
            familiarity_evidence=familiarity().model_copy(update={"records": ()}),
            track_feature_evidence=feature_artifact,
        )
    )

    assert tuple(reason.code for reason in artifact.withheld[0].reasons) == (
        WithholdingReasonCode.HARD_ELIGIBILITY_EXCLUDED,
        WithholdingReasonCode.EVIDENCE_CONFLICTING,
        WithholdingReasonCode.EVIDENCE_UNAVAILABLE,
        WithholdingReasonCode.EVIDENCE_UNSUPPORTED,
        WithholdingReasonCode.EVIDENCE_INAPPLICABLE,
        WithholdingReasonCode.DERIVATION_RULE_UNAPPROVED,
    )


def test_artist_identity_conflict_preserves_all_applicable_reasons() -> None:
    artifact = CandidateFormer().form(
        request(familiarity_evidence=familiarity(artist_name="björk"))
    )

    reasons = artifact.withheld[0].reasons
    assert tuple(reason.code for reason in reasons) == (
        WithholdingReasonCode.ARTIST_IDENTITY_CONFLICTING,
        WithholdingReasonCode.EVIDENCE_UNAVAILABLE,
    )
    assert tuple(reason.field_path for reason in reasons) == (
        "$.artist_name",
        "$.familiarity",
    )


def test_every_validated_track_appears_once_in_formed_or_withheld() -> None:
    first = validated_track()
    second = validated_track("track-b", "Kraftwerk", "record-b")
    validation = track_validation((second, first))
    artifact = CandidateFormer().form(request(track_validation=validation))

    assert artifact.input_track_ids == ("track-a", "track-b")
    assert tuple(item.candidate.track_id for item in artifact.formed) == ("track-a",)
    assert tuple(item.validated_track.track_id for item in artifact.withheld) == (
        "track-b",
    )
    assert artifact.summary.validated_track_count == 2


def test_request_fails_closed_on_objective_journey_snapshot_or_profile_mismatch() -> None:
    wrong_journey = journey().model_copy(
        update={"objective_safety_artifact_id": "other"}
    )
    with pytest.raises(ValidationError, match="accepted objective artifact"):
        request(journey_plan=wrong_journey)

    wrong_context = context().model_copy(update={"journey_id": "other"})
    with pytest.raises(ValidationError, match="correspond exactly"):
        request(objective_context_evidence=wrong_context)

    wrong_features = features().model_copy(update={"track_snapshot_id": "other"})
    with pytest.raises(ValidationError, match="validated snapshot"):
        request(track_feature_evidence=wrong_features)

    wrong_familiarity = familiarity().model_copy(update={"profile_id": "other"})
    with pytest.raises(ValidationError, match="one exact profile"):
        request(familiarity_evidence=wrong_familiarity)


def test_unvalidated_track_evidence_is_request_level_failure() -> None:
    with pytest.raises(ValidationError, match="unvalidated track identity"):
        request(track_feature_evidence=features(track_id="other"))


@pytest.mark.parametrize("near_match", ("Track-A", "track-a!", "track‐a"))
def test_track_identity_near_matches_are_not_repaired(near_match: str) -> None:
    with pytest.raises(ValidationError, match="unvalidated track identity"):
        request(track_feature_evidence=features(track_id=near_match))


def test_track_identity_does_not_apply_unicode_normalization() -> None:
    composed = "träck-a"
    decomposed = "tra\u0308ck-a"
    validation = track_validation((validated_track(composed),))

    with pytest.raises(ValidationError, match="unvalidated track identity"):
        request(
            track_validation=validation,
            familiarity_evidence=familiarity(track_id=composed),
            track_feature_evidence=features(track_id=decomposed),
            objective_context_evidence=context(track_id=composed),
        )


def test_objective_identity_must_match_exactly_without_normalization() -> None:
    variants = (
        "support a focused coding session.",
        "Support a focused coding session!",
        "Support a focused co\u0301ding session.",
    )
    for statement in variants:
        mismatched = context().model_copy(update={"objective_statement": statement})
        with pytest.raises(ValidationError, match="correspond exactly"):
            request(objective_context_evidence=mismatched)


def test_policy_requires_explicit_mapping_and_cannot_map_unknown() -> None:
    with pytest.raises(ValidationError, match="exactly Love, Like, and Meh"):
        PreferenceMappingRule(
            rule_name="bad-map",
            rule_version="1.0",
            mappings=(
                PreferenceMappingEntry(rating=Rating.LOVE, value=1.0),
                PreferenceMappingEntry(rating=Rating.UNKNOWN, value=0.5),
            ),
        )


def test_reordered_source_collections_produce_equal_artifacts_and_bytes() -> None:
    caller_mappings = [
        PreferenceMappingEntry(rating=Rating.MEH, value=0.4),
        PreferenceMappingEntry(rating=Rating.LOVE, value=1.0),
        PreferenceMappingEntry(rating=Rating.LIKE, value=0.8),
    ]
    reversed_rule = PreferenceMappingRule(
        rule_name="categorical-preference-map",
        rule_version="1.0",
        mappings=caller_mappings,
    )
    reordered_policy = CandidateFormationPolicy(
        policy_id="candidate-policy",
        policy_version="1.0",
        preference_rule=reversed_rule,
    )
    first = CandidateFormer().form(request())
    second = CandidateFormer().form(request(policy=reordered_policy))

    assert first == second
    assert serialize_candidate_formation(first) == serialize_candidate_formation(second)
    assert [entry.rating for entry in caller_mappings] == [
        Rating.MEH,
        Rating.LOVE,
        Rating.LIKE,
    ]


def test_artifact_schema_rejects_partition_tampering() -> None:
    artifact = CandidateFormer().form(request())
    tampered = artifact.model_dump(mode="json")
    tampered["formed"] = []

    with pytest.raises(ValidationError, match="exactly once"):
        CandidateFormationArtifact.model_validate(tampered)


def test_artifact_schema_rejects_candidate_value_without_matching_evidence() -> None:
    artifact = CandidateFormer().form(request())
    tampered = artifact.model_dump(mode="json")
    tampered["formed"][0]["candidate"]["energy"] = 0.2

    with pytest.raises(ValidationError, match="must equal its recorded evidence"):
        CandidateFormationArtifact.model_validate(tampered)


def test_artifact_schema_rejects_field_provenance_from_wrong_source() -> None:
    artifact = CandidateFormer().form(request())
    tampered = artifact.model_dump(mode="json")
    tampered["formed"][0]["field_evidence"][4]["source_artifact_id"] = "other"

    with pytest.raises(ValidationError, match="must use its owned source"):
        CandidateFormationArtifact.model_validate(tampered)


def test_empty_validated_snapshot_produces_complete_empty_partition() -> None:
    empty_validation = track_validation(())
    artifact = CandidateFormer().form(
        request(
            track_validation=empty_validation,
            familiarity_evidence=familiarity().model_copy(update={"records": ()}),
            track_feature_evidence=features().model_copy(update={"records": ()}),
            objective_context_evidence=context().model_copy(update={"records": ()}),
        )
    )

    assert artifact.input_track_ids == ()
    assert artifact.formed == ()
    assert artifact.withheld == ()
    assert artifact.summary.validated_track_count == 0


def test_formation_does_not_call_scoring_selection_construction_or_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("Candidate Formation called a downstream layer")

    monkeypatch.setattr(TrackScorer, "score", unexpected_call)
    monkeypatch.setattr(CandidateSelector, "select", unexpected_call)
    monkeypatch.setattr(SequentialPlaylistConstructor, "construct", unexpected_call)
    monkeypatch.setattr(PlaylistJourneyEvaluator, "evaluate", unexpected_call)

    artifact = CandidateFormer().form(request())

    assert artifact.summary.formed_count == 1


def test_cf2_modules_do_not_import_provider_or_downstream_behavior() -> None:
    package_root = (
        Path(__file__).parents[1]
        / "src"
        / "playlist_narrative_engine"
        / "candidate_formation"
    )
    forbidden_prefixes = (
        "playlist_narrative_engine.providers",
        "playlist_narrative_engine.sequencing.scorer",
        "playlist_narrative_engine.sequencing.selector",
        "playlist_narrative_engine.sequencing.constructor",
        "playlist_narrative_engine.evaluation",
        "playlist_narrative_engine.refinement",
    )

    imported_modules: set[str] = set()
    for filename in ("formation_schemas.py", "former.py"):
        tree = ast.parse((package_root / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
            elif isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)

    assert not any(
        module.startswith(prefix)
        for module in imported_modules
        for prefix in forbidden_prefixes
    )
