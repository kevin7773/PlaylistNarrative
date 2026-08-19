from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from playlist_narrative_engine.research_store.study_calculators import calculate_paired_difference
from playlist_narrative_engine.research_store.study_evaluator_registry import DEFAULT_STUDY_EVALUATOR_REGISTRY
from playlist_narrative_engine.research_store.study_protocol import protocol_registration_hash
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from playlist_narrative_engine.research_store.study_execution_registry import DEFAULT_STUDY_EXECUTION_REGISTRY
from playlist_narrative_engine.research_store.study_structured_evaluation import (
    enumerate_evaluation_subjects,
    evaluate_structured_constraint,
)


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static" / "study_builder.js"


def _plan() -> dict[str, object]:
    return {
        "instrumentation_version": "1", "subject_kind": "PLACEMENT_FIELD",
        "subject_field": "explicit_flag",
        "subject_selector": {"evaluator_key": "selector.exact_displayed_title_artist", "evaluator_version": "1"},
        "subject_evaluator": {"evaluator_key": "subject.boolean_equals", "evaluator_version": "1"},
        "aggregate_evaluator": {"evaluator_key": "aggregate.unique_selected_subject", "evaluator_version": "1"},
        "require_complete_subject_set": True, "allow_partial_subject_status": False,
        "measurement_definitions": [{
            "measurement_key": "observed", "authority": "DIRECT_OBSERVATION",
            "value_type": "BOOLEAN", "required": True, "evidence_required": True,
            "unavailable_policy": "MAY_BE_UNAVAILABLE",
        }],
        "parameters": [
            {"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": False},
            {"parameter_key": "display_artist", "value_type": "TEXT", "text_value": "DNCE"},
            {"parameter_key": "match_semantics", "value_type": "TEXT", "text_value": "EXACT_CODEPOINT_V1"},
        ],
        "vocabulary_terms": [
            {"vocabulary_key": "accepted_display_titles", "term_key": "title-1", "term_definition": "Cake By The Ocean"},
            {"vocabulary_key": "accepted_display_titles", "term_key": "title-2", "term_definition": "Cake By The Ocean [Explicit]"},
        ],
    }


def _experiment(rows: list[tuple[str, str, bool | None]]) -> dict[str, object]:
    return {"id": 9, "tracks": [
        {"id": index, "observed_ordinal": index, "title": title, "artist": artist, "explicit_flag": explicit}
        for index, (title, artist, explicit) in enumerate(rows, 1)
    ]}


def _measurement(subject: dict[str, object], value: bool | None, *, unavailable: bool = False):
    return {
        "subject_key": subject["subject_key"], "measurement_key": "observed",
        "authority_kind": "DIRECT_OBSERVATION", "value_type": "UNAVAILABLE" if unavailable else "BOOLEAN",
        "boolean_value": None if unavailable else value,
        "unavailable_reason": "badge obscured" if unavailable else None,
        "evidence": [
            {"source_key": "screen", "evidence_link_field": "title", "evidence_role": "SUBJECT_IDENTITY"},
            {"source_key": "screen", "evidence_link_field": "artist", "evidence_role": "SUBJECT_IDENTITY"},
            {"source_key": "screen", "evidence_link_field": "explicit_flag", "evidence_role": "OBSERVED_VALUE"},
        ],
    }


def test_exact_target_selector_has_no_hidden_normalization_and_honors_registered_set():
    rows = [
        ("Cake By The Ocean", "DNCE", False),
        ("Cake By The Ocean [Explicit]", "DNCE", True),
        ("cake By The Ocean", "DNCE", True),
        ("Cake By The Ocean ", "DNCE", True),
        ("Cake By The Ocean!", "DNCE", True),
        ("Cake By The Ocean", "DNCÉ", True),
        ("Cake By The Ocean", "Other", True),
        ("Other", "DNCE", True),
    ]
    subjects = enumerate_evaluation_subjects(_plan(), _experiment(rows), 4)
    assert [row["experiment_track_id"] for row in subjects] == [1, 2]
    assert [row["enumeration_ordinal"] for row in subjects] == [1, 2]


def test_unique_target_aggregate_distinguishes_absent_ambiguous_and_observed_states():
    absent = evaluate_structured_constraint(_plan(), _experiment([("Other", "DNCE", True)]), 4, [])
    assert absent["complete"] and absent["subjects"] == []
    assert absent["aggregate_constraint_result"]["reason_code"] == "TARGET_ABSENT"

    ambiguous = evaluate_structured_constraint(_plan(), _experiment([
        ("Cake By The Ocean", "DNCE", False),
        ("Cake By The Ocean [Explicit]", "DNCE", True),
    ]), 4, [])
    assert ambiguous["complete"] and len(ambiguous["subjects"]) == 2
    assert ambiguous["measurements"] == [] and ambiguous["subject_results"] == []
    assert ambiguous["aggregate_constraint_result"]["reason_code"] == "TARGET_AMBIGUOUS"

    for value, status, reason in [
        (False, "PASS", "TARGET_FOUND_EXPECTED_VALUE"),
        (True, "FAIL", "TARGET_FOUND_OTHER_VALUE"),
    ]:
        experiment = _experiment([("Cake By The Ocean", "DNCE", value), ("Unrelated", "Other", True)])
        subject = enumerate_evaluation_subjects(_plan(), experiment, 4)[0]
        result = evaluate_structured_constraint(_plan(), experiment, 4, [_measurement(subject, value)])
        assert result["complete"] and result["aggregate_constraint_result"]["status"] == status
        assert result["aggregate_constraint_result"]["reason_code"] == reason

    experiment = _experiment([("Cake By The Ocean", "DNCE", None)])
    subject = enumerate_evaluation_subjects(_plan(), experiment, 4)[0]
    unavailable = evaluate_structured_constraint(_plan(), experiment, 4, [_measurement(subject, None, unavailable=True)])
    assert unavailable["aggregate_constraint_result"]["status"] == "UNKNOWN"
    assert unavailable["aggregate_constraint_result"]["reason_code"] == "REQUIRED_OBSERVATION_NOT_DERIVABLE"


def _paired_v2():
    return {
        "id": 8, "analysis_key": "paired", "outcome_key": "target-state",
        "calculator_key": "analysis.paired_difference", "calculator_version": "2",
        "dimensions": [{"dimension_role": "MATCH", "dimension_key": "BLOCK", "ordinal": 1}, {"dimension_role": "MATCH", "dimension_key": "REPLICATE", "ordinal": 2}],
        "condition_bindings": [{"comparison_role": "LEFT", "condition_key": "a"}, {"comparison_role": "RIGHT", "condition_key": "b"}],
        "parameters": [{"parameter_key": "difference_direction", "ordinal": 1, "text_value": "RIGHT_MINUS_LEFT"}, {"parameter_key": "pair_completeness", "ordinal": 1, "text_value": "EXCLUDE_NON_NUMERIC_PAIR"}, {"parameter_key": "missing_policy", "ordinal": 1, "text_value": "EXCLUDE_PAIR_AND_REPORT"}],
    }


def _outcome(run_id, value=None, *, reason=None):
    return {"execution_state": "AVAILABLE", "derivability_state": "DERIVABLE",
            "calculation_state": "CALCULATED" if value is not None else "NOT_CALCULABLE",
            "decimal_value": value, "planned_run_id": run_id,
            "source_reason_codes": [] if reason is None else [reason]}


def test_pairwise_exclusion_v2_reports_each_pair_and_preserves_direction():
    protocol = {"id": 2, "registration_hash": "a" * 64, "planned_runs": [
        {"id": 1, "condition_key": "a", "block_key": "b1", "replicate_number": 1},
        {"id": 2, "condition_key": "b", "block_key": "b1", "replicate_number": 1},
        {"id": 3, "condition_key": "a", "block_key": "b1", "replicate_number": 2},
        {"id": 4, "condition_key": "b", "block_key": "b1", "replicate_number": 2},
    ]}
    result = calculate_paired_difference(_paired_v2(), protocol, {
        1: _outcome(1, "0"), 2: _outcome(2, "1"),
        3: _outcome(3, "1"), 4: _outcome(4, reason="TARGET_ABSENT"),
    })
    assert result["calculation_state"] == "CALCULATED"
    assert result["total_registered_pair_count"] == 2
    assert result["eligible_pair_count"] == 1 and result["excluded_pair_count"] == 1
    assert result["mean_difference"] == "1"
    assert result["pairs"][0]["difference"] == "1"
    assert result["pairs"][1]["reason_code"] == "RIGHT_TARGET_ABSENT"
    assert result["pairs"][1]["left_planned_run_id"] == 3
    assert result["pairs"][1]["right_planned_run_id"] == 4

    none = calculate_paired_difference(_paired_v2(), protocol, {
        key: _outcome(key, reason="TARGET_AMBIGUOUS") for key in range(1, 5)
    })
    assert none["calculation_state"] == "NOT_CALCULABLE"
    assert none["reason_code"] == "ZERO_ELIGIBLE_PAIRS"


def _compile(config):
    script = f"const b=require({json.dumps(str(BUILDER))});b.compile({json.dumps(config)}).then(x=>console.log(JSON.stringify(x))).catch(e=>{{console.error(e);process.exit(1)}});"
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def _builder_config():
    return {
        "studyKey": "TARGET-DRAFT", "title": "Target observation draft", "researchQuestion": "Does treatment change target state?",
        "objective": "", "primaryHypothesis": "", "nullHypothesis": "", "seed": "target-seed", "sourceSystem": "Maestro Beta",
        "operationalPolicy": "Record operations separately.", "refusalPolicy": "Record refusal.", "missingPolicy": "No imputation.",
        "leftKey": "condition-a", "leftLabel": "Requested target", "leftFactor": "No restriction.",
        "rightKey": "condition-b", "rightLabel": "Requested target plus restriction", "rightFactor": "No Explicit target.",
        "basePrompt": "Create exactly 10 tracks and include the requested track.", "leftFraming": "", "rightFraming": "Do not use an Explicit target.",
        "blockCount": 1, "replicates": 20,
        "constraints": [
            {"constraintKey": "target-state", "template": "target_explicit", "applicability": "BOTH", "primary": True,
             "acceptedDisplayTitles": ["Cake By The Ocean", "Cake By The Ocean [Explicit]"], "displayArtist": "DNCE", "aggregateBehavior": "MIXED_PARTIAL"},
            {"constraintKey": "exact-count", "template": "exact_count", "applicability": "BOTH", "primary": False,
             "expectedCount": 10, "aggregateBehavior": "MIXED_PARTIAL"},
        ],
        "outcomeKind": "AUTO", "success": "PASS", "unknownPolicy": "EXCLUDE", "missingInputPolicy": "NOT_CALCULABLE",
        "refusalTreatment": "NOT_CALCULABLE", "failureTreatment": "NOT_CALCULABLE", "direction": "RIGHT_MINUS_LEFT",
    }


def test_guided_target_protocol_is_authoritative_roundtrippable_and_hashed():
    draft = _compile(_builder_config())
    parsed = StudyRegistrationInput.model_validate(draft)
    assert len(parsed.protocol.planned_runs) == 40
    target = next(item for item in draft["protocol"]["constraint_definitions"] if item["constraint_key"] == "target-state")
    assert target["is_hard_constraint"] is False
    assert target["structured_evaluation_plan"]["subject_selector"] == {"evaluator_key": "selector.exact_displayed_title_artist", "evaluator_version": "1"}
    assert [term["term_definition"] for term in target["structured_evaluation_plan"]["vocabulary_terms"]] == ["Cake By The Ocean", "Cake By The Ocean [Explicit]"]
    outcome = draft["protocol"]["execution_contract"]["outcome_calculation_plans"][0]
    assert outcome["calculator_key"] == "outcome.constraint_status_rate"
    assert [item["constraint_key"] for item in outcome["constraint_bindings"]] == ["target-state"]
    assert next(item for item in outcome["parameters"] if item["parameter_key"] == "unknown_policy")["text_value"] == "NOT_CALCULABLE"
    analysis = draft["protocol"]["execution_contract"]["analysis_calculation_plans"][0]
    assert (analysis["calculator_key"], analysis["calculator_version"], analysis["output_shape_version"]) == ("analysis.paired_difference", "2", "2")
    DEFAULT_STUDY_EVALUATOR_REGISTRY.validate_protocol(parsed.protocol)
    DEFAULT_STUDY_EXECUTION_REGISTRY.validate_protocol(parsed.protocol)

    changed = deepcopy(draft)
    next(item for item in changed["protocol"]["constraint_definitions"] if item["constraint_key"] == "target-state")["structured_evaluation_plan"]["vocabulary_terms"][0]["term_definition"] = "Different Exact Title"
    assert protocol_registration_hash(draft["study_key"], draft["title"], parsed.protocol) != protocol_registration_hash(
        changed["study_key"], changed["title"], StudyRegistrationInput.model_validate(changed).protocol
    )


def test_guided_and_worksheet_ui_state_the_scientific_boundary():
    studies = (ROOT / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static" / "studies.js").read_text(encoding="utf-8")
    app = (ROOT / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static" / "app.js").read_text(encoding="utf-8")
    assert "PLAYLIST-WIDE — require or forbid displayed Explicit" in studies
    assert "TARGET-SPECIFIC — observe Explicit state of one exact displayed track" in studies
    assert "Nothing is added, stripped, trimmed, case-folded, or normalized" in studies
    assert "FAIL is not Condition A prompt noncompliance" in studies
    assert "TARGET_ABSENT" in app and "TARGET_AMBIGUOUS" in app
    assert "Displayed-title identity evidence" in app and "Displayed-artist identity evidence" in app
    assert "No placement or Boolean observation was manufactured" in app
