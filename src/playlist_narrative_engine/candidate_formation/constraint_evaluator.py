from __future__ import annotations

import json
from collections.abc import Callable

from playlist_narrative_engine.candidate_formation.constraint_authority import (
    CandidateConstraintVocabularyArtifact,
    EXACT_TYPED_EQUALITY_PREDICATE_ID,
    FINITE_VOCABULARY_PREDICATE_ID,
    MATCHING_CONTRACT_ID,
    MATCHING_CONTRACT_SHA256,
    MATCHING_CONTRACT_VERSION,
    PREDICATE_VERSION,
    matched_vocabulary_terms,
)
from playlist_narrative_engine.candidate_formation.formation_schemas import (
    CandidateConstraintEligibility,
    CandidateConstraintField,
    CandidateEligibilityReason,
    CandidateEligibilityState,
    CandidateHardConstraint,
)


PredicateEvaluator = Callable[
    [CandidateHardConstraint, object | None, tuple[str, ...], dict[str, CandidateConstraintVocabularyArtifact], dict[str, str]],
    CandidateConstraintEligibility,
]


def evaluate_candidate_constraint(
    *,
    constraint: CandidateHardConstraint,
    observed: object | None,
    source_evidence_ids: tuple[str, ...],
    vocabularies: tuple[CandidateConstraintVocabularyArtifact, ...] = (),
    declaration_authority: dict[str, str] | None = None,
) -> CandidateConstraintEligibility:
    implicit_legacy = constraint.predicate_id is None
    identity = (
        EXACT_TYPED_EQUALITY_PREDICATE_ID,
        PREDICATE_VERSION,
    ) if implicit_legacy else (constraint.predicate_id, constraint.predicate_version)
    evaluator = _PREDICATE_REGISTRY.get(identity)
    if evaluator is None:
        raise ValueError(
            f"unsupported candidate constraint predicate identity: {identity[0]}/{identity[1]}"
        )
    vocabulary_map = {
        f"{item.vocabulary_id}\n{item.vocabulary_version}": item
        for item in vocabularies
    }
    authority = {} if implicit_legacy else dict(declaration_authority or {})
    if not implicit_legacy and set(authority) != {
        "declaration_id", "declaration_schema_version", "declaration_version", "declaration_sha256"
    }:
        raise ValueError("explicit predicate evaluation requires declaration authority")
    return evaluator(
        constraint,
        observed,
        source_evidence_ids,
        vocabulary_map,
        authority,
    )


def _exact_typed_equality(
    constraint: CandidateHardConstraint,
    observed: object | None,
    source_evidence_ids: tuple[str, ...],
    vocabularies: dict[str, CandidateConstraintVocabularyArtifact],
    authority: dict[str, str],
) -> CandidateConstraintEligibility:
    del vocabularies
    if constraint.expected_json is None:
        raise ValueError("exact equality requires an expected value")
    expected = json.loads(constraint.expected_json)
    if observed is None:
        state = CandidateEligibilityState.UNKNOWN
        reason = CandidateEligibilityReason.REQUIRED_METADATA_UNKNOWN
        observed_json = None
    else:
        matches = observed == expected and type(observed) is type(expected)
        state = CandidateEligibilityState.ELIGIBLE if matches else CandidateEligibilityState.INELIGIBLE
        reason = (
            CandidateEligibilityReason.PROPERTY_MATCH
            if matches and constraint.field is CandidateConstraintField.DISPLAYED_EXPLICIT
            else CandidateEligibilityReason.EXACT_MATCH
            if matches
            else CandidateEligibilityReason.PROPERTY_MISMATCH
            if constraint.field is CandidateConstraintField.DISPLAYED_EXPLICIT
            else CandidateEligibilityReason.EXACT_MISMATCH
        )
        observed_json = _json(observed)
    return CandidateConstraintEligibility(
        constraint_key=constraint.constraint_key,
        field=constraint.field,
        state=state,
        reason=reason,
        expected_json=constraint.expected_json,
        observed_json=observed_json,
        source_evidence_ids=source_evidence_ids,
        predicate_id=constraint.predicate_id,
        predicate_version=constraint.predicate_version,
        **authority,
    )


def _finite_vocabulary_membership(
    constraint: CandidateHardConstraint,
    observed: object | None,
    source_evidence_ids: tuple[str, ...],
    vocabularies: dict[str, CandidateConstraintVocabularyArtifact],
    authority: dict[str, str],
) -> CandidateConstraintEligibility:
    if constraint.field is CandidateConstraintField.DISPLAYED_EXPLICIT:
        raise ValueError("finite vocabulary requires a governed text field")
    key = f"{constraint.vocabulary_id}\n{constraint.vocabulary_version}"
    vocabulary = vocabularies.get(key)
    if vocabulary is None or vocabulary.canonical_sha256 != constraint.vocabulary_sha256:
        raise ValueError("finite-vocabulary authority is missing or substituted")
    if (
        constraint.matching_contract_id != MATCHING_CONTRACT_ID
        or constraint.matching_contract_version != MATCHING_CONTRACT_VERSION
        or constraint.matching_contract_sha256 != MATCHING_CONTRACT_SHA256
        or vocabulary.matching_contract_id != constraint.matching_contract_id
        or vocabulary.matching_contract_version != constraint.matching_contract_version
        or vocabulary.matching_contract_sha256 != constraint.matching_contract_sha256
    ):
        raise ValueError("matching-contract authority is missing or substituted")
    if observed is None:
        state = CandidateEligibilityState.UNKNOWN
        reason = CandidateEligibilityReason.REQUIRED_FIELD_UNKNOWN
        observed_json = None
        matched_terms: tuple[str, ...] = ()
    else:
        if not isinstance(observed, str):
            raise ValueError("finite vocabulary observed authority must be text")
        matched_terms = matched_vocabulary_terms(observed, vocabulary)
        state = (
            CandidateEligibilityState.ELIGIBLE
            if matched_terms else CandidateEligibilityState.INELIGIBLE
        )
        reason = (
            CandidateEligibilityReason.VOCABULARY_MEMBER_MATCH
            if matched_terms else CandidateEligibilityReason.VOCABULARY_MEMBER_NONMATCH
        )
        observed_json = _json(observed)
    return CandidateConstraintEligibility(
        constraint_key=constraint.constraint_key,
        field=constraint.field,
        state=state,
        reason=reason,
        expected_json=None,
        observed_json=observed_json,
        source_evidence_ids=source_evidence_ids,
        predicate_id=constraint.predicate_id,
        predicate_version=constraint.predicate_version,
        vocabulary_id=constraint.vocabulary_id,
        vocabulary_version=constraint.vocabulary_version,
        vocabulary_sha256=constraint.vocabulary_sha256,
        matching_contract_id=constraint.matching_contract_id,
        matching_contract_version=constraint.matching_contract_version,
        matching_contract_sha256=constraint.matching_contract_sha256,
        matched_terms=matched_terms,
        **authority,
    )


_PREDICATE_REGISTRY: dict[tuple[str | None, str | None], PredicateEvaluator] = {
    (EXACT_TYPED_EQUALITY_PREDICATE_ID, PREDICATE_VERSION): _exact_typed_equality,
    (FINITE_VOCABULARY_PREDICATE_ID, PREDICATE_VERSION): _finite_vocabulary_membership,
}


def supported_candidate_constraint_predicates() -> tuple[tuple[str, str], ...]:
    return tuple(sorted(_PREDICATE_REGISTRY, key=lambda item: (item[0].encode(), item[1].encode())))  # type: ignore[union-attr]


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
