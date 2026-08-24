from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from playlist_narrative_engine.maestro_workbench.server import MaestroWorkbenchServer
from playlist_narrative_engine.research_store.service import initialize_research_store


def _protocol(study_key="P2-TEST"):
    return {
        "study_key": study_key, "title": "P2 test study",
        "protocol": {
            "version_number": 1, "amendment_reason": None,
            "objective": "Test the operator surface.",
            "primary_hypothesis": "Treatment changes results.",
            "null_hypothesis": "Treatment does not change results.",
            "design_summary": "One planned test run.", "planned_sample_size": 1,
            "randomization_method": "Frozen order", "randomization_seed": "p2-seed",
            "operational_failure_policy": "Retry without consuming the run.",
            "operational_failure_consumes_run": False,
            "refusal_policy": "Refusal terminally realizes the run.",
            "missing_result_policy": "UNKNOWN is not imputed.",
            "conditions": [{"condition_key":"control","label":"Control","role":"CONTROL","exact_factor_definition":"No narrative addition."}],
            "blocks": [{"block_key":"b1","label":"Block 1","block_definition":"Exact count."}],
            "constraint_definitions": [{"constraint_key":"count","constraint_type":"exact_count","constraint_text":"Return exactly one track.","is_hard_constraint":True,"evaluation_rule":"Count observed placements.","permitted_result_provenance":"DIRECT_OBSERVATION","unknown_handling":"UNKNOWN is excluded."}],
            "outcome_definitions": [{"outcome_key":"primary","role":"PRIMARY","unit_of_analysis":"run","outcome_definition":"All hard constraints pass.","computation_rule":"All PASS.","missing_data_rule":"Exclude UNKNOWN.","refusal_handling":"Separate.","operational_failure_handling":"Exclude and retry."}],
            "analysis_definitions": [{"analysis_key":"a1","outcome_key":"primary","analysis_population":"Maestro outcomes","comparison_definition":"Report control.","aggregation_rule":"Raw count.","exclusion_rule":"Operational failures.","reporting_rule":"Report all states."}],
            "planned_runs": [{"run_key":"run-1","condition_key":"control","block_key":"b1","replicate_number":1,"randomized_ordinal":1,"planned_prompt_text":"Return exactly one track.","planned_source_system":"Maestro Beta","replacement_for_run_key":None,"applicable_constraint_keys":["count"]}],
        },
    }


class RunningWorkbench:
    def __init__(self, tmp_path):
        self.database_url = f"sqlite:///{(tmp_path / 'p2.db').as_posix()}"
        initialize_research_store(self.database_url)
        self.server = MaestroWorkbenchServer(("127.0.0.1", 0), database_url=self.database_url)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=5)

    def get(self, path):
        with urlopen(self.base + path) as response: return response.read(), response.headers

    def post(self, path, payload):
        request = Request(self.base + path, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}, method="POST")
        with urlopen(request) as response: return json.load(response)


def test_studies_resources_expose_separate_operator_surface(tmp_path):
    app = RunningWorkbench(tmp_path)
    try:
        html, _ = app.get("/studies.html"); script, headers = app.get("/studies.js"); main, _ = app.get("/")
        assert b"REGISTER AND LOCK PROTOCOL" in html
        assert b"Advanced Protocol Editor" in html and b"Planned Run Queue" in html
        assert b"Section 06" not in html and b"Study Evaluation" in html
        assert b"localStorage" in script and b"sessionStorage" in script
        assert b"renderEvaluationFailure" in script
        assert script.index(b'renderRuns(protocol)') < script.index(b'await jsonFetch(`/api/studies/${id}/evaluations/')
        assert b"Sections 04\xe2\x80\x9305 remain available" in script
        assert b"attach existing experiment" not in script.lower()
        assert b"Studies" in main
        assert headers["Cache-Control"] == "no-store"
    finally: app.close()


def test_studies_runtime_identity_handshake_exposes_serving_process_and_contract(tmp_path):
    app = RunningWorkbench(tmp_path)
    try:
        raw, headers = app.get("/api/runtime-identity")
        identity = json.loads(raw)
        assert identity["identity_version"] == 1
        assert identity["api_contract_version"] == "p8.1-runtime-identity-v1"
        assert identity["backend_module"].endswith("maestro_workbench\\server.py")
        assert identity["static_root"].endswith("maestro_workbench\\static")
        assert identity["study_contract_capabilities"] == [
            "study.constraint.structured_evaluation_plan",
            "study.protocol.execution_contract",
        ]
        assert len(identity["study_contract_sha256"]) == 64
        assert len(identity["studies_assets_sha256"]) == 64
        assert headers["Cache-Control"] == "no-store"
    finally:
        app.close()


def test_studies_ui_fails_closed_when_runtime_contract_is_missing(tmp_path):
    app = RunningWorkbench(tmp_path)
    try:
        html, _ = app.get("/studies.html")
        script, _ = app.get("/studies.js")
        assert b'id="runtime-identity"' in html
        assert b'id="guided-study" type="button" disabled' in html
        assert b'id="new-study" class="secondary" type="button" disabled' in html
        assert b'REQUIRED_STUDY_CAPABILITIES' in script
        assert b'EXPECTED_WORKBENCH_API_CONTRACT' in script
        assert b'WORKBENCH VERSION MISMATCH' in script
        assert b'Study creation and registration are disabled' in script
        assert b'verifyRuntimeIdentity()' in script
    finally:
        app.close()


def test_study_open_dependencies_are_independent_and_read_only(tmp_path):
    app = RunningWorkbench(tmp_path)
    try:
        registered = app.post("/api/studies/register", _protocol("P2-OPEN"))
        study_id = registered["id"]
        protocol_before, _ = app.get(f"/api/studies/{study_id}/protocols/1")

        study, _ = app.get(f"/api/studies/{study_id}")
        protocol, _ = app.get(f"/api/studies/{study_id}/protocols/1")
        assert json.loads(study)["study_key"] == "P2-OPEN"
        assert json.loads(protocol)["study_id"] == study_id

        evaluation, _ = app.get(f"/api/studies/{study_id}/evaluations/1")
        assert json.loads(evaluation)["study_id"] == study_id

        protocol_after, _ = app.get(f"/api/studies/{study_id}/protocols/1")
        assert protocol_after == protocol_before
    finally:
        app.close()


def test_study_validation_registration_list_and_readback_http_flow(tmp_path):
    app = RunningWorkbench(tmp_path)
    try:
        invalid = _protocol(); invalid["protocol"]["planned_sample_size"] = 2
        refused = app.post("/api/studies/validate", invalid)
        assert not refused["valid"] and refused["validation_issues"]
        valid = app.post("/api/studies/validate", _protocol())
        assert valid["valid"] and valid["canonical_proposal"]["study_key"] == "P2-TEST"
        registered = app.post("/api/studies/register", valid["canonical_proposal"])
        locked = registered["registered_protocol"]
        assert locked["version_number"] == 1 and len(locked["registration_hash"]) == 64
        assert locked["registered_at"]
        body, _ = app.get("/api/studies"); studies = json.loads(body)["studies"]
        assert studies[0]["planned_run_count"] == 1
        assert studies[0]["remaining_executable_run_count"] == 1
        protocol, _ = app.get(f"/api/studies/{registered['id']}/protocols/1")
        assert json.loads(protocol)["planned_runs"][0]["randomized_ordinal"] == 1
        evaluation, _ = app.get(f"/api/studies/{registered['id']}/evaluations/1")
        projection = json.loads(evaluation)
        assert projection["completion"]["planned_runs"] == 1
        assert not projection["completion"]["collection_complete"]
        assert projection["registration_hash"] == locked["registration_hash"]
        protocol_after, _ = app.get(f"/api/studies/{registered['id']}/protocols/1")
        assert json.loads(protocol_after) == json.loads(protocol)
        # No realized run means the exploratory surface correctly has no projection yet.
        try:
            app.get(f"/api/studies/{registered['id']}/explorations/1")
        except Exception as error:
            assert "404" in str(error)
    finally: app.close()


def test_operational_retry_then_atomic_experiment_realization_http_flow(tmp_path):
    app = RunningWorkbench(tmp_path)
    try:
        registered = app.post("/api/studies/register", _protocol())
        protocol = registered["registered_protocol"]
        run = protocol["planned_runs"][0]; definition = protocol["constraint_definitions"][0]
        attempt = app.post(f"/api/study-runs/{run['id']}/operational-attempts", {"failure_code":"NETWORK","notes":"No Maestro outcome."})
        assert attempt["attempt_number"] == 1 and not attempt["consumes_planned_run"]
        proposal = {
            "prompt": run["planned_prompt_text"], "source_system": run["planned_source_system"],
            "tracks": [{"position":1,"title":"Song","artist":"Artist"}],
            "constraints": [{"study_constraint_definition_id":definition["id"],"constraint_type":definition["constraint_type"],"constraint_text":definition["constraint_text"],"is_hard_constraint":definition["is_hard_constraint"],"result":{"status":"PASS","provenance_type":definition["permitted_result_provenance"]}}],
        }
        realized = app.post(f"/api/study-runs/{run['id']}/realize-experiment", {"proposal":proposal})
        assert realized["kind"] == "experiment"
        assert realized["record"]["prompt"] == run["planned_prompt_text"]
        assert realized["record"]["constraints"][0]["constraint_text"] == definition["constraint_text"]
        refreshed, _ = app.get(f"/api/studies/{registered['id']}/protocols/1")
        run_after = json.loads(refreshed)["planned_runs"][0]
        assert len(run_after["attempts"]) == 1
        assert run_after["realization"]["disposition"] == "EXPERIMENT_RECORDED"
        exploration, _ = app.get(f"/api/studies/{registered['id']}/explorations/1")
        explored = json.loads(exploration)
        assert explored["projection_type"] == "EXPLORATORY_READ_ONLY_STUDY_ANALYSIS"
        assert explored["study_id"] == registered["id"]
        unchanged, _ = app.get(f"/api/studies/{registered['id']}/protocols/1")
        assert json.loads(unchanged) == json.loads(refreshed)
        closeout, _ = app.get(f"/api/studies/{registered['id']}/closeouts/1")
        closed = json.loads(closeout)
        assert closed["report_type"] == "DERIVED_READ_ONLY_STUDY_CLOSEOUT"
        assert closed["registered_results"]["study_id"] == registered["id"]
        json_report, json_headers = app.get(f"/api/studies/{registered['id']}/closeouts/1/report.json")
        markdown_report, markdown_headers = app.get(f"/api/studies/{registered['id']}/closeouts/1/report.md")
        assert json.loads(json_report)["registered"]["registration_hash"] == protocol["registration_hash"]
        assert b"## REGISTERED RESULTS" in markdown_report
        assert "attachment" in json_headers["Content-Disposition"]
        assert "attachment" in markdown_headers["Content-Disposition"]
        final_protocol, _ = app.get(f"/api/studies/{registered['id']}/protocols/1")
        assert json.loads(final_protocol) == json.loads(refreshed)
    finally: app.close()


def test_maestro_refusal_is_terminal_without_experiment(tmp_path):
    app = RunningWorkbench(tmp_path)
    try:
        registered = app.post("/api/studies/register", _protocol("P2-REFUSAL"))
        run = registered["registered_protocol"]["planned_runs"][0]
        result = app.post(f"/api/study-runs/{run['id']}/failures", {"disposition":"MAESTRO_REFUSAL_RECORDED","failure":{"prompt":run["planned_prompt_text"],"source_system":run["planned_source_system"],"failure_type":"REFUSAL","displayed_message":"Try something else."}})
        assert result["disposition"] == "MAESTRO_REFUSAL_RECORDED"
        assert result["experiment_id"] is None and result["generation_failure_id"]
    finally: app.close()


def test_existing_nonstudy_proposal_builder_remains_constraint_optional():
    from playlist_narrative_engine.maestro_workbench.proposal_builder import build_governed_proposal
    proposal = build_governed_proposal("historical_experiment", {"prompt":"Ordinary","tracklist_completeness":"NOT_OBSERVED","tracks":[]}, [])
    assert proposal["constraints"] == []


def test_run_queue_exposes_deterministic_operator_execution_packet():
    script = Path("src/playlist_narrative_engine/maestro_workbench/static/studies.js").read_text(encoding="utf-8")

    assert "Execution and evidence checklist" in script
    assert "Submit this exact prompt once in a fresh generation." in script
    assert "Do not regenerate, edit, delete, or substitute the result." in script
    assert "Array.from(run.planned_prompt_text).length" in script
    assert "complete ordered tracklist, including playlist boundaries" in script
    assert "field-specific evidence link" in script
