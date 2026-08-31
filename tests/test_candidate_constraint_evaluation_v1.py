from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.candidate_formation import (
    CandidateConstraintField,
    CandidateEligibilityReason,
    CandidateEligibilityState,
    CandidateFormer,
    CandidateHardConstraint,
    EXACT_TYPED_EQUALITY_PREDICATE_ID,
    FINITE_VOCABULARY_PREDICATE_ID,
    HardConstraintDeclarationArtifact,
    MATCHING_CONTRACT_ID,
    MATCHING_CONTRACT_SHA256,
    MATCHING_CONTRACT_VERSION,
    PREDICATE_VERSION,
    create_candidate_constraint_vocabulary,
    create_hard_constraint_declaration_v2,
    derive_formed_candidate_pool,
    hard_constraint_declaration_content_sha256,
    matched_vocabulary_terms,
    serialize_hard_constraint_declaration,
    supported_candidate_constraint_predicates,
    tokenize_text,
    verify_matching_contract,
)
from playlist_narrative_engine.candidate_formation.constraint_authority import (
    matching_contract_bytes,
)
from playlist_narrative_engine.candidate_formation.request_assembler import (
    FormationRequestAssembler,
)
from test_candidate_constraint_eligibility import NON_EXPLICIT
from test_formation_request_assembler import assembly_input


def vocabulary(*terms: str):
    return create_candidate_constraint_vocabulary(
        vocabulary_id="product.fixture.words",
        vocabulary_version="1.0",
        terms=tuple(terms),
    )


def vocabulary_constraint(value, *, field=CandidateConstraintField.DISPLAYED_TITLE):
    return CandidateHardConstraint(
        constraint_key="required-vocabulary",
        field=field,
        predicate_id=FINITE_VOCABULARY_PREDICATE_ID,
        predicate_version=PREDICATE_VERSION,
        vocabulary_id=value.vocabulary_id,
        vocabulary_version=value.vocabulary_version,
        vocabulary_sha256=value.canonical_sha256,
        matching_contract_id=MATCHING_CONTRACT_ID,
        matching_contract_version=MATCHING_CONTRACT_VERSION,
        matching_contract_sha256=MATCHING_CONTRACT_SHA256,
    )


def declaration_for(value, constraint=None):
    return create_hard_constraint_declaration_v2(
        artifact_id="constraints-v2",
        declaration_version="2.0",
        source_type="explicit_user_declaration",
        source_reference="request:fixture-v2",
        constraints=(constraint or vocabulary_constraint(value),),
        vocabularies=(value,),
    )


def assemble_v2(value, constraint=None):
    declaration = declaration_for(value, constraint)
    return FormationRequestAssembler().assemble(assembly_input(
        hard_constraint_declaration=declaration,
        authorized_declaration_id=declaration.artifact_id,
        authorized_declaration_version=declaration.declaration_version,
        authorized_declaration_sha256=declaration.canonical_sha256,
    ))


def test_schema_1_canonical_bytes_and_exact_equality_remain_unchanged() -> None:
    declaration = HardConstraintDeclarationArtifact(
        artifact_id="constraints-001",
        declaration_version="1.0",
        source_type="explicit_user_declaration",
        source_reference="request:001",
        constraints=(NON_EXPLICIT,),
    )
    expected = (
        b'{"schema_version":"1.0","artifact_kind":"hard_constraint_declaration",'
        b'"artifact_id":"constraints-001","declaration_version":"1.0",'
        b'"source_type":"explicit_user_declaration","source_reference":"request:001",'
        b'"constraints":[{"constraint_key":"no-explicit","field":"displayed_explicit",'
        b'"expected_json":"false"}]}'
    )
    assert serialize_hard_constraint_declaration(declaration) == expected
    formed = CandidateFormer().form(FormationRequestAssembler().assemble(assembly_input()))
    assert formed.schema_version == "1.0"
    assert formed.formed[0].constraint_eligibility[0].reason is CandidateEligibilityReason.PROPERTY_MATCH
    assert formed.formed[0].constraint_eligibility[0].predicate_id is None
    serialized_request = FormationRequestAssembler().assemble(assembly_input()).model_dump(mode="json")
    assert "hard_constraint_declaration_schema_version" not in serialized_request
    assert "hard_constraint_declaration_sha256" not in serialized_request
    assert "hard_constraint_declaration_json" not in serialized_request
    assert "hard_constraint_vocabularies" not in serialized_request


def test_schema_2_declaration_and_vocabulary_are_deterministic_and_digest_bound() -> None:
    value = vocabulary("zeta", "title", "Café Noir")
    first = declaration_for(value)
    second = declaration_for(value)
    assert first == second
    assert first.canonical_sha256 == hard_constraint_declaration_content_sha256(first)
    assert first.vocabularies[0].terms == ("Café Noir", "title", "zeta")
    assert serialize_hard_constraint_declaration(first) == serialize_hard_constraint_declaration(second)

    tampered = first.model_copy(update={"source_reference": "request:substitute"})
    with pytest.raises(ValidationError, match="canonical digest"):
        HardConstraintDeclarationArtifact.model_validate(tampered.model_dump(mode="json"))


def test_closed_registry_and_published_matching_authority() -> None:
    assert supported_candidate_constraint_predicates() == (
        (EXACT_TYPED_EQUALITY_PREDICATE_ID, PREDICATE_VERSION),
        (FINITE_VOCABULARY_PREDICATE_ID, PREDICATE_VERSION),
    )
    verify_matching_contract()
    assert hashlib.sha256(matching_contract_bytes()).hexdigest() == MATCHING_CONTRACT_SHA256
    unsupported = CandidateHardConstraint(
        constraint_key="unsupported",
        field=CandidateConstraintField.DISPLAYED_TITLE,
        expected_json='"Title track-a"',
        predicate_id="pne.candidate-constraint.unsupported",
        predicate_version="1.0",
    )
    with pytest.raises(ValidationError, match="unsupported candidate constraint predicate"):
        create_hard_constraint_declaration_v2(
            artifact_id="bad", declaration_version="2.0", source_type="explicit",
            source_reference="request:bad", constraints=(unsupported,),
        )


def test_title_vocabulary_match_is_eligible_and_provenance_reaches_formed_pool() -> None:
    request = assemble_v2(vocabulary("title"))
    artifact = CandidateFormer().form(request)
    result = artifact.formed[0].constraint_eligibility[0]
    assert artifact.schema_version == "2.0"
    assert result.state is CandidateEligibilityState.ELIGIBLE
    assert result.matched_terms == ("title",)
    assert result.observed_json == '"Title track-a"'
    assert result.source_evidence_ids == ("record-a",)
    assert result.declaration_sha256 == request.hard_constraint_declaration_sha256
    assert result.vocabulary_sha256 == request.hard_constraint_vocabularies[0].canonical_sha256
    pool = derive_formed_candidate_pool(artifact)
    assert pool.trace.parent_schema_version == "2.0"
    assert pool.formed_entries[0].constraint_eligibility[0] == result
    assert artifact.hard_constraint_declaration_json == request.hard_constraint_declaration_json


def test_schema_2_authority_survives_constructor_and_finalizer_no_bypass_path() -> None:
    from playlist_narrative_engine.evaluation import PlaylistJourneyEvaluator
    from playlist_narrative_engine.product_artifact import (
        FinalProductFinalizer,
        verify_final_product_artifact,
    )
    from playlist_narrative_engine.sequencing import (
        ConstructionPolicy,
        ConstructionState,
        SequentialPlaylistConstructor,
    )

    request = assemble_v2(vocabulary("title"))
    formation = CandidateFormer().form(request)
    pool = derive_formed_candidate_pool(formation)
    policy = ConstructionPolicy()
    construction = SequentialPlaylistConstructor(policy=policy).construct(
        journey_plan=request.journey_plan,
        formed_pool=pool,
        state=ConstructionState(),
        requested_track_count=1,
    )
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=construction,
        journey_plan=request.journey_plan,
        construction_policy=policy,
    )
    final = FinalProductFinalizer().finalize(
        artifact_id="final-v2-constraint",
        journey_plan=request.journey_plan,
        candidate_formation=formation,
        formed_pool=pool,
        construction_policy=policy,
        construction_result=construction,
        evaluation_report=report,
    )
    assert verify_final_product_artifact(
        final,
        journey_plan=request.journey_plan,
        candidate_formation=formation,
        formed_pool=pool,
        construction_policy=policy,
    )
    assert final.content.formation_authority.schema_version == "2.0"
    assert pool.formed_entries[0].constraint_eligibility[0].predicate_id == FINITE_VOCABULARY_PREDICATE_ID


def test_nonmatch_and_artist_only_match_are_ineligible_before_ranking() -> None:
    nonmatch = CandidateFormer().form(assemble_v2(vocabulary("missing")))
    assert nonmatch.formed == ()
    assert nonmatch.withheld[0].constraint_eligibility[0].state is CandidateEligibilityState.INELIGIBLE
    assert nonmatch.withheld[0].constraint_eligibility[0].matched_terms == ()

    artist_only = CandidateFormer().form(assemble_v2(vocabulary("artist")))
    assert artist_only.formed == ()
    result = artist_only.withheld[0].constraint_eligibility[0]
    assert result.observed_json == '"Title track-a"'
    assert result.state is CandidateEligibilityState.INELIGIBLE
    assert derive_formed_candidate_pool(artist_only).candidates == ()


def test_explicit_schema_2_equality_uses_existing_typed_semantics() -> None:
    constraint = CandidateHardConstraint(
        constraint_key="exact-title",
        field=CandidateConstraintField.DISPLAYED_TITLE,
        expected_json='"Title track-a"',
        predicate_id=EXACT_TYPED_EQUALITY_PREDICATE_ID,
        predicate_version=PREDICATE_VERSION,
    )
    declaration = create_hard_constraint_declaration_v2(
        artifact_id="equal-v2", declaration_version="2.0", source_type="explicit",
        source_reference="request:equal", constraints=(constraint,),
    )
    request = FormationRequestAssembler().assemble(assembly_input(
        hard_constraint_declaration=declaration,
        authorized_declaration_id=declaration.artifact_id,
        authorized_declaration_version=declaration.declaration_version,
        authorized_declaration_sha256=declaration.canonical_sha256,
    ))
    result = CandidateFormer().form(request).formed[0].constraint_eligibility[0]
    assert result.state is CandidateEligibilityState.ELIGIBLE
    assert result.reason is CandidateEligibilityReason.EXACT_MATCH


def test_vocabulary_and_matching_substitution_fail_closed() -> None:
    value = vocabulary("title")
    declaration = declaration_for(value)
    substituted_vocabulary = value.model_copy(update={"vocabulary_id": "product.substitute"})
    tampered = declaration.model_copy(update={"vocabularies": (substituted_vocabulary,)})
    with pytest.raises(ValidationError):
        HardConstraintDeclarationArtifact.model_validate(tampered.model_dump(mode="json"))

    constraint = vocabulary_constraint(value).model_copy(
        update={"matching_contract_sha256": "0" * 64}
    )
    with pytest.raises(ValidationError, match="matching authority"):
        create_hard_constraint_declaration_v2(
            artifact_id="bad-match", declaration_version="2.0", source_type="explicit",
            source_reference="request:bad", constraints=(constraint,), vocabularies=(value,),
        )

    valid_artifact = CandidateFormer().form(assemble_v2(value))
    result = valid_artifact.formed[0].constraint_eligibility[0].model_copy(
        update={"matched_terms": ("substituted",)}
    )
    entry = valid_artifact.formed[0].model_copy(
        update={"constraint_eligibility": (result,)}
    )
    tampered_artifact = valid_artifact.model_copy(update={"formed": (entry,)})
    from playlist_narrative_engine.candidate_formation import CandidateFormationArtifact
    with pytest.raises(ValidationError, match="matched terms"):
        CandidateFormationArtifact.model_validate(tampered_artifact.model_dump(mode="json"))

    substituted_binding = valid_artifact.model_copy(
        update={
            "hard_constraint_declaration_json": valid_artifact.hard_constraint_declaration_json.replace(
                "request:fixture-v2", "request:substitute"
            )
        }
    )
    with pytest.raises(ValidationError):
        CandidateFormationArtifact.model_validate(substituted_binding.model_dump(mode="json"))


def test_unicode_case_token_boundary_and_punctuation_contract() -> None:
    value = vocabulary("Café Noir", "cat")
    assert matched_vocabulary_terms("CAFE\u0301 NOIR!", value) == ("Café Noir",)
    assert matched_vocabulary_terms("A cat, then silence.", value) == ("cat",)
    assert matched_vocabulary_terms("concatenate", value) == ()
    assert tokenize_text("rock-and-roll") == ("rock", "and", "roll")


def test_missing_text_metadata_is_unknown_and_withheld() -> None:
    from playlist_narrative_engine.candidate_formation import (
        CandidateIdentityMetadataArtifact,
        ExactStringEvidence,
        EvidenceState,
    )
    from test_evidence_acquisition import acquisition, metadata_record

    base = metadata_record()
    unavailable = ExactStringEvidence(
        state=EvidenceState.UNAVAILABLE, value=None, observations=()
    )
    record = base.model_copy(update={"source_catalog_identity": unavailable})
    acquired = acquisition(metadata=CandidateIdentityMetadataArtifact(
        artifact_id="metadata-001", track_snapshot_id="snapshot-001", records=(record,)
    ))
    value = vocabulary("catalog")
    constraint = vocabulary_constraint(value, field=CandidateConstraintField.SOURCE_CATALOG_IDENTITY)
    declaration = declaration_for(value, constraint)
    request = FormationRequestAssembler().assemble(assembly_input(
        acquisition=acquired,
        hard_constraint_declaration=declaration,
        authorized_declaration_id=declaration.artifact_id,
        authorized_declaration_version=declaration.declaration_version,
        authorized_declaration_sha256=declaration.canonical_sha256,
    ))
    artifact = CandidateFormer().form(request)
    result = artifact.withheld[0].constraint_eligibility[0]
    assert result.state is CandidateEligibilityState.UNKNOWN
    assert result.reason is CandidateEligibilityReason.REQUIRED_FIELD_UNKNOWN
    assert result.observed_json is None
    assert artifact.formed == ()


def test_product_constraint_implementation_has_no_research_or_workbench_imports() -> None:
    root = Path("src/playlist_narrative_engine/candidate_formation")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "playlist_narrative_engine.research_store" not in source
    assert "playlist_narrative_engine.maestro_workbench" not in source
    assert "Animal Vocabulary" not in source
