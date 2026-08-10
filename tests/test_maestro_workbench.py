from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from playlist_narrative_engine.maestro_workbench.operations import (
    EvidenceStager,
    WorkbenchOperations,
)
from playlist_narrative_engine.maestro_workbench.proposal_builder import (
    build_governed_proposal,
)
from playlist_narrative_engine.maestro_workbench.server import (
    MaestroWorkbenchServer,
    STATIC_ROOT,
    resolve_launch_mode,
    startup_lines,
)
from playlist_narrative_engine.maestro_workbench.track_extraction import (
    DelimitedTextTrackExtractionAdapter,
    DraftTrackGenerationError,
    StructuredJsonDraftTrackProvider,
    UnavailableTrackExtractionAdapter,
    generate_draft_tracks,
)
from playlist_narrative_engine.research_store.service import (
    initialize_research_store,
    open_research_store_service,
)


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'research.db').as_posix()}"


def test_evidence_staging_preserves_bytes_filename_and_sha256(tmp_path) -> None:
    content = b"exact screenshot bytes"

    staged = EvidenceStager(tmp_path / "staging").stage("capture.png", content)

    assert staged.original_filename == "capture.png"
    assert staged.size_bytes == len(content)
    assert staged.sha256 == hashlib.sha256(content).hexdigest()
    assert open(staged.local_path, "rb").read() == content


def test_validation_is_read_only_and_uses_governed_schema(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    with open_research_store_service(database_url) as service:
        operations = WorkbenchOperations(service)

        invalid = operations.validate("historical_experiment", {
            "tracklist_completeness": "COMPLETE", "tracks": []
        })
        valid = operations.validate("historical_experiment", {
            "prompt": "Exact prompt",
            "tracklist_completeness": "NOT_OBSERVED",
            "tracks": [],
        })

        assert not invalid["valid"]
        assert invalid["validation_issues"]
        assert valid == {
            "valid": True,
            "validation_issues": [],
            "evidence_valid": True,
            "evidence_issues": [],
        }
        assert service.get_experiment(1) is None


def test_ingestion_is_explicit_single_record_and_returns_projection(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    with open_research_store_service(database_url) as service:
        operations = WorkbenchOperations(service)
        proposal = {
            "prompt": "Exact prompt",
            "tracklist_completeness": "NOT_OBSERVED",
            "tracks": [],
        }

        preview = operations.validate("historical_experiment", proposal)
        assert preview["valid"]
        assert service.get_experiment(1) is None

        result = operations.ingest("historical_experiment", proposal)

        assert result["kind"] == "experiment"
        assert result["record_id"] == 1
        assert result["record"] == service.get_experiment(1)


def test_current_artifact_uses_separate_governed_path(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    with open_research_store_service(database_url) as service:
        result = WorkbenchOperations(service).ingest(
            "current_persisted_artifact",
            {
                "persistence_state": "UNKNOWN",
                "tracklist_completeness": "NOT_OBSERVED",
            },
        )

        assert result["kind"] == "persisted_artifact"
        assert result["record"]["persistence_state"] == "UNKNOWN"


def test_recovery_leads_and_batch_kinds_are_not_supported(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    with open_research_store_service(database_url) as service:
        operations = WorkbenchOperations(service)

        with pytest.raises(ValueError, match="unsupported workbench proposal kind"):
            operations.validate("recovery_lead", {})
        with pytest.raises(ValueError, match="unsupported workbench proposal kind"):
            operations.validate("batch", [])


def test_structured_builder_copies_only_explicit_declarations() -> None:
    proposal = build_governed_proposal(
        "historical_experiment",
        {
            "prompt": "Exact prompt",
            "source_system": "Maestro Beta",
            "tracklist_completeness": "NOT_OBSERVED",
            "evidence_standard": "RECOVERED_HISTORICAL",
            "tracks": [],
            "top_level_evidence": [
                {"source_key": "source_1", "field_name": "prompt", "provenance_type": "DIRECT_OBSERVATION"},
                {"source_key": "source_1", "field_name": "source_system", "provenance_type": "DIRECT_OBSERVATION"},
                {"source_key": "source_1", "field_name": "tracklist_completeness", "provenance_type": "HUMAN_ASSESSMENT"},
            ],
        },
        [{
            "source_type": "SCREENSHOT",
            "source_reference": "Phone capture 1",
            "original_filename": "capture.png",
            "local_path": "staging/capture.png",
            "sha256": "a" * 64,
            "size_bytes": 42,
        }],
    )

    assert proposal["prompt"] == "Exact prompt"
    assert proposal["segments"] == []
    assert proposal["tracks"] == []
    assert proposal["evidence_sources"] == [{
        "source_key": "source_1",
        "source_type": "SCREENSHOT",
        "source_reference": "Phone capture 1",
        "original_filename": "capture.png",
        "local_path": "staging/capture.png",
        "sha256": "a" * 64,
    }]
    assert [link["field_name"] for link in proposal["evidence"]] == [
        "prompt", "source_system", "tracklist_completeness",
    ]


def test_structured_builder_accepts_explicit_non_file_evidence_source() -> None:
    proposal = build_governed_proposal(
        "historical_experiment",
        {
            "prompt": "Exact prompt",
            "tracklist_completeness": "NOT_OBSERVED",
            "evidence_standard": "RECOVERED_HISTORICAL",
            "tracks": [],
            "top_level_evidence": [{
                "source_key": "source_1",
                "field_name": "prompt",
                "provenance_type": "HUMAN_ASSESSMENT",
                "support_status": "FULL",
            }, {
                "source_key": "source_1",
                "field_name": "tracklist_completeness",
                "provenance_type": "HUMAN_ASSESSMENT",
                "support_status": "FULL",
            }],
        },
        [{
            "source_type": "CONVERSATION_USER_STATEMENT",
            "source_reference": "workbench:operator-prompt-attestation",
            "notes": "Explicit operator declaration.",
        }],
    )

    assert proposal["evidence_sources"] == [{
        "source_key": "source_1",
        "source_type": "CONVERSATION_USER_STATEMENT",
        "source_reference": "workbench:operator-prompt-attestation",
        "notes": "Explicit operator declaration.",
    }]
    assert proposal["evidence"][0] == {
        "source_key": "source_1",
        "field_name": "prompt",
        "provenance_type": "HUMAN_ASSESSMENT",
        "support_status": "FULL",
    }


def test_structured_builder_requires_explicit_declarations() -> None:
    with pytest.raises(ValueError, match="tracklist_completeness"):
        build_governed_proposal("historical_experiment", {"tracks": []}, [])

    with pytest.raises(ValueError, match="source_type"):
        build_governed_proposal(
            "historical_experiment",
            {"tracklist_completeness": "NOT_OBSERVED", "tracks": []},
            [{"source_reference": "capture", "original_filename": "x.png", "local_path": "x.png", "sha256": "a" * 64}],
        )


def test_track_extraction_adapters_produce_drafts_without_authority() -> None:
    unavailable_provider = UnavailableTrackExtractionAdapter()
    assert not unavailable_provider.available()
    unavailable = generate_draft_tracks(unavailable_provider, ("source_1",))
    assert not unavailable.available
    assert unavailable.draft_tracks == ()

    delimited_provider = DelimitedTextTrackExtractionAdapter()
    assert delimited_provider.available()
    extracted = delimited_provider.generate(
        ("source_1", "source_2"),
        "1 | First title | First artist | Remastered\n2 | Second title | Second artist |",
    )

    assert extracted.available
    assert extracted.draft_tracks[0].proposed_position == 1
    assert extracted.draft_tracks[0].proposed_version_remaster_text == "Remastered"
    assert extracted.draft_tracks[0].source_keys == ("source_1", "source_2")
    assert extracted.draft_tracks[0].review_status == "UNREVIEWED"


def test_available_provider_failure_is_distinct_from_unavailable_capability() -> None:
    class FailingProvider:
        provider = "failing"

        def available(self) -> bool:
            return True

        def generate(self, source_keys, supplied_text=None):
            raise RuntimeError("vision process exited")

    with pytest.raises(DraftTrackGenerationError, match="vision process exited"):
        generate_draft_tracks(FailingProvider(), ("source_1",))


def test_structured_json_import_preserves_order_values_uncertainty_and_sources() -> None:
    imported = generate_draft_tracks(
        StructuredJsonDraftTrackProvider(),
        ("source_1", "source_2"),
        json.dumps({"tracks": [
            {"position": 7, "title": "  Exact title  ", "artist": "Artist A", "version": None,
             "uncertain": True, "source_keys": ["source_2", "source_1"]},
            {"position": 2, "title": "Second", "artist": None, "version": "Live", "uncertain": False},
        ]}),
    )

    assert imported.available
    assert [item.proposed_position for item in imported.draft_tracks] == [7, 2]
    assert imported.draft_tracks[0].proposed_title == "  Exact title  "
    assert imported.draft_tracks[0].ambiguity_flag is True
    assert imported.draft_tracks[0].source_keys == ("source_2", "source_1")
    assert imported.draft_tracks[1].source_keys == ()
    assert imported.draft_tracks[1].proposed_version_remaster_text == "Live"


@pytest.mark.parametrize("document, message", [
    ("not json", "invalid JSON"),
    (json.dumps([]), "object containing only a tracks array"),
    (json.dumps({"tracks": [{}]}), "at track 1: title, artist, or version is required"),
    (json.dumps({"tracks": [{"title": "Title", "uncertain": "maybe"}]}), "uncertain must be true or false"),
    (json.dumps({"tracks": [{"title": "Title", "source_keys": ["missing"]}]}), "unknown staged sources"),
    (json.dumps({"tracks": [{"title": "Title", "invented": 1}]}), "unsupported fields"),
])
def test_structured_json_import_rejects_invalid_documents_without_repair(document, message) -> None:
    with pytest.raises(ValueError, match=message):
        generate_draft_tracks(StructuredJsonDraftTrackProvider(), ("source_1",), document)


def test_structured_json_import_accepts_forty_unassigned_external_drafts() -> None:
    tracks = [
        {
            "position": position,
            "title": "Chandelier" if position == 1 else f"Track {position}",
            "artist": "Sia" if position == 1 else f"Artist {position}",
            "version": None,
            "uncertain": False,
        }
        for position in range(1, 41)
    ]

    imported = generate_draft_tracks(
        StructuredJsonDraftTrackProvider(),
        ("source_1", "source_2"),
        json.dumps({"tracks": tracks}),
    )

    assert len(imported.draft_tracks) == 40
    assert all(track.source_keys == () for track in imported.draft_tracks)
    assert imported.draft_tracks[0].proposed_title == "Chandelier"
    assert imported.message == "Imported 40 draft tracks. Review the list before confirmation."


def test_frontend_generation_flow_terminates_every_busy_state() -> None:
    controller = (
        Path(__file__).parents[1]
        / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static" / "draft_generation.js"
    )
    script = r'''
const flow = require(process.argv[1]);
function ui() { return {button: {textContent: "Generate draft tracklist", disabled: false}, status: {textContent: ""}}; }
async function main() {
  const unavailableUi = ui();
  const unavailableDrafts = [];
  let unavailableBusy = false;
  const unavailable = await flow.run({
    ...unavailableUi,
    loadingText: "Generating draft tracklist",
    invoke: async () => {
      unavailableBusy = unavailableUi.button.disabled && unavailableUi.status.textContent === "Generating draft tracklist…";
      return {available: false, provider: "automatic", message: "No provider. No draft tracks have been created.", draft_tracks: []};
    },
    acceptDrafts: rows => unavailableDrafts.push(...rows)
  });

  const availableUi = ui();
  const availableDrafts = [];
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  const availableRun = flow.run({
    ...availableUi,
    loadingText: "Generating draft tracklist",
    invoke: () => pending,
    acceptDrafts: rows => availableDrafts.push(...rows)
  });
  const availableBusy = availableUi.button.disabled && availableUi.status.textContent === "Generating draft tracklist…";
  release({available: true, provider: "future", message: "1 draft track generated.", draft_tracks: [{title: "Draft"}]});
  await availableRun;

  async function failure(message, value) {
    const state = ui();
    try {
      await flow.run({...state, loadingText: "Generating draft tracklist", invoke: async () => value instanceof Error ? Promise.reject(value) : value, acceptDrafts: () => {}});
    } catch (_) {}
    return {disabled: state.button.disabled, label: state.button.textContent, status: state.status.textContent};
  }
  const providerFailure = await failure("provider", new Error("provider failed"));
  const networkFailure = await failure("network", new Error("network unavailable"));
  const malformed = await failure("malformed", {available: true});

  process.stdout.write(JSON.stringify({
    unavailable: {busy: unavailableBusy, disabled: unavailableUi.button.disabled, label: unavailableUi.button.textContent, status: unavailableUi.status.textContent, rows: unavailableDrafts.length, available: unavailable.available},
    available: {busy: availableBusy, disabled: availableUi.button.disabled, label: availableUi.button.textContent, status: availableUi.status.textContent, rows: availableDrafts.length},
    providerFailure, networkFailure, malformed
  }));
}
main();
'''
    completed = subprocess.run(
        ["node", "-e", script, str(controller)],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["unavailable"] == {
        "busy": True,
        "disabled": False,
        "label": "Generate draft tracklist",
        "status": "No provider. No draft tracks have been created.",
        "rows": 0,
        "available": False,
    }
    assert result["available"] == {
        "busy": True,
        "disabled": False,
        "label": "Generate draft tracklist",
        "status": "1 draft track generated.",
        "rows": 1,
    }
    assert "provider failed" in result["providerFailure"]["status"]
    assert "network unavailable" in result["networkFailure"]["status"]
    assert "malformed response" in result["malformed"]["status"]
    for outcome in ("providerFailure", "networkFailure", "malformed"):
        assert result[outcome]["disabled"] is False
        assert result[outcome]["label"] == "Generate draft tracklist"


def test_confirmed_track_shape_supports_version_and_multiple_explicit_sources() -> None:
    staged = [
        {"source_type": "SCREENSHOT", "source_reference": f"Screenshot {number}",
         "original_filename": f"{number}.png", "local_path": f"staging/{number}.png",
         "sha256": str(number) * 64}
        for number in (1, 2)
    ]
    proposal = build_governed_proposal(
        "historical_experiment",
        {
            "tracklist_completeness": "PARTIAL",
            "captures_playlist_start": "YES",
            "captures_playlist_end": "UNKNOWN",
            "tracks": [{
                "absolute_position": 1,
                "title": "Visible title",
                "artist": "Visible artist",
                "version_or_remaster_text": "Remastered",
                "source_keys": ["source_1", "source_2"],
                "canonical_identity_established": False,
                "provenance_type": "DIRECT_OBSERVATION",
            }],
        },
        staged,
    )

    track = proposal["tracks"][0]
    assert track["version_or_remaster_text"] == "Remastered"
    assert {link["source_key"] for link in track["evidence"]} == {"source_1", "source_2"}
    assert len(track["evidence"]) == 8


def test_static_workbench_requires_review_confirmation_before_proposal_build() -> None:
    root = Path(__file__).parents[1] / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static"
    html = (root / "index.html").read_text(encoding="utf-8")
    javascript = (root / "app.js").read_text(encoding="utf-8")
    generation_javascript = (root / "draft_generation.js").read_text(encoding="utf-8")

    assert "Generate draft tracklist" in html
    assert "Import draft tracklist" in html
    assert "Confirm reviewed tracklist" in html
    assert "Review status" not in html
    assert html.index("Generate draft tracklist") < html.index("Advanced tracklist tools")
    assert html.index('src="/draft_generation.js"') < html.index('src="/app.js"')
    assert 'PneDraftGenerationPublication = {state: "awaiting-script"}' in html
    assert 'PneDraftGenerationPublication.state = "load-failed"' in html
    assert 'PneDraftGenerationPublication.state = "execution-failed"' in html
    assert 'window.DraftGenerationFlow = api' in generation_javascript
    assert 'PneDraftGenerationPublication.state = "published"' in generation_javascript
    assert 'dataset.draftGenerationPublication = "published"' in generation_javascript
    assert 'const draftGenerationFlow = window.DraftGenerationFlow' not in javascript
    assert "function resolveDraftGenerationFlow()" in javascript
    assert "function initializeDraftTrackWorkflow()" in javascript
    assert "initializeDraftTrackWorkflow();" in javascript
    assert "draftGenerationFlow.run" in javascript
    assert "DraftGenerationFlow.run" not in javascript
    assert "stagedEvidence.map((item, index) => `source_${index + 1}`)" in javascript
    assert "Generating draft tracklist" in javascript
    assert "The provider request timed out" in javascript
    assert "Restart it to load the current generation provider route" in javascript
    assert "Workbench initialization failed: draft-track workflow unavailable." in javascript
    assert "confirmedTracks" in javascript
    assert 'generateDraft("structured_json"' not in javascript
    assert 'addEventListener("click", event => importDraftTracklist(draftGenerationFlow, event))' in javascript
    assert "Draft import failed:" in javascript
    assert 'status.textContent = message' in javascript
    assert "invalidateConfirmation();" in javascript
    assert 'tracks: completeness === "NOT_OBSERVED" ? [] : tracksWithCoverage()' in javascript
    assert "function readinessIssues()" in javascript
    assert "function validateProposal()" in javascript
    assert "function ingestProposal()" in javascript
    assert "Confirm the reviewed tracklist before building a proposal" in javascript
    assert 'window.confirm("Ingest exactly this one reviewed record?")' in javascript


def test_draft_generation_explicitly_exports_browser_global() -> None:
    script_path = (
        Path(__file__).parents[1]
        / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static" / "draft_generation.js"
    )
    script = r'''
const fs = require("fs");
const vm = require("vm");
const browser = {window: {}};
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), browser);
process.stdout.write(JSON.stringify({
  defined: typeof browser.window.DraftGenerationFlow === "object",
  run: typeof browser.window.DraftGenerationFlow?.run,
  validate: typeof browser.window.DraftGenerationFlow?.validateResult
}));
'''
    completed = subprocess.run(
        ["node", "-e", script, str(script_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {"defined": True, "run": "function", "validate": "function"}


def test_workbench_initialization_fails_closed_when_draft_generation_dependency_is_absent() -> None:
    script_path = (
        Path(__file__).parents[1]
        / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static" / "app.js"
    )
    script = r'''
const fs = require("fs");
const vm = require("vm");

class FakeClassList {
  add() {}
  remove() {}
}

class FakeElement {
  constructor(value = "") {
    this.value = value;
    this.textContent = "";
    this.innerHTML = "";
    this.disabled = false;
    this.hidden = false;
    this.multiple = false;
    this.selectedOptions = [];
    this.files = [];
    this.listeners = {};
    this.children = [];
    this.classList = new FakeClassList();
    this.dataset = {};
  }
  addEventListener(type, handler) {
    (this.listeners[type] ||= []).push(handler);
  }
  querySelector(selector) {
    if (selector === ".empty") return null;
    return new FakeElement();
  }
  querySelectorAll() {
    return [];
  }
  append(child) {
    this.children.push(child);
  }
}

function buildEnvironment() {
  const selectors = new Map();
  function element(selector, value = "") {
    const node = new FakeElement(value);
    selectors.set(selector, node);
    return node;
  }
  element("#kind", "historical_experiment");
  element("#proposal");
  element("#result");
  element("#staged");
  element("#completeness", "NOT_OBSERVED");
  element("#historical-fields");
  element("#artifact-fields");
  element("#confirmed-summary");
  element("#stage");
  element("#generate-tracks");
  element("#import-draft");
  element("#load-draft");
  element("#structured-draft-file");
  element("#add-draft");
  element("#merge-drafts");
  element("#confirm-tracks");
  element("#add-link");
  element("#build");
  element("#validate");
  element("#ingest");
  element("#evidence-files");
  element("#draft-text");
  const draftSources = element("#draft-sources");
  draftSources.multiple = true;
  element("#extraction-status");
  element("#import-status");
  element("#structured-draft");
  element("#draft-tracks");
  element("#overlap-suggestions");
  element("#raw-draft");
  for (const selector of ["#track-coverage", "#readiness", "#stage-status", "#build-status", "#validation-status", "#ingest-status", "#readback-summary", "#apply-source-type", "#bulk-source-type", "#evidence-standard", "#captures-start", "#captures-end", "#evidence-provenance", "#evidence-support", "#source-system", "#prompt", "#prompt-attested", "#generated-title", "#generated-description", "#notes"]) element(selector);

  const boundaryFields = [new FakeElement(), new FakeElement()];
  const document = {
    querySelector(selector) {
      const node = selectors.get(selector);
      if (!node) throw new Error(`Missing selector ${selector}`);
      return node;
    },
    querySelectorAll(selector) {
      if (selector === ".boundary-field") return boundaryFields;
      if (selector === "#draft-tracks .draft-row") return [];
      return [];
    },
    createElement() {
      return new FakeElement();
    },
  };

  const window = {
    location: {search: ""},
    confirm: () => true,
    setTimeout,
    clearTimeout,
  };

  return {selectors, document, window};
}

const env = buildEnvironment();
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), {
  window: env.window,
  document: env.document,
  URLSearchParams,
  AbortController,
  fetch: async () => { throw new Error("fetch should not run"); },
  console,
  HTMLSelectElement: FakeElement,
});

const result = {
  generateDisabled: env.selectors.get("#generate-tracks").disabled,
  importDisabled: env.selectors.get("#import-draft").disabled,
  loadDisabled: env.selectors.get("#load-draft").disabled,
  extractionStatus: env.selectors.get("#extraction-status").textContent,
  importStatus: env.selectors.get("#import-status").textContent,
  resultText: env.selectors.get("#result").textContent,
  generateListeners: (env.selectors.get("#generate-tracks").listeners.click || []).length,
  importListeners: (env.selectors.get("#import-draft").listeners.click || []).length,
  loadListeners: (env.selectors.get("#load-draft").listeners.click || []).length,
};
process.stdout.write(JSON.stringify(result));
'''
    completed = subprocess.run(
        ["node", "-e", script, str(script_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {
        "generateDisabled": True,
        "importDisabled": True,
        "loadDisabled": True,
        "extractionStatus": "Workbench initialization failed: draft-track workflow unavailable.",
        "importStatus": "Workbench initialization failed: draft-track workflow unavailable.",
        "resultText": json.dumps({"error": "Workbench initialization failed: draft-track workflow unavailable."}, indent=2),
        "generateListeners": 0,
        "importListeners": 0,
        "loadListeners": 0,
    }


def test_workbench_initialization_captures_draft_generation_dependency_and_preserves_import_errors() -> None:
    generation_script_path = (
        Path(__file__).parents[1]
        / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static" / "draft_generation.js"
    )
    app_script_path = (
        Path(__file__).parents[1]
        / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static" / "app.js"
    )
    script = r'''
const fs = require("fs");
const vm = require("vm");

class FakeClassList {
  add() {}
  remove() {}
}

class FakeElement {
  constructor(value = "") {
    this.value = value;
    this.textContent = "";
    this.innerHTML = "";
    this.disabled = false;
    this.hidden = false;
    this.multiple = false;
    this.selectedOptions = [];
    this.files = [];
    this.listeners = {};
    this.children = [];
    this.classList = new FakeClassList();
    this.dataset = {};
  }
  addEventListener(type, handler) {
    (this.listeners[type] ||= []).push(handler);
  }
  async trigger(type, event = {preventDefault() {}}) {
    for (const handler of this.listeners[type] || []) {
      await handler(event);
    }
  }
  querySelector(selector) {
    if (selector === ".empty") return null;
    return new FakeElement();
  }
  querySelectorAll() {
    return [];
  }
  append(child) {
    this.children.push(child);
  }
}

function buildEnvironment() {
  const selectors = new Map();
  function element(selector, value = "") {
    const node = new FakeElement(value);
    selectors.set(selector, node);
    return node;
  }
  element("#kind", "historical_experiment");
  element("#proposal");
  element("#result");
  element("#staged");
  element("#completeness", "NOT_OBSERVED");
  element("#historical-fields");
  element("#artifact-fields");
  element("#confirmed-summary");
  element("#stage");
  element("#generate-tracks");
  element("#import-draft");
  element("#load-draft");
  element("#structured-draft-file");
  element("#add-draft");
  element("#merge-drafts");
  element("#confirm-tracks");
  element("#add-link");
  element("#build");
  element("#validate");
  element("#ingest");
  element("#evidence-files");
  element("#draft-text", "1 | Track | Artist |");
  const draftSources = element("#draft-sources");
  draftSources.multiple = true;
  draftSources.selectedOptions = [];
  element("#extraction-status");
  element("#import-status");
  element("#structured-draft", '{"tracks":[{"position":1,"title":"Imported","artist":"Artist","version":null,"uncertain":false}]}');
  element("#draft-tracks");
  element("#overlap-suggestions");
  element("#raw-draft");
  for (const selector of ["#track-coverage", "#readiness", "#stage-status", "#build-status", "#validation-status", "#ingest-status", "#readback-summary", "#apply-source-type", "#bulk-source-type", "#evidence-standard", "#captures-start", "#captures-end", "#evidence-provenance", "#evidence-support", "#source-system", "#prompt", "#prompt-attested", "#generated-title", "#generated-description", "#notes"]) element(selector);

  const boundaryFields = [new FakeElement(), new FakeElement()];
  const document = {
    querySelector(selector) {
      const node = selectors.get(selector);
      if (!node) throw new Error(`Missing selector ${selector}`);
      return node;
    },
    querySelectorAll(selector) {
      if (selector === ".boundary-field") return boundaryFields;
      if (selector === "#draft-tracks .draft-row") return [];
      return [];
    },
    createElement() {
      return new FakeElement();
    },
  };

  const window = {
    location: {search: ""},
    confirm: () => true,
    setTimeout,
    clearTimeout,
  };

  return {selectors, document, window};
}

async function main() {
  const env = buildEnvironment();
  const responses = [
    {
      ok: true,
      status: 200,
      body: {available: true, provider: "structured_json", message: "Imported 0 draft tracks. Review the list before confirmation.", draft_tracks: []},
    },
    {
      ok: false,
      status: 400,
      body: {error: "invalid JSON"},
    },
  ];
  const fetchCalls = [];
  const fetch = async (path, options) => {
    fetchCalls.push({path, body: JSON.parse(options.body)});
    const next = responses.shift();
    return {
      ok: next.ok,
      status: next.status,
      headers: {get: () => "application/json"},
      async json() { return next.body; },
    };
  };

  const context = {
    window: env.window,
    document: env.document,
    URLSearchParams,
    AbortController,
    fetch,
    console,
    HTMLSelectElement: FakeElement,
  };

  vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), context);
  vm.runInNewContext(fs.readFileSync(process.argv[2], "utf8"), context);

  const importButton = env.selectors.get("#import-draft");
  env.window.DraftGenerationFlow = undefined;
  await importButton.trigger("click");
  const successfulImport = {
    importDisabled: importButton.disabled,
    importStatus: env.selectors.get("#import-status").textContent,
    resultText: env.selectors.get("#result").textContent,
    importListeners: (importButton.listeners.click || []).length,
    generateListeners: (env.selectors.get("#generate-tracks").listeners.click || []).length,
    loadListeners: (env.selectors.get("#load-draft").listeners.click || []).length,
    fetchProvider: fetchCalls[0].body.provider,
  };

  await importButton.trigger("click");
  const malformedImport = {
    importStatus: env.selectors.get("#import-status").textContent,
    resultText: env.selectors.get("#result").textContent,
    fetchProvider: fetchCalls[1].body.provider,
  };

  process.stdout.write(JSON.stringify({successfulImport, malformedImport}));
}

main().catch(error => {
  process.stderr.write(String(error && error.stack || error));
  process.exit(1);
});
'''
    completed = subprocess.run(
        ["node", "-e", script, str(generation_script_path), str(app_script_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["successfulImport"] == {
        "importDisabled": False,
        "importStatus": "Imported 0 draft tracks. Review the list before confirmation.",
        "resultText": json.dumps({
            "draft_only": True,
            "available": True,
            "provider": "structured_json",
            "message": "Imported 0 draft tracks. Review the list before confirmation.",
            "draft_tracks": [],
        }, indent=2),
        "importListeners": 1,
        "generateListeners": 1,
        "loadListeners": 1,
        "fetchProvider": "structured_json",
    }
    assert result["malformedImport"] == {
        "importStatus": "Draft import failed: invalid JSON",
        "resultText": json.dumps({"error": "Draft import failed: invalid JSON"}, indent=2),
        "fetchProvider": "structured_json",
    }


def test_launch_modes_are_explicit_and_secure_tokens_are_ephemeral() -> None:
    local = resolve_launch_mode(lan=False, secure=False)
    trusted = resolve_launch_mode(lan=True, secure=False)
    protected_one = resolve_launch_mode(lan=True, secure=True)
    protected_two = resolve_launch_mode(lan=True, secure=True)

    assert (local.name, local.bind_host, local.access_token) == ("localhost", "127.0.0.1", None)
    assert (trusted.name, trusted.bind_host, trusted.access_token) == ("trusted LAN", "0.0.0.0", None)
    assert protected_one.name == "protected LAN"
    assert protected_one.bind_host == "0.0.0.0"
    assert protected_one.access_token
    assert protected_one.access_token != protected_two.access_token
    with pytest.raises(ValueError, match="--secure requires --lan"):
        resolve_launch_mode(lan=False, secure=True)


def test_startup_output_identifies_transport_security_mode() -> None:
    local = startup_lines(resolve_launch_mode(lan=False, secure=False), 8765, ["127.0.0.1"])
    trusted = startup_lines(resolve_launch_mode(lan=True, secure=False), 8765, ["192.168.1.7"])
    protected = startup_lines(resolve_launch_mode(lan=True, secure=True), 8765, ["192.168.1.7"])

    assert local == ["Maestro Evidence Workbench", "Mode: localhost", "Open: http://127.0.0.1:8765"]
    assert "WARNING: Trusted LAN mode enabled." in trusted
    assert "This workbench is accessible to devices on your local network." in trusted
    assert trusted[-1] == "http://192.168.1.7:8765"
    assert "Mode: protected LAN" in protected
    assert "Session token generated for this launch." in protected
    assert protected[-1].startswith("http://192.168.1.7:8765/?session=")

    with pytest.raises(ValueError, match="canonical_identity_established"):
        build_governed_proposal(
            "historical_experiment",
            {
                "tracklist_completeness": "PARTIAL",
                "captures_playlist_start": "UNKNOWN",
                "captures_playlist_end": "UNKNOWN",
                "tracks": [{"title": "Observed title", "artist": "Observed artist"}],
            },
            [],
        )


def test_workbench_python_surface_has_no_direct_repository_access() -> None:
    root = Path(__file__).parents[1] / "src" / "playlist_narrative_engine" / "maestro_workbench"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))

    assert "research_store.repository" not in source
    assert "sqlalchemy" not in source
    assert "sqlite3" not in source


def test_local_http_surface_stages_validates_and_explicitly_ingests(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    server = MaestroWorkbenchServer(
        ("127.0.0.1", 0),
        database_url=database_url,
        staging_root=tmp_path / "staging",
        access_token="test-token",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base_url}/?session=test-token") as response:
            assert b"Collect. Display. Invoke." in response.read()

        unauthorized = Request(
            f"{base_url}/api/validate",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as denied:
            urlopen(unauthorized)
        assert denied.value.code == 403

        invalid_token = Request(
            f"{base_url}/api/health",
            headers={"X-Workbench-Token": "wrong-token"},
        )
        with pytest.raises(HTTPError) as invalid:
            urlopen(invalid_token)
        assert invalid.value.code == 403

        evidence_request = Request(
            f"{base_url}/api/stage-evidence",
            data=b"screenshot bytes",
            headers={
                "X-Original-Filename": "capture%20one.png",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(evidence_request) as response:
            staged = json.load(response)
        assert staged["sha256"] == hashlib.sha256(b"screenshot bytes").hexdigest()
        assert staged["original_filename"] == "capture one.png"

        build_request = Request(
            f"{base_url}/api/build-proposal",
            data=json.dumps({
                "kind": "historical_experiment",
                "declarations": {
                    "prompt": "Built prompt",
                    "tracklist_completeness": "NOT_OBSERVED",
                    "tracks": [],
                },
                "staged_evidence": [],
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(build_request) as response:
            built = json.load(response)["proposal"]
        assert built["prompt"] == "Built prompt"
        assert built["tracklist_completeness"] == "NOT_OBSERVED"
        with open_research_store_service(database_url) as service:
            assert service.get_experiment(1) is None

        extract_request = Request(
            f"{base_url}/api/generate-draft-tracklist",
            data=json.dumps({
                "provider": "delimited_text",
                "source_keys": ["source_1"],
                "supplied_text": "1 | Draft title | Draft artist |",
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(extract_request) as response:
            draft = json.load(response)
        assert draft["draft_tracks"][0]["review_status"] == "UNREVIEWED"

        structured_request = Request(
            f"{base_url}/api/generate-draft-tracklist",
            data=json.dumps({
                "provider": "structured_json",
                "source_keys": ["source_1"],
                "supplied_text": json.dumps({"tracks": [{
                    "position": 4,
                    "title": "  Exact imported title  ",
                    "artist": "Imported artist",
                    "version": None,
                    "uncertain": True,
                    "source_keys": ["source_1"],
                }]}),
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(structured_request) as response:
            structured_draft = json.load(response)
        assert structured_draft["provider"] == "structured_json"
        assert structured_draft["draft_tracks"] == [{
            "proposed_position": 4,
            "proposed_title": "  Exact imported title  ",
            "proposed_artist": "Imported artist",
            "proposed_version_remaster_text": None,
            "source_keys": ["source_1"],
            "ambiguity_flag": True,
            "review_status": "UNREVIEWED",
        }]
        with open_research_store_service(database_url) as service:
            assert service.get_experiment(1) is None

        unavailable_request = Request(
            f"{base_url}/api/generate-draft-tracklist",
            data=json.dumps({
                "provider": "automatic",
                "source_keys": ["source_1"],
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(unavailable_request) as response:
            unavailable_draft = json.load(response)
            assert response.status == 200
        assert unavailable_draft["available"] is False
        assert unavailable_draft["draft_tracks"] == []
        assert "No automatic extraction provider is configured" in unavailable_draft["message"]
        with open_research_store_service(database_url) as service:
            assert service.get_experiment(1) is None

        proposal = {
            "kind": "historical_experiment",
            "proposal": {
                "prompt": "Exact prompt",
                "tracklist_completeness": "NOT_OBSERVED",
                "tracks": [],
            },
        }
        validate_request = Request(
            f"{base_url}/api/validate",
            data=json.dumps(proposal).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(validate_request) as response:
            assert json.load(response)["valid"] is True
        with open_research_store_service(database_url) as service:
            assert service.get_experiment(1) is None

        ingest_request = Request(
            f"{base_url}/api/ingest",
            data=json.dumps(proposal).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(ingest_request) as response:
            inserted = json.load(response)
        assert inserted["record_id"] == 1
        assert inserted["record"]["prompt"] == "Exact prompt"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_surface_serves_current_workbench_html_and_javascript_with_no_cache_headers(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    server = MaestroWorkbenchServer(
        ("127.0.0.1", 0),
        database_url=database_url,
        staging_root=tmp_path / "staging",
        access_token=None,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base_url}/") as response:
            html = response.read().decode("utf-8")
            html_headers = response.headers
        with urlopen(f"{base_url}/draft_generation.js") as response:
            generation_javascript = response.read().decode("utf-8")
            generation_headers = response.headers
        with urlopen(f"{base_url}/app.js") as response:
            application_javascript = response.read().decode("utf-8")
            application_headers = response.headers

        assert html_headers.get("Content-Type") == "text/html; charset=utf-8"
        assert html_headers.get("Cache-Control") == "no-store"
        assert html_headers.get("Pragma") == "no-cache"
        assert html_headers.get("Expires") == "0"
        assert html.index('src="/draft_generation.js"') < html.index('src="/app.js"')
        assert 'PneDraftGenerationPublication = {state: "awaiting-script"}' in html
        assert 'PneDraftGenerationPublication.state = "load-failed"' in html
        assert 'PneDraftGenerationPublication.state = "execution-failed"' in html

        assert generation_headers.get("Content-Type") == "text/javascript; charset=utf-8"
        assert generation_headers.get("Cache-Control") == "no-store"
        assert generation_headers.get("Pragma") == "no-cache"
        assert generation_headers.get("Expires") == "0"
        assert "window.DraftGenerationFlow = api" in generation_javascript
        assert 'PneDraftGenerationPublication.state = "published"' in generation_javascript
        assert 'dataset.draftGenerationPublication = "published"' in generation_javascript

        assert application_headers.get("Content-Type") == "text/javascript; charset=utf-8"
        assert application_headers.get("Cache-Control") == "no-store"
        assert application_headers.get("Pragma") == "no-cache"
        assert application_headers.get("Expires") == "0"
        assert "function initializeDraftTrackWorkflow()" in application_javascript
        assert "Workbench initialization failed: draft-track workflow unavailable." in application_javascript
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_surface_serves_new_static_javascript_files_without_hardcoded_route_entries(tmp_path, monkeypatch) -> None:
    static_root = tmp_path / "static"
    static_root.mkdir()
    (static_root / "index.html").write_text(
        '<!doctype html><html><body><script src="/draft_generation.js"></script><script src="/app.js"></script></body></html>',
        encoding="utf-8",
    )
    (static_root / "draft_generation.js").write_text("window.DraftGenerationFlow = { run() {}, validateResult() {} };", encoding="utf-8")
    (static_root / "app.js").write_text("window.__appLoaded = true;", encoding="utf-8")
    (static_root / "styles.css").write_text("body { color: black; }", encoding="utf-8")
    monkeypatch.setattr("playlist_narrative_engine.maestro_workbench.server.STATIC_ROOT", static_root)

    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    server = MaestroWorkbenchServer(
        ("127.0.0.1", 0),
        database_url=database_url,
        staging_root=tmp_path / "staging",
        access_token=None,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base_url}/draft_generation.js") as response:
            body = response.read().decode("utf-8")
            headers = response.headers
        assert body == "window.DraftGenerationFlow = { run() {}, validateResult() {} };"
        assert headers.get("Content-Type") == "text/javascript; charset=utf-8"
        assert headers.get("Cache-Control") == "no-store"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_unauthenticated_modes_use_the_same_validation_behavior(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    server = MaestroWorkbenchServer(
        ("127.0.0.1", 0),
        database_url=database_url,
        staging_root=tmp_path / "staging",
        access_token=None,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base_url}/") as response:
            assert response.status == 200
        request = Request(
            f"{base_url}/api/validate",
            data=json.dumps({
                "kind": "historical_experiment",
                "proposal": {"prompt": "Same semantics", "tracklist_completeness": "NOT_OBSERVED", "tracks": []},
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            assert json.load(response) == {
                "valid": True,
                "validation_issues": [],
                "evidence_valid": True,
                "evidence_issues": [],
            }
        with open_research_store_service(database_url) as service:
            assert service.get_experiment(1) is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_realistic_historical_workbench_http_journey_builds_validates_ingests_and_reads_back(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    server = MaestroWorkbenchServer(
        ("127.0.0.1", 0),
        database_url=database_url,
        staging_root=tmp_path / "staging",
        access_token=None,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    def post_json(path: str, document: dict[str, object]) -> dict[str, object]:
        request = Request(
            f"{base_url}{path}",
            data=json.dumps(document).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            return json.load(response)

    try:
        with urlopen(f"{base_url}/") as response:
            html = response.read().decode("utf-8")
        with urlopen(f"{base_url}/app.js") as response:
            javascript = response.read().decode("utf-8")
        assert 'id="stage-status"' in html
        assert 'id="readiness"' in html
        assert 'id="build-status"' in html
        assert 'id="validation-status"' in html
        assert 'id="ingest-status"' in html
        assert 'data-claim-field="prompt"' in html
        assert 'id="prompt-attested"' in html
        assert "function coverageByTrack(trackCount)" in javascript
        assert "function renderReadback(record, kindName)" in javascript

        staged = []
        for index in range(1, 7):
            request = Request(
                f"{base_url}/api/stage-evidence",
                data=f"screenshot-{index}".encode(),
                headers={"X-Original-Filename": f"wheelbarrow-{index}.png"},
                method="POST",
            )
            with urlopen(request) as response:
                item = json.load(response)
            staged.append({
                **item,
                "source_type": "SCREENSHOT",
                "source_reference": f"wheelbarrow screenshot {index}",
            })

        ranges = [(1, 8), (7, 15), (14, 22), (21, 29), (28, 36), (35, 40)]
        tracks = []
        for position in range(1, 41):
            source_keys = [
                f"source_{index}"
                for index, (start, end) in enumerate(ranges, start=1)
                if start <= position <= end
            ]
            tracks.append({
                "absolute_position": position,
                "title": "Chandelier" if position == 1 else f"Track {position}",
                "artist": "Sia" if position == 1 else f"Artist {position}",
                "version_or_remaster_text": None,
                "source_keys": source_keys,
                "canonical_identity_established": False,
                "provenance_type": "DIRECT_OBSERVATION",
                "support_status": "FULL",
            })
        screenshot_claim_fields = (
            "source_system", "generated_title", "generated_description",
            "generated_track_count", "tracklist_completeness",
        )
        staged.append({
            "source_type": "CONVERSATION_USER_STATEMENT",
            "source_reference": "workbench:operator-prompt-attestation",
            "notes": "Operator explicitly attested that the supplied prompt is exact.",
        })
        declarations = {
            "prompt": "Songs that accurately capture the exact emotional frequency of a medieval peasant watching a wheelbarrow break for the third time that week.",
            "source_system": "Maestro Beta",
            "generated_title": "When Things Break Again",
            "generated_description": "Weary frustration and resigned exhaustion in musical form",
            "notes": "Experiment tests emotional interpretation of a repeated practical failure.",
            "evidence_standard": "RECOVERED_HISTORICAL",
            "tracklist_completeness": "COMPLETE",
            "captures_playlist_start": "YES",
            "captures_playlist_end": "YES",
            "tracks": tracks,
            "top_level_evidence": [{
                "source_key": "source_1",
                "field_name": field,
                "provenance_type": "DIRECT_OBSERVATION",
                "support_status": "FULL",
            } for field in screenshot_claim_fields] + [{
                "source_key": "source_7",
                "field_name": "prompt",
                "provenance_type": "HUMAN_ASSESSMENT",
                "support_status": "FULL",
            }],
        }
        built = post_json("/api/build-proposal", {
            "kind": "historical_experiment",
            "declarations": declarations,
            "staged_evidence": staged,
        })["proposal"]
        assert len(built["tracks"]) == 40
        assert len(built["evidence_sources"]) == 7
        assert len(built["evidence"]) == 6
        prompt_link = next(link for link in built["evidence"] if link["field_name"] == "prompt")
        assert prompt_link["source_key"] == "source_7"
        assert prompt_link["provenance_type"] == "HUMAN_ASSESSMENT"

        validation = post_json("/api/validate", {"kind": "historical_experiment", "proposal": built})
        assert validation == {
            "valid": True,
            "validation_issues": [],
            "evidence_valid": True,
            "evidence_issues": [],
        }
        with open_research_store_service(database_url) as service:
            assert service.get_experiment(1) is None

        ingested = post_json("/api/ingest", {"kind": "historical_experiment", "proposal": built})
        assert ingested["record_id"] == 1
        record = ingested["record"]
        assert record["prompt"] == declarations["prompt"]
        assert record["generated_title"] == "When Things Break Again"
        assert record["generated_description"] == "Weary frustration and resigned exhaustion in musical form"
        assert record["tracklist_completeness"] == "COMPLETE"
        assert len(record["tracks"]) == 40
        assert [track["position"] for track in record["tracks"]] == list(range(1, 41))
        assert len(record["evidence_sources"]) == 7
        assert {link["field_name"] for link in record["evidence"]} == set(screenshot_claim_fields) | {"prompt"}
        assert all(track["evidence"] for track in record["tracks"])
        with open_research_store_service(database_url) as service:
            assert service.get_experiment(1) == record
            assert service.get_experiment(2) is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_workbench_operator_lifecycle_is_local_and_fail_closed() -> None:
    root = Path(__file__).parents[1] / "src" / "playlist_narrative_engine" / "maestro_workbench" / "static"
    html = (root / "index.html").read_text(encoding="utf-8")
    javascript = (root / "app.js").read_text(encoding="utf-8")

    for status_id in ("stage-status", "build-status", "validation-status", "ingest-status"):
        assert f'id="{status_id}"' in html
    assert '<option value="">Select explicitly…</option><option>CONTEMPORARY_MANUAL</option>' in html
    assert 'id="prompt-attested"' in html
    assert 'source_type: "CONVERSATION_USER_STATEMENT"' in javascript
    assert 'provenance_type: "HUMAN_ASSESSMENT"' in javascript
    assert "Support the prompt with a visible screenshot or explicitly attest" in javascript
    assert '$("#prompt-attested").checked = false;' in javascript
    assert "Cannot build yet:" in javascript
    assert "missing_prerequisites: issues" in javascript
    assert "returned a malformed response" in javascript
    assert "returned malformed JSON" in javascript
    assert "finally" in javascript
    assert "if (ingestionActive) return;" in javascript
    assert "validatedProposalSnapshot !== proposal.value" in javascript
    assert "Proposal changed. Validate again before ingestion." in javascript
    assert "Ingestion cancelled. No write occurred." in javascript
    assert "renderReadback(body.record, body.kind)" in javascript
    assert "View raw projection" in javascript
