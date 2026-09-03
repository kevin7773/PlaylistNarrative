from __future__ import annotations

import math

import pytest

import playlist_narrative_engine.candidate_readiness.vocabulary as vocabulary_module
from playlist_narrative_engine.candidate_formation import EvidenceState
from playlist_narrative_engine.candidate_readiness import (
    GuardedActiveFocusCandidateFormationBridge,
    ReadinessField,
    ReadinessLevel,
    project_level,
)
from playlist_narrative_engine.taste.ratings import Rating
from test_candidate_readiness_capture import build_readiness


def test_exact_projection_preserves_categories_and_missing_does_not_default(monkeypatch, session) -> None:
    *_, verifier, _, _, _, _, _, occurrence = build_readiness(monkeypatch, session)
    record = occurrence.track_feature_evidence.records[0]
    assert record.energy.value == 0.5
    assert record.instrumentalness.value == 0.25
    assert record.lyrical_distraction.value == 0.25
    assert record.groove.value == 0.75
    assert occurrence.familiarity_evidence.records[0].familiarity.value == 1.0
    assert occurrence.objective_context_evidence.records[0].context_fit.value == 1.0
    assert '"category":"LEVEL_2"' in record.energy.observations[0].payload_json
    assert verifier.verify(occurrence)


def test_partial_capture_yields_unavailable_and_candidate_withholding(monkeypatch, session) -> None:
    from playlist_narrative_engine.candidate_readiness import ActiveFocusCandidateReadinessDeclaration
    setup = build_readiness(monkeypatch, session, declarations=(
        {
            "track_id": "itunes-windows-library:9C9E2747D29AB9A8/track:60F3F28BD78BD511",
            "familiarity": "LEVEL_4",
        },
    ))
    verifier, occurrence = setup[2], setup[-1]
    features = occurrence.track_feature_evidence.records[0]
    assert all(getattr(features, name).state is EvidenceState.UNAVAILABLE for name in ("energy", "instrumentalness", "lyrical_distraction", "groove"))
    verified = verifier.verify_authority(occurrence)
    formation = GuardedActiveFocusCandidateFormationBridge(
        verifier,
        accepted_objective=occurrence.accepted_objective,
        journey_plan=occurrence.journey_plan,
    ).form(verified_readiness=verified, request_id="partial-readiness")
    assert formation.summary.formed_count == 0
    assert formation.summary.withheld_count == 59


def test_tampered_numeric_projection_and_context_scope_fail(monkeypatch, session) -> None:
    *_, verifier, _, _, _, _, _, occurrence = build_readiness(monkeypatch, session)
    feature = occurrence.track_feature_evidence.records[0]
    bad_energy = feature.energy.model_copy(update={"value": 0.75})
    bad_feature = feature.model_copy(update={"energy": bad_energy})
    bad_features = occurrence.track_feature_evidence.model_copy(update={"records": (bad_feature,)})
    assert not verifier.verify(occurrence.model_copy(update={"track_feature_evidence": bad_features}))
    assert not verifier.verify(occurrence.model_copy(update={"journey_id": "other-journey"}))


@pytest.mark.parametrize(
    "rating,state,formed_count",
    [
        (Rating.LOVE, EvidenceState.MEASURED, 1), (Rating.LIKE, EvidenceState.MEASURED, 1),
        (Rating.MEH, EvidenceState.MEASURED, 1), (Rating.NO_THANKS, EvidenceState.MEASURED, 0),
        (Rating.PENCIL, EvidenceState.MEASURED, 0), (Rating.FORBIDDEN, EvidenceState.MEASURED, 0),
        (Rating.UNKNOWN, EvidenceState.MEASURED, 0), (None, EvidenceState.UNAVAILABLE, 0),
    ],
)
def test_every_rating_state_is_projected_explicitly(monkeypatch, session, rating, state, formed_count) -> None:
    setup = build_readiness(monkeypatch, session, rating=rating)
    verifier, occurrence = setup[2], setup[-1]
    record = occurrence.local_taste_evidence.records[0]
    assert record.state is state
    assert record.rating is rating
    formation = GuardedActiveFocusCandidateFormationBridge(
        verifier,
        accepted_objective=occurrence.accepted_objective,
        journey_plan=occurrence.journey_plan,
    ).form(
        verified_readiness=verifier.verify_authority(occurrence),
        request_id="rating-policy-projection",
    )
    assert formation.summary.formed_count == formed_count


def test_near_match_artist_does_not_normalize_into_correspondence(monkeypatch, session) -> None:
    occurrence = build_readiness(
        monkeypatch, session, rating=None,
        extra_ratings=(("the Sisters Of Mercy", Rating.LOVE), ("The Sisters Of MercY", Rating.LIKE)),
    )[-1]
    assert occurrence.local_taste_evidence.records[0].state is EvidenceState.UNAVAILABLE


def test_projection_has_no_mutable_secondary_authority(monkeypatch) -> None:
    monkeypatch.setattr(
        vocabulary_module,
        "_PROJECTIONS",
        {ReadinessLevel.LEVEL_2: 0.99},
        raising=False,
    )
    assert project_level(ReadinessField.ENERGY, ReadinessLevel.LEVEL_2) == 0.5
    monkeypatch.setattr(
        vocabulary_module,
        "VOCABULARY_JSON",
        vocabulary_module.VOCABULARY_JSON.replace('"0.50"', '"0.51"', 1),
    )
    with pytest.raises(RuntimeError, match="vocabulary authority"):
        project_level(ReadinessField.ENERGY, ReadinessLevel.LEVEL_2)


@pytest.mark.parametrize("replacement", (-0.0, 0, 1, 0.5000000000000001, math.nan, math.inf))
def test_alternative_numeric_projection_representations_fail_closed(
    monkeypatch, session, replacement,
) -> None:
    *_, verifier, _, _, _, _, _, occurrence = build_readiness(monkeypatch, session)
    feature = occurrence.track_feature_evidence.records[0]
    bad_unit = feature.energy.model_copy(update={"value": replacement})
    bad_feature = feature.model_copy(update={"energy": bad_unit})
    bad_features = occurrence.track_feature_evidence.model_copy(
        update={"records": (bad_feature,)}
    )
    assert not verifier.verify(
        occurrence.model_copy(update={"track_feature_evidence": bad_features})
    )
