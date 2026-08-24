from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from playlist_narrative_engine.research_store.animal_vocabulary import (
    ANIMAL_VOCABULARY_CASE_SENSITIVE,
    ANIMAL_VOCABULARY_ID,
    ANIMAL_VOCABULARY_KEY,
    ANIMAL_VOCABULARY_SHA256,
    ANIMAL_VOCABULARY_TERMS,
    ANIMAL_VOCABULARY_VERSION,
    animal_vocabulary_parameters,
    verify_animal_vocabulary_publication,
)
from playlist_narrative_engine.research_store.study_structured_evaluation import (
    evaluate_structured_constraint,
)
from playlist_narrative_engine.research_store.study_evaluator_registry import (
    DEFAULT_STUDY_EVALUATOR_REGISTRY,
)
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from playlist_narrative_engine.research_store.study_vocabulary import (
    STANDALONE_MEMBER_MATCH_CONTRACT_ID,
    STANDALONE_MEMBER_MATCH_CONTRACT_SHA256,
    STANDALONE_MEMBER_MATCH_CONTRACT_VERSION,
    canonical_finite_vocabulary_bytes,
    finite_vocabulary_sha256,
)
from test_study_structured_evaluation_p7a import _document


def _text_parameter(key: str, value: str) -> dict[str, object]:
    return {"parameter_key": key, "value_type": "TEXT", "text_value": value}


def _plan() -> dict[str, object]:
    return {
        "instrumentation_version": "1", "subject_kind": "PLACEMENT_FIELD",
        "subject_field": "display_title",
        "subject_selector": {"evaluator_key": "selector.all_placements", "evaluator_version": "1"},
        "subject_evaluator": {"evaluator_key": "subject.lexical_any_vocabulary_member", "evaluator_version": "1"},
        "aggregate_evaluator": {"evaluator_key": "aggregate.all_subjects_required", "evaluator_version": "1"},
        "require_complete_subject_set": True, "allow_partial_subject_status": False,
        "measurement_definitions": [{
            "measurement_key": "display-title", "authority": "DIRECT_OBSERVATION",
            "value_type": "TEXT", "required": True, "evidence_required": False,
            "unavailable_policy": "MAY_BE_UNAVAILABLE",
        }],
        "parameters": [
            *animal_vocabulary_parameters(),
            _text_parameter("mixed_status", "FAIL"),
            _text_parameter("all_fail_status", "FAIL"),
            _text_parameter("unknown_status", "UNKNOWN"),
        ],
        "vocabulary_terms": list(ANIMAL_VOCABULARY_TERMS),
    }


def _evaluate(*rows: tuple[str, str]) -> dict[str, object]:
    tracks = [
        {"id": 100 + index, "observed_ordinal": index, "display_title": title,
         "display_artist": artist}
        for index, (title, artist) in enumerate(rows, start=1)
    ]
    measurements = [{
        "subject_key": f"FIELD:{track['id']}:display_title",
        "measurement_key": "display-title", "authority_kind": "DIRECT_OBSERVATION",
        "value_type": "TEXT", "boolean_value": None, "integer_value": None,
        "decimal_value": None, "text_value": track["display_title"], "date_value": None,
        "vocabulary_term_key": None, "unavailable_reason": None, "evidence": [],
    } for track in tracks]
    return evaluate_structured_constraint(_plan(), {"id": 7, "tracks": tracks}, 42, measurements)


def _members() -> set[str]:
    return {str(item["term_definition"]) for item in ANIMAL_VOCABULARY_TERMS}


def test_literal_publication_identity_version_count_and_digest() -> None:
    assert ANIMAL_VOCABULARY_KEY == "animal-names"
    assert ANIMAL_VOCABULARY_ID == "pne.research-vocabulary.animal-names"
    assert ANIMAL_VOCABULARY_VERSION == "1.0"
    assert ANIMAL_VOCABULARY_CASE_SENSITIVE is False
    assert len(ANIMAL_VOCABULARY_TERMS) == 351
    assert ANIMAL_VOCABULARY_SHA256 == "c63f9de32ebfc76b4ff622f68bf3422a062a4a9afbdb120f94a4a40b8aec95cb"
    assert verify_animal_vocabulary_publication() == tuple(
        item["term_definition"] for item in ANIMAL_VOCABULARY_TERMS
    )


def test_authoring_order_does_not_change_canonical_bytes_or_digest() -> None:
    arguments = {
        "vocabulary_id": ANIMAL_VOCABULARY_ID,
        "vocabulary_version": ANIMAL_VOCABULARY_VERSION,
        "vocabulary_key": ANIMAL_VOCABULARY_KEY,
    }
    assert canonical_finite_vocabulary_bytes(terms=ANIMAL_VOCABULARY_TERMS, **arguments) == canonical_finite_vocabulary_bytes(terms=reversed(ANIMAL_VOCABULARY_TERMS), **arguments)
    assert finite_vocabulary_sha256(terms=reversed(ANIMAL_VOCABULARY_TERMS), **arguments) == ANIMAL_VOCABULARY_SHA256


def test_member_mutation_fails_literal_publication_verification() -> None:
    changed = list(deepcopy(ANIMAL_VOCABULARY_TERMS))
    changed[0]["term_definition"] = "changed-member"
    with pytest.raises(ValueError, match="digest"):
        verify_animal_vocabulary_publication(terms=tuple(changed))


def test_matching_contract_binding_is_exact() -> None:
    parameters = {
        item["parameter_key"]: item.get("boolean_value", item.get("text_value"))
        for item in animal_vocabulary_parameters()
    }
    assert parameters["matching_contract_id"] == STANDALONE_MEMBER_MATCH_CONTRACT_ID
    assert parameters["matching_contract_version"] == STANDALONE_MEMBER_MATCH_CONTRACT_VERSION
    assert parameters["matching_contract_sha256"] == STANDALONE_MEMBER_MATCH_CONTRACT_SHA256
    parameters["matching_contract_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="matching-contract"):
        verify_animal_vocabulary_publication(parameters=parameters)


def test_singular_plural_irregular_and_compound_forms_are_explicit() -> None:
    members = _members()
    assert {"wolf", "wolves", "mouse", "mice", "monkey", "monkeys", "dove", "doves"} <= members
    assert {"blackbird", "catfish", "seahorse", "ladybug", "butterfly"} <= members
    assert "wolfs" not in members


def test_ambiguous_terms_are_lexical_and_mythical_terms_are_absent() -> None:
    members = _members()
    assert {"seal", "bass", "crane", "mole", "turkey"} <= members
    assert {"phoenix", "dragon", "unicorn", "griffin"}.isdisjoint(members)
    assert _evaluate(("Seal the Deal", "Artist"))["subject_results"][0]["status"] == "PASS"
    assert _evaluate(("Phoenix", "Artist"))["subject_results"][0]["status"] == "FAIL"


def test_extinct_real_world_common_names_are_published() -> None:
    assert {"dinosaur", "dinosaurs", "dodo", "dodos", "mammoth", "mammoths"} <= _members()
    assert _evaluate(("Mammoth", "Artist"))["subject_results"][0]["status"] == "PASS"


@pytest.mark.parametrize("title", [
    "Hungry Like the Wolf", "Monkey Gone to Heaven", "Blackbird",
    "When Doves Cry", "Crocodile Rock",
])
def test_required_title_probes_pass_through_generic_evaluator(title: str) -> None:
    assert _evaluate((title, "Artist"))["subject_results"][0]["status"] == "PASS"


def test_artist_only_animal_term_and_unrelated_title_fail_title_predicate() -> None:
    result = _evaluate(("Hotel California", "Eagles"), ("Ordinary World", "Artist"))
    assert [item["status"] for item in result["subject_results"]] == ["FAIL", "FAIL"]
    assert all(item["subject"]["governed_field"] == "display_title" for item in result["subject_results"])
    assert result["aggregate_constraint_result"]["status"] == "FAIL"


def test_universal_aggregate_fails_when_one_title_has_no_member() -> None:
    result = _evaluate(("Blackbird", "Artist"), ("Ordinary World", "Artist"))
    assert [item["status"] for item in result["subject_results"]] == ["PASS", "FAIL"]
    assert result["aggregate_constraint_result"]["status"] == "FAIL"


def test_animal_vocabulary_plan_is_valid_prospective_study_authority() -> None:
    document = _document(structured=True)
    document["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"] = _plan()
    protocol = StudyRegistrationInput.model_validate(document).protocol
    DEFAULT_STUDY_EVALUATOR_REGISTRY.validate_protocol(protocol)


def test_generic_evaluator_contains_no_animal_specific_logic() -> None:
    source = Path("src/playlist_narrative_engine/research_store/study_evaluator_registry.py").read_text(encoding="utf-8").lower()
    assert "animal_vocabulary" not in source
    assert "animal-names" not in source
    assert "blackbird" not in source
