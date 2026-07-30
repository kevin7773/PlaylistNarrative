from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.elicitation import (
    ARTIST_QUESTIONNAIRE_SCHEMA_VERSION,
    ArtistQuestionnaireObjective,
    ArtistQuestionnaireRequest,
    ArtistQuestionnaireSeed,
    ArtistQuestionnaireSeedGenerator,
    ArtistSeedEvidence,
    InclusionBasis,
    serialize_artist_questionnaire_seed,
)
from playlist_narrative_engine.evaluation import PlaylistJourneyEvaluator
from playlist_narrative_engine.sequencing import (
    CandidateSelector,
    SequentialPlaylistConstructor,
    TrackScorer,
)


def evidence(
    evidence_id: str,
    artist_name: str,
    *,
    source: str = "manual_seed",
) -> ArtistSeedEvidence:
    return ArtistSeedEvidence(
        evidence_id=evidence_id,
        artist_name=artist_name,
        source=source,
        rationale=f"{artist_name} was explicitly supplied for manual rating.",
    )


def request(
    seed_evidence: tuple[ArtistSeedEvidence, ...],
) -> ArtistQuestionnaireRequest:
    return ArtistQuestionnaireRequest(
        objective=ArtistQuestionnaireObjective(
            objective_id="initial-manual-rating",
            statement="Create a starting artist list for manual rating.",
        ),
        seed_evidence=seed_evidence,
    )


def test_equivalent_inputs_produce_equal_objects_and_identical_bytes() -> None:
    first_request = request(
        (
            evidence("seed-2", "Björk"),
            evidence("seed-1", "Aphex Twin"),
        )
    )
    second_request = request(tuple(reversed(first_request.seed_evidence)))
    generator = ArtistQuestionnaireSeedGenerator()

    first = generator.generate(first_request)
    second = generator.generate(second_request)

    assert first == second
    assert serialize_artist_questionnaire_seed(first) == (
        serialize_artist_questionnaire_seed(second)
    )


def test_output_is_closed_to_verbatim_supplied_artist_names() -> None:
    artifact = ArtistQuestionnaireSeedGenerator().generate(
        request(
            (
                evidence("one", "The Cure"),
                evidence("two", "Siouxsie and the Banshees"),
            )
        )
    )

    assert tuple(entry.artist_name for entry in artifact.entries) == (
        "Siouxsie and the Banshees",
        "The Cure",
    )
    assert set(entry.artist_name for entry in artifact.entries) == {
        item.artist_name
        for item in (
            evidence("one", "The Cure"),
            evidence("two", "Siouxsie and the Banshees"),
        )
    }


def test_exact_duplicates_are_consolidated_with_complete_provenance() -> None:
    artifact = ArtistQuestionnaireSeedGenerator().generate(
        request(
            (
                evidence("second", "New Order", source="interview"),
                evidence("first", "New Order", source="worksheet"),
            )
        )
    )

    assert len(artifact.entries) == 1
    entry = artifact.entries[0]
    assert entry.ordinal == 1
    assert entry.artist_name == "New Order"
    assert entry.inclusion_basis is InclusionBasis.EXPLICIT_SEED_EVIDENCE
    assert tuple(item.evidence_id for item in entry.source_evidence) == (
        "first",
        "second",
    )


def test_case_variants_are_not_merged_or_inferred_as_aliases() -> None:
    artifact = ArtistQuestionnaireSeedGenerator().generate(
        request(
            (
                evidence("upper", "HEALTH"),
                evidence("lower", "Health"),
            )
        )
    )

    assert tuple(entry.artist_name for entry in artifact.entries) == (
        "HEALTH",
        "Health",
    )


def test_unicode_normalization_is_not_used_for_deduplication() -> None:
    composed = "Beyoncé"
    decomposed = "Beyonce\u0301"
    artifact = ArtistQuestionnaireSeedGenerator().generate(
        request(
            (
                evidence("composed", composed),
                evidence("decomposed", decomposed),
            )
        )
    )

    assert composed != decomposed
    assert {entry.artist_name for entry in artifact.entries} == {
        composed,
        decomposed,
    }


def test_surrounding_whitespace_is_rejected_not_trimmed() -> None:
    with pytest.raises(
        ValidationError,
        match="text fields cannot contain surrounding whitespace",
    ):
        evidence("spaced", " Kraftwerk")


def test_empty_evidence_produces_empty_questionnaire_seed() -> None:
    artifact = ArtistQuestionnaireSeedGenerator().generate(request(()))

    assert artifact.entries == ()
    assert artifact.recommendation_claims is False


def test_ratings_are_explicitly_unset_and_output_makes_no_recommendation() -> None:
    artifact = ArtistQuestionnaireSeedGenerator().generate(
        request((evidence("one", "Kraftwerk"),))
    )

    assert artifact.entries[0].rating is None
    assert artifact.artifact_purpose == "elicitation_test_artifact"
    assert artifact.recommendation_claims is False
    assert "playlist" not in artifact.entries[0].inclusion_explanation.lower()
    assert "recommend" not in artifact.entries[0].inclusion_explanation.lower()


def test_schema_is_versioned_and_serialization_field_order_is_stable() -> None:
    artifact = ArtistQuestionnaireSeedGenerator().generate(
        request((evidence("one", "Kraftwerk"),))
    )
    serialized = serialize_artist_questionnaire_seed(artifact)
    parsed = json.loads(serialized)

    assert artifact.schema_version == ARTIST_QUESTIONNAIRE_SCHEMA_VERSION
    assert tuple(parsed) == (
        "schema_version",
        "artifact_kind",
        "artifact_purpose",
        "objective",
        "approved_local_rules",
        "ordering_rule",
        "entries",
        "recommendation_claims",
    )
    assert serialized == serialize_artist_questionnaire_seed(artifact)


def test_inputs_and_outputs_are_immutable() -> None:
    seed_request = request((evidence("one", "Kraftwerk"),))
    artifact = ArtistQuestionnaireSeedGenerator().generate(seed_request)

    with pytest.raises(ValidationError):
        seed_request.objective.statement = "Changed"
    with pytest.raises(ValidationError):
        artifact.entries[0].artist_name = "Changed"


def test_nonempty_local_rules_are_rejected_in_schema_1_0() -> None:
    with pytest.raises(
        ValidationError,
        match="schema 1.0 approves no local derivation rules",
    ):
        ArtistQuestionnaireRequest(
            objective=ArtistQuestionnaireObjective(
                objective_id="initial-manual-rating",
                statement="Create a starting artist list for manual rating.",
            ),
            seed_evidence=(evidence("one", "Kraftwerk"),),
            approved_local_rules=("related_artist_expansion",),
        )


def test_duplicate_evidence_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="seed evidence IDs must be unique"):
        request(
            (
                evidence("duplicate", "Kraftwerk"),
                evidence("duplicate", "New Order"),
            )
        )


def test_artifact_schema_rejects_an_artist_not_reproduced_by_provenance() -> None:
    artifact = ArtistQuestionnaireSeedGenerator().generate(
        request((evidence("one", "Kraftwerk"),))
    )
    tampered = artifact.model_dump(mode="json")
    tampered["entries"][0]["artist_name"] = "Unproven Artist"

    with pytest.raises(
        ValidationError,
        match="source evidence artist name must exactly match",
    ):
        ArtistQuestionnaireSeed.model_validate(tampered)


def test_generation_is_isolated_from_downstream_playlist_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("elicitation called a downstream playlist layer")

    monkeypatch.setattr(TrackScorer, "score", unexpected_call)
    monkeypatch.setattr(CandidateSelector, "select", unexpected_call)
    monkeypatch.setattr(
        SequentialPlaylistConstructor,
        "construct",
        unexpected_call,
    )
    monkeypatch.setattr(PlaylistJourneyEvaluator, "evaluate", unexpected_call)

    artifact = ArtistQuestionnaireSeedGenerator().generate(
        request((evidence("one", "Kraftwerk"),))
    )

    assert tuple(entry.artist_name for entry in artifact.entries) == ("Kraftwerk",)
