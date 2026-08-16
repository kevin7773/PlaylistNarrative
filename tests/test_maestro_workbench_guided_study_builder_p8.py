from __future__ import annotations

import json
import hashlib
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_calculators import calculate_paired_difference


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static"
BUILDER = STATIC / "study_builder.js"


def _config(**changes):
    value = {
        "studyKey": "P7-SMOKE-1",
        "title": "Structured Evaluation End-to-End Smoke Test",
        "objective": "Verify prospective structured evaluation end to end.",
        "primaryHypothesis": "Explicit condition framing may change registered compliance.",
        "nullHypothesis": "Explicit condition framing does not change registered compliance.",
        "seed": "p7-smoke-1-seed",
        "sourceSystem": "Maestro Beta",
        "operationalPolicy": "Record non-consuming operational failures separately.",
        "refusalPolicy": "Record refusal as a terminal scientific disposition.",
        "missingPolicy": "Preserve missing and UNKNOWN without imputation.",
        "leftKey": "direct",
        "leftLabel": "Direct constraint",
        "leftFactor": "Base constraint only.",
        "rightKey": "framed",
        "rightLabel": "Narrative-framed constraint",
        "rightFactor": "Base constraint plus explicit framing.",
        "basePrompt": "Create a playlist of exactly 10 tracks.",
        "leftFraming": "",
        "rightFraming": "Frame the playlist around a sleepless nighttime narrative.",
        "blockCount": 1,
        "replicates": 1,
        "template": "exact_count",
        "expectedCount": 10,
        "expectedExplicit": False,
        "token": "night",
        "outcomeKind": "AUTO",
        "success": "PASS",
        "unknownPolicy": "NOT_CALCULABLE",
        "missingInputPolicy": "NOT_DERIVABLE",
        "refusalTreatment": "MISSING",
        "failureTreatment": "NOT_CALCULABLE",
        "direction": "RIGHT_MINUS_LEFT",
    }
    value.update(changes)
    return value


def _compile(config):
    script = (
        f"const b=require({json.dumps(str(BUILDER))});"
        f"b.compile({json.dumps(config)}).then(x=>console.log(JSON.stringify(x)))"
        ".catch(e=>{console.error(e);process.exit(1)});"
    )
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True,
        capture_output=True, text=True, timeout=15,
    )
    return json.loads(result.stdout)


def _compile_error(config):
    script = (
        f"const b=require({json.dumps(str(BUILDER))});"
        f"b.compile({json.dumps(config)}).then(()=>process.exit(0))"
        ".catch(e=>{console.error(e.message);process.exit(2)});"
    )
    return subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=False,
        capture_output=True, text=True, timeout=15,
    )


def _compile_without_subtle(config):
    script = (
        "Object.defineProperty(globalThis,'crypto',{value:{},configurable:true});"
        f"const b=require({json.dumps(str(BUILDER))});"
        f"b.compile({json.dumps(config)}).then(x=>console.log(JSON.stringify(x)))"
        ".catch(e=>{console.error(e);process.exit(1)});"
    )
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True,
        capture_output=True, text=True, timeout=15,
    )
    return json.loads(result.stdout)


def _nc3_config(**changes):
    value = _config(
        studyKey="NC-3-DRAFT",
        title="Exact Count Competition With Displayed Explicit Compliance",
        researchQuestion="Does adding an exact-count requirement reduce displayed no-Explicit compliance?",
        seed="nc-3-authoring-fixture",
        leftKey="condition-a",
        leftLabel="Explicit-only control",
        rightKey="condition-b",
        rightLabel="Explicit plus exact-count treatment",
        basePrompt="Create a playlist of upbeat pop and rock music suitable for listening while doing household chores.",
        leftFraming="Do not include any tracks tagged Explicit. Use only tracks that are not tagged Explicit.",
        rightFraming=(
            "Do not include any tracks tagged Explicit. Use only tracks that are not tagged Explicit.\n\n"
            "Generate exactly 10 tracks. The playlist must contain 10 tracks total, no more and no fewer."
        ),
        blockCount=1,
        direction="RIGHT_MINUS_LEFT",
        constraints=[
            {
                "constraintKey": "no-explicit",
                "template": "displayed_explicit",
                "applicability": "BOTH",
                "primary": True,
                "expectedExplicit": False,
                "aggregateBehavior": "ANY_VIOLATION_FAILS",
            },
            {
                "constraintKey": "exact-count-10",
                "template": "exact_count",
                "applicability": "CONDITION_B",
                "primary": False,
                "expectedCount": 10,
                "aggregateBehavior": "MIXED_PARTIAL",
            },
        ],
    )
    value.update(changes)
    return value


def _portable_digest(value: str, *, without_subtle: bool) -> str:
    setup = "Object.defineProperty(globalThis,'crypto',{value:{},configurable:true});" if without_subtle else ""
    script = setup + f"const b=require({json.dumps(str(BUILDER))});console.log(b.sha256({json.dumps(value)}));"
    return subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True,
        capture_output=True, text=True, timeout=15,
    ).stdout.strip()


def test_guided_and_advanced_entry_points_are_independent_and_ordered():
    html = (STATIC / "studies.html").read_text(encoding="utf-8")
    script = (STATIC / "studies.js").read_text(encoding="utf-8")
    assert 'id="guided-study"' in html and 'id="new-study"' in html
    assert "Guided Builder" in html and "Advanced Protocol Editor" in html
    assert html.index('src="/study_builder.js"') < html.index('src="/studies.js"')
    assert "openGuided" in script and "newDraft" in script
    assert "populateDraft" in script and "openGuidedAdvanced" in script


def test_exact_count_compiles_existing_p7_e1_contract_and_validates():
    draft = _compile(_config())
    validation = ResearchStoreService.validate_study_protocol(draft)
    assert validation.valid, validation.issues
    protocol = draft["protocol"]
    assert len(protocol["conditions"]) == 2
    assert [item["condition_key"] for item in protocol["conditions"]] == ["direct", "framed"]
    plan = protocol["constraint_definitions"][0]["structured_evaluation_plan"]
    assert plan["subject_kind"] == "RUN"
    assert plan["subject_selector"] == {"evaluator_key": "selector.run", "evaluator_version": "1"}
    assert plan["subject_evaluator"] == {"evaluator_key": "subject.integer_equals", "evaluator_version": "1"}
    assert plan["aggregate_evaluator"] == {"evaluator_key": "aggregate.single_subject", "evaluator_version": "1"}
    assert plan["measurement_definitions"][0]["derivation_key"] == "structural.placement_count"
    assert plan["measurement_definitions"][0]["unavailable_policy"] == "MUST_HAVE_VALUE"


def test_field_templates_use_only_frozen_registry_identities():
    explicit = _compile(_config(template="displayed_explicit"))
    lexical = _compile(_config(template="lexical_title", basePrompt="Create tracks whose displayed title contains night."))
    for draft, field, evaluator in (
        (explicit, "explicit_flag", "subject.boolean_equals"),
        (lexical, "display_title", "subject.lexical_standalone_token"),
    ):
        assert ResearchStoreService.validate_study_protocol(draft).valid
        plan = draft["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]
        assert plan["subject_kind"] == "PLACEMENT_FIELD"
        assert plan["subject_field"] == field
        assert plan["subject_evaluator"]["evaluator_key"] == evaluator
        assert plan["measurement_definitions"][0]["authority"] == "DIRECT_OBSERVATION"
        assert plan["measurement_definitions"][0]["evidence_required"] is True
    source = BUILDER.read_text(encoding="utf-8")
    assert "Billboard" not in source and "release date" not in source.lower()


def test_outcome_disposition_and_pairing_are_explicit_not_label_inferred():
    draft = _compile(_config(
        leftLabel="Treatment-looking label", rightLabel="Control-looking label",
        success="PASS_PARTIAL", unknownPolicy="EXCLUDE",
        refusalTreatment="NOT_CALCULABLE", failureTreatment="MISSING",
        direction="LEFT_MINUS_RIGHT",
    ))
    contract = draft["protocol"]["execution_contract"]
    outcome = contract["outcome_calculation_plans"][0]
    assert outcome["calculator_key"] == "outcome.constraint_status_rate"
    assert [item["text_value"] for item in outcome["parameters"] if item["parameter_key"] == "numerator_status"] == ["PASS", "PARTIAL"]
    assert [item["text_value"] for item in outcome["parameters"] if item["parameter_key"] == "denominator_status"] == ["PASS", "PARTIAL", "FAIL"]
    policies = {item["population_state"]: item["treatment"] for item in outcome["disposition_policies"]}
    assert policies == {
        "EXPERIMENT_RECORDED": "CALCULATE", "PENDING": "MISSING",
        "MAESTRO_REFUSAL_RECORDED": "NOT_CALCULABLE",
        "MAESTRO_FAILURE_RECORDED": "MISSING",
    }
    analysis = contract["analysis_calculation_plans"][0]
    assert analysis["condition_bindings"] == [
        {"comparison_role": "LEFT", "condition_key": "direct"},
        {"comparison_role": "RIGHT", "condition_key": "framed"},
    ]
    assert [(item["dimension_key"], item["ordinal"]) for item in analysis["dimensions"]] == [("BLOCK", 1), ("REPLICATE", 2)]
    assert next(item for item in analysis["parameters"] if item["parameter_key"] == "difference_direction")["text_value"] == "LEFT_MINUS_RIGHT"


def test_runs_sample_size_applicability_and_sha_order_are_deterministic():
    config = _config(blockCount=2, replicates=2)
    first = _compile(config)
    second = _compile(config)
    assert first == second
    protocol = first["protocol"]
    assert protocol["planned_sample_size"] == 8 == len(protocol["planned_runs"])
    assert sorted(item["randomized_ordinal"] for item in protocol["planned_runs"]) == list(range(1, 9))
    assert "SHA-256" in protocol["randomization_method"]
    constraints_by_block = {
        item["constraint_key"].split("-")[0]: item["constraint_key"]
        for item in protocol["constraint_definitions"]
    }
    assert all(item["applicable_constraint_keys"] == [constraints_by_block[item["block_key"]]] for item in protocol["planned_runs"])
    assert len({(item["block_key"], item["condition_key"], item["replicate_number"]) for item in protocol["planned_runs"]}) == 8


def test_twenty_replicates_generate_valid_protocol_and_twenty_registered_pairs():
    config = _config(blockCount=1, replicates=20, seed="twenty-replicate-seed")
    first = _compile(config)
    second = _compile(config)
    assert first == second
    validation = ResearchStoreService.validate_study_protocol(first)
    assert validation.valid, validation.issues

    protocol = first["protocol"]
    runs = protocol["planned_runs"]
    assert protocol["planned_sample_size"] == 40 == len(runs)
    assert sorted(item["randomized_ordinal"] for item in runs) == list(range(1, 41))
    assert len({(item["block_key"], item["condition_key"], item["replicate_number"]) for item in runs}) == 40
    for condition_key in ("direct", "framed"):
        assert sorted(item["replicate_number"] for item in runs if item["condition_key"] == condition_key) == list(range(1, 21))

    persisted_shape = deepcopy(protocol)
    persisted_shape["id"] = 81
    persisted_shape["registration_hash"] = "test-registration-hash"
    run_outcomes = {}
    for run_id, run in enumerate(persisted_shape["planned_runs"], start=1):
        run["id"] = run_id
        run["realization"] = {"id": 1000 + run_id}
        run_outcomes[run_id] = {
            "execution_state": "AVAILABLE",
            "derivability_state": "DERIVABLE",
            "calculation_state": "CALCULATED",
            "decimal_value": "1" if run["condition_key"] == "direct" else "0",
        }
    analysis_plan = deepcopy(persisted_shape["execution_contract"]["analysis_calculation_plans"][0])
    analysis_plan["id"] = 91
    analysis_plan["outcome_key"] = persisted_shape["analysis_definitions"][0]["outcome_key"]
    paired = calculate_paired_difference(analysis_plan, persisted_shape, run_outcomes)
    assert paired["calculation_state"] == "CALCULATED"
    assert paired["complete_pair_count"] == 20
    assert paired["valid_numeric_pair_count"] == 20
    assert len(paired["pairs"]) == 20
    assert not paired["invalid_or_incomplete_pairs"]


def test_asymmetric_multi_constraint_protocol_compiles_and_validates_authoritatively():
    draft = _compile(_nc3_config(replicates=1))
    validation = ResearchStoreService.validate_study_protocol(draft)
    assert validation.valid, validation.issues
    protocol = draft["protocol"]
    definitions = {item["constraint_key"]: item for item in protocol["constraint_definitions"]}
    assert set(definitions) == {"no-explicit", "exact-count-10"}

    runs = {item["condition_key"]: item for item in protocol["planned_runs"]}
    assert runs["condition-a"]["applicable_constraint_keys"] == ["no-explicit"]
    assert runs["condition-b"]["applicable_constraint_keys"] == ["no-explicit", "exact-count-10"]
    assert runs["condition-a"]["planned_prompt_text"] == (
        "Create a playlist of upbeat pop and rock music suitable for listening while doing household chores.\n\n"
        "Do not include any tracks tagged Explicit. Use only tracks that are not tagged Explicit."
    )
    assert runs["condition-b"]["planned_prompt_text"] == (
        "Create a playlist of upbeat pop and rock music suitable for listening while doing household chores.\n\n"
        "Do not include any tracks tagged Explicit. Use only tracks that are not tagged Explicit.\n\n"
        "Generate exactly 10 tracks. The playlist must contain 10 tracks total, no more and no fewer."
    )

    explicit = definitions["no-explicit"]["structured_evaluation_plan"]
    assert explicit["subject_kind"] == "PLACEMENT_FIELD"
    assert explicit["subject_field"] == "explicit_flag"
    assert explicit["subject_selector"] == {"evaluator_key": "selector.all_placements", "evaluator_version": "1"}
    assert explicit["subject_evaluator"] == {"evaluator_key": "subject.boolean_equals", "evaluator_version": "1"}
    assert explicit["aggregate_evaluator"] == {"evaluator_key": "aggregate.all_subjects_required", "evaluator_version": "1"}
    parameters = {item["parameter_key"]: item for item in explicit["parameters"]}
    assert parameters["expected"]["boolean_value"] is False
    assert parameters["mixed_status"]["text_value"] == "FAIL"
    assert parameters["all_fail_status"]["text_value"] == "FAIL"
    assert parameters["unknown_status"]["text_value"] == "UNKNOWN"

    count = definitions["exact-count-10"]["structured_evaluation_plan"]
    assert count["subject_kind"] == "RUN"
    assert count["measurement_definitions"][0]["derivation_key"] == "structural.placement_count"
    assert count["subject_evaluator"]["evaluator_key"] == "subject.integer_equals"
    assert count["aggregate_evaluator"]["evaluator_key"] == "aggregate.single_subject"
    assert next(item for item in count["parameters"] if item["parameter_key"] == "expected")["integer_value"] == 10

    assert len(protocol["outcome_definitions"]) == 1
    outcome = protocol["execution_contract"]["outcome_calculation_plans"][0]
    assert outcome["calculator_key"] == "outcome.constraint_status_rate"
    assert [item["constraint_key"] for item in outcome["constraint_bindings"]] == ["no-explicit"]
    assert len(protocol["analysis_definitions"]) == 1
    analysis = protocol["execution_contract"]["analysis_calculation_plans"][0]
    assert protocol["analysis_definitions"][0]["outcome_key"] == outcome["outcome_key"]
    assert next(item for item in analysis["parameters"] if item["parameter_key"] == "difference_direction")["text_value"] == "RIGHT_MINUS_LEFT"


def test_repeatable_single_constraint_preserves_legacy_template_semantics():
    for template, extra in (
        ("exact_count", {"expectedCount": 10}),
        ("displayed_explicit", {"expectedExplicit": False}),
        ("lexical_title", {"token": "night"}),
    ):
        legacy = _compile(_config(template=template, **extra))
        repeatable = _compile(_config(constraints=[{
            "constraintKey": f"b01-{template.replace('_', '-')}",
            "template": template,
            "applicability": "BOTH",
            "primary": True,
            "aggregateBehavior": "MIXED_PARTIAL",
            **extra,
        }]))
        legacy_definition = legacy["protocol"]["constraint_definitions"][0]
        repeatable_definition = repeatable["protocol"]["constraint_definitions"][0]
        assert repeatable_definition["structured_evaluation_plan"] == legacy_definition["structured_evaluation_plan"]
        assert repeatable["protocol"]["execution_contract"] == legacy["protocol"]["execution_contract"]
        assert [item["applicable_constraint_keys"] for item in repeatable["protocol"]["planned_runs"]] == [
            item["applicable_constraint_keys"] for item in legacy["protocol"]["planned_runs"]
        ]


def test_asymmetric_twenty_replicates_preserve_randomization_and_twenty_pairs():
    first = _compile(_nc3_config(replicates=20))
    second = _compile(_nc3_config(replicates=20))
    assert first == second
    assert ResearchStoreService.validate_study_protocol(first).valid
    protocol = first["protocol"]
    assert protocol["planned_sample_size"] == 40
    assert sorted(item["randomized_ordinal"] for item in protocol["planned_runs"]) == list(range(1, 41))
    assert len({(item["block_key"], item["condition_key"], item["replicate_number"]) for item in protocol["planned_runs"]}) == 40
    for condition in ("condition-a", "condition-b"):
        assert sorted(item["replicate_number"] for item in protocol["planned_runs"] if item["condition_key"] == condition) == list(range(1, 21))

    persisted = deepcopy(protocol)
    persisted["id"] = 88
    persisted["registration_hash"] = "fixture"
    outcomes = {}
    for run_id, run in enumerate(persisted["planned_runs"], start=1):
        run["id"] = run_id
        run["realization"] = {"id": 900 + run_id}
        outcomes[run_id] = {"execution_state": "AVAILABLE", "derivability_state": "DERIVABLE", "calculation_state": "CALCULATED", "decimal_value": "1"}
    analysis = deepcopy(persisted["execution_contract"]["analysis_calculation_plans"][0])
    analysis["id"] = 99
    analysis["outcome_key"] = persisted["analysis_definitions"][0]["outcome_key"]
    paired = calculate_paired_difference(analysis, persisted, outcomes)
    assert paired["complete_pair_count"] == 20
    assert paired["valid_numeric_pair_count"] == 20
    assert not paired["invalid_or_incomplete_pairs"]


@pytest.mark.parametrize(
    ("constraints", "message"),
    [
        ([], "At least one constraint is required."),
        ([{"constraintKey": "one", "template": "exact_count", "applicability": "BOTH", "primary": False}], "Exactly one primary outcome constraint is required."),
        ([{"constraintKey": "one", "template": "exact_count", "applicability": "BOTH", "primary": True}, {"constraintKey": "two", "template": "displayed_explicit", "applicability": "BOTH", "primary": True}], "Exactly one primary outcome constraint is required."),
        ([{"constraintKey": "one", "template": "displayed_explicit", "applicability": "CONDITION_B", "primary": True}], "The primary outcome constraint must apply to both compared conditions."),
        ([{"constraintKey": "same", "template": "displayed_explicit", "applicability": "BOTH", "primary": True}, {"constraintKey": "same", "template": "exact_count", "applicability": "CONDITION_B", "primary": False}], "Constraint keys must be unique."),
        ([{"constraintKey": "one", "template": "displayed_explicit", "applicability": "NONE", "primary": True}], "must apply to at least one condition"),
        ([{"constraintKey": "one", "template": "exact_count", "applicability": "BOTH", "primary": True, "aggregateBehavior": "ANY_VIOLATION_FAILS"}], "supported only for displayed Explicit constraints"),
        ([{"constraintKey": "one", "template": "displayed_explicit", "applicability": "BOTH", "primary": True, "aggregateBehavior": "UNSUPPORTED"}], "unsupported aggregation choice"),
    ],
)
def test_multi_constraint_authoring_rejects_invalid_intent(constraints, message):
    result = _compile_error(_nc3_config(constraints=constraints))
    assert result.returncode == 2
    assert message in result.stderr


def test_guided_replicate_range_preserves_one_and_two_and_rejects_out_of_range():
    assert _compile(_config(replicates=1))["protocol"]["planned_sample_size"] == 2
    assert _compile(_config(replicates=2))["protocol"]["planned_sample_size"] == 4
    source = BUILDER.read_text(encoding="utf-8")
    assert "replicates < 1 || replicates > 20" in source
    html = (STATIC / "studies.html").read_text(encoding="utf-8")
    options = html[html.index('id="guided-replicates"'):html.index("</select>", html.index('id="guided-replicates"'))]
    assert [f'value="{value}"' in options for value in range(1, 21)] == [True] * 20
    for invalid in (0, 21, 1.5):
        result = _compile_error(_config(replicates=invalid))
        assert result.returncode == 2
        assert "Replicates must be an integer from 1 through 20." in result.stderr


def test_guided_handoff_preserves_nested_contract_and_never_registers():
    script = (STATIC / "studies.js").read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    assert "generatedDraftBase.protocol.execution_contract" in script
    assert "structured_evaluation_plan" in builder
    guided_slice = script[script.index("const GUIDED_STEP_LABELS"):script.index("buildGroups();")]
    assert "/api/studies/register" not in guided_slice
    assert "/api/studies/validate" in guided_slice
    assert "REGISTER AND LOCK" not in builder
    html = (STATIC / "studies.html").read_text(encoding="utf-8")
    assert 'id="advanced-technical-json"' in html
    assert "JSON.stringify(draft,null,2)" in script


def test_multi_constraint_guided_handoff_preserves_nested_plans_and_applicability():
    draft = _compile(_nc3_config(replicates=1))
    protocol = draft["protocol"]
    assert [item["constraint_key"] for item in protocol["constraint_definitions"]] == ["no-explicit", "exact-count-10"]
    assert all(item["structured_evaluation_plan"] for item in protocol["constraint_definitions"])
    assert protocol["execution_contract"]["outcome_calculation_plans"][0]["constraint_bindings"] == [
        {"constraint_key": "no-explicit", "binding_role": "CONTRIBUTOR", "ordinal": 1}
    ]
    script = (STATIC / "studies.js").read_text(encoding="utf-8")
    assert "const prior=new Map((generatedDraftBase.protocol.constraint_definitions||[])" in script
    assert "protocol.execution_contract=generatedDraftBase.protocol.execution_contract" in script
    assert "item.applicable_constraint_keys.join(\", \")" in script
    assert "/api/studies/register" not in script[script.index("const GUIDED_STEP_LABELS"):script.index("buildGroups();")]


def test_multi_constraint_guided_ui_is_intent_oriented():
    html = (STATIC / "studies.html").read_text(encoding="utf-8")
    script = (STATIC / "studies.js").read_text(encoding="utf-8")
    constraint_step = html[html.index('data-guided-step="3"'):html.index('data-guided-step="4"')]
    assert "Add another rule" in constraint_step
    assert "which condition it applies to" in constraint_step
    assert "registry" not in constraint_step.lower()
    for label in ("Both conditions", "Condition A only", "Condition B only", "Primary comparison rule", "Any violating track fails the playlist"):
        assert label in script


def test_phone_width_progressive_disclosure_is_present():
    html = (STATIC / "studies.html").read_text(encoding="utf-8")
    styles = (STATIC / "styles.css").read_text(encoding="utf-8")
    assert html.count("data-guided-step=") == 7
    assert "Technical details" in html
    assert "guided-navigation" in html
    assert "@media (max-width: 640px)" in styles
    assert ".guided-steps" in styles and "overflow-x: auto" in styles


def test_advanced_edits_change_validation_input_without_silent_repair():
    script = (STATIC / "studies.js").read_text(encoding="utf-8")
    assert "input.addEventListener(\"input\", invalidate)" in script
    assert "Draft changed. Validate again." in script
    assert "Validation refused:" in script
    assert "generatedDraftBase" in script


def test_guided_builder_resource_is_served_before_app_with_no_cache(tmp_path):
    from test_maestro_workbench_studies_p2 import RunningWorkbench

    app = RunningWorkbench(tmp_path)
    try:
        html, html_headers = app.get("/studies.html")
        builder, builder_headers = app.get("/study_builder.js")
        assert html.index(b'src="/study_builder.js"') < html.index(b'src="/studies.js"')
        assert b"window.GuidedStudyBuilder = api" in builder
        assert "javascript" in builder_headers["Content-Type"].lower()
        assert html_headers["Cache-Control"] == "no-store"
        assert builder_headers["Cache-Control"] == "no-store"
    finally:
        app.close()


def test_p81_intent_only_dogfood_compiles_governed_valid_protocol():
    question = "Does adding a narrative instruction make Maestro less likely to satisfy an explicit playlist constraint?"
    config = _config(
        studyKey="NARRATIVE-COMPETITION-SMOKE-TEST",
        title="Narrative Competition Smoke Test",
        researchQuestion=question,
        objective="",
        primaryHypothesis="",
        nullHypothesis="",
        seed="",
        leftLabel="Constraint only",
        leftFactor="",
        rightLabel="Constraint plus narrative instruction",
        rightFactor="",
        basePrompt="Create a playlist of exactly 10 tracks.",
        leftFraming="",
        rightFraming="Consider this playlist part of a narrative.",
    )
    first = _compile(config)
    second = _compile(config)
    assert first == second
    assert ResearchStoreService.validate_study_protocol(first).valid
    protocol = first["protocol"]
    assert protocol["objective"].startswith("Prospectively evaluate the research question:")
    assert question in protocol["design_summary"]
    assert protocol["primary_hypothesis"] and protocol["null_hypothesis"]
    assert protocol["randomization_seed"].startswith("guided-")
    assert protocol["planned_sample_size"] == 2
    prompts = {item["condition_key"]: item["planned_prompt_text"] for item in protocol["planned_runs"]}
    assert prompts == {
        "direct": "Create a playlist of exactly 10 tracks.",
        "framed": "Create a playlist of exactly 10 tracks.\n\nConsider this playlist part of a narrative.",
    }
    assert sorted(item["randomized_ordinal"] for item in protocol["planned_runs"]) == [1, 2]


def test_p81_primary_flow_hides_protocol_jargon_and_generates_operator_defaults():
    html = (STATIC / "studies.html").read_text(encoding="utf-8")
    script = (STATIC / "studies.js").read_text(encoding="utf-8")
    primary_step = html[html.index('data-guided-step="1"'):html.index('data-guided-step="2"')]
    assert "What are you trying to learn?" in primary_step
    assert "Research question" in primary_step
    assert "Edit generated study language" in primary_step
    assert "Study governance details" in primary_step
    assert primary_step.index("Research question") < primary_step.index("Study governance details")
    assert 'id="guided-seed" readonly' in primary_step
    assert 'id="guided-source-system" value="Maestro Beta" readonly' in primary_step
    assert "safeStudyKey" in script and "syncIntentDefaults" in script
    assert "guidedLanguageEdited" in script


def test_p81_mobile_navigation_is_compact_and_has_no_horizontal_tab_dependency():
    html = (STATIC / "studies.html").read_text(encoding="utf-8")
    styles = (STATIC / "styles.css").read_text(encoding="utf-8")
    assert 'id="guided-mobile-progress"' in html
    mobile = styles[styles.index("@media (max-width: 640px)") :]
    assert ".guided-steps { display: none; }" in mobile
    assert ".guided-mobile-progress { display: grid;" in mobile
    assert "overflow-x: clip" in mobile
    assert ".guided-navigation button { flex: 1; }" in mobile
    assert ".guided-builder textarea.short { min-height: 104px; }" in mobile


def test_p81_review_keeps_technical_contract_secondary_and_advanced_handoff_intact():
    html = (STATIC / "studies.html").read_text(encoding="utf-8")
    script = (STATIC / "studies.js").read_text(encoding="utf-8")
    review = html[html.index('data-guided-step="7"'):html.index('class="guided-navigation"')]
    assert "Review exactly what will be registered and run." in review
    assert "Complete technical protocol" in review
    assert review.index('id="guided-review"') < review.index("Complete technical protocol")
    assert "Research question:" in script
    assert "planned runs in registered order" in script
    assert "openGuidedAdvanced" in script and "populateDraft(draft)" in script
    assert 'values[field] === null ? ""' in script


def test_p81_sha256_is_secure_origin_independent_and_matches_utf8_authority():
    values = [
        "ascii",
        "seed with spaces\nrun key",
        "punctuation !@#$%^&*()[]{}:;,.?",
        "Unicode café 夜 🎵",
        "guided-mstsi0zu\nb01-condition-b-r1",
    ]
    for value in values:
        expected = hashlib.sha256(value.encode("utf-8")).hexdigest()
        assert _portable_digest(value, without_subtle=False) == expected
        assert _portable_digest(value, without_subtle=True) == expected
    source = BUILDER.read_text(encoding="utf-8")
    assert "crypto.subtle" not in source


def test_p81_protocol_is_identical_when_crypto_subtle_is_unavailable():
    config = _config(
        researchQuestion="Does framing change exact-count compliance?",
        seed="fixed-lan-parity-seed",
        blockCount=2,
        replicates=2,
    )
    secure_context = _compile(config)
    insecure_lan_context = _compile_without_subtle(config)
    assert insecure_lan_context == secure_context
    secure_protocol = secure_context["protocol"]
    insecure_protocol = insecure_lan_context["protocol"]
    assert insecure_protocol["randomization_seed"] == secure_protocol["randomization_seed"]
    assert insecure_protocol["planned_runs"] == secure_protocol["planned_runs"]
    assert ResearchStoreService.validate_study_protocol(insecure_lan_context).valid


def test_p81_exact_phone_fixture_passes_authoritative_strict_validation():
    question = "Does adding a narrative instruction make Maestro less likely to satisfy an explicit playlist constraint?"
    draft = _compile(_config(
        studyKey="NARRATIVE-COMPETITION-SMOKE-TEST",
        title="Narrative Competition Smoke Test",
        researchQuestion=question,
        objective="",
        primaryHypothesis="",
        nullHypothesis="",
        seed="guided-phone-fixture",
        leftKey="condition-a",
        leftLabel="Constraint only",
        leftFactor="",
        rightKey="condition-b",
        rightLabel="Constraint plus narrative instruction",
        rightFactor="",
        basePrompt="Create a playlist of exactly 10 tracks.",
        leftFraming="",
        rightFraming="Frame the playlist as the soundtrack to a late-night road trip.",
        blockCount=1,
        replicates=1,
        template="exact_count",
        expectedCount=10,
    ))
    validation = ResearchStoreService.validate_study_protocol(draft)
    assert validation.valid, validation.issues
    protocol = draft["protocol"]
    prompts = {item["condition_key"]: item["planned_prompt_text"] for item in protocol["planned_runs"]}
    assert prompts["condition-a"] == "Create a playlist of exactly 10 tracks."
    assert prompts["condition-b"] == (
        "Create a playlist of exactly 10 tracks.\n\n"
        "Frame the playlist as the soundtrack to a late-night road trip."
    )
    assert protocol["constraint_definitions"][0]["structured_evaluation_plan"]
    assert protocol["execution_contract"]["outcome_calculation_plans"]
    assert protocol["execution_contract"]["analysis_calculation_plans"]


def test_p81_validation_errors_render_backend_location_paths():
    issue = {
        "location": ["protocol", "constraint_definitions", 0, "structured_evaluation_plan"],
        "message": "Extra inputs are not permitted",
    }
    script = (
        f"const b=require({json.dumps(str(BUILDER))});"
        f"console.log(b.formatValidationIssue({json.dumps(issue)}));"
    )
    rendered = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True,
        capture_output=True, text=True, timeout=15,
    ).stdout.strip()
    assert rendered == (
        "protocol.constraint_definitions[0].structured_evaluation_plan: "
        "Extra inputs are not permitted"
    )


def test_p81_advanced_handoff_uses_multiline_safe_prompt_control():
    script = (STATIC / "studies.js").read_text(encoding="utf-8")
    assert 'field === "planned_prompt_text"' in script
    assert '<textarea class="short" data-field="${field}"' in script
