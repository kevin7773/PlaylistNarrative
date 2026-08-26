const $ = selector => document.querySelector(selector);
const kind = $("#kind");
const proposal = $("#proposal");
const result = $("#result");
const stagedContainer = $("#staged");
const accessToken = new URLSearchParams(window.location.search).get("session") || new URLSearchParams(window.location.search).get("token");
const stagedEvidence = [];
let confirmedTracks = null;
let acceptedExtractionContinuity = null;
let validatedProposalSnapshot = null;
let ingestionActive = false;
let pendingSourceDeclarations = null;
let plannedRunContext = (() => {
  try { return JSON.parse(sessionStorage.getItem("pne-planned-run") || "null"); }
  catch (_error) { return null; }
})();
let structuredWorksheet = null;
let structuredWorksheetProposalSnapshot = null;
let structuredPreviewComplete = false;

const REQUIRED_HISTORICAL_CLAIMS = [
  ["source_system", "Source system"],
  ["generated_title", "Generated title"],
  ["generated_description", "Generated description"],
  ["generated_track_count", "Generated track count"],
  ["tracklist_completeness", "Tracklist completeness"],
];

function promptAttestationSourceKey() {
  return `source_${stagedEvidence.length + 1}`;
}

function apiHeaders(additional = {}) {
  return accessToken ? {...additional, "X-Workbench-Token": accessToken} : additional;
}

function show(value) {
  result.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function setLocalStatus(selector, message, state = "idle") {
  const target = $(selector);
  target.textContent = message;
  target.dataset.state = state;
}

function beginOperation(button, statusSelector, busyLabel) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = busyLabel;
  setLocalStatus(statusSelector, `${busyLabel}…`, "busy");
  return () => {
    button.disabled = false;
    button.textContent = original;
  };
}

async function readJsonResponse(response, operationName) {
  const contentType = response.headers.get("Content-Type") || "";
  if (!contentType.includes("application/json")) throw new Error(`${operationName} returned a malformed response`);
  let body;
  try { body = await response.json(); }
  catch (_error) { throw new Error(`${operationName} returned malformed JSON`); }
  if (!response.ok) throw new Error(body?.error || `${operationName} failed with HTTP ${response.status}`);
  return body;
}

function invalidateValidation(message = "Proposal changed. Validate again before ingestion.") {
  validatedProposalSnapshot = null;
  if (structuredWorksheet) {
    structuredPreviewComplete = false;
    setLocalStatus("#structured-evaluation-preview", "Experiment proposal changed. Recalculate the deterministic preview.", "idle");
  }
  $("#ingest").disabled = true;
  setLocalStatus("#validation-status", message, "idle");
}

function invalidateStructuredWorksheet(message = "Advanced governed JSON changed. Rebuild the structured worksheet from the current proposal before preview or realization.") {
  if (!plannedRunContext?.constraints?.some(item => item.structured_evaluation_plan)) return;
  structuredWorksheet = null;
  structuredWorksheetProposalSnapshot = null;
  structuredPreviewComplete = false;
  $("#ingest").disabled = true;
  $("#preview-structured-evaluation").disabled = true;
  $("#rebuild-structured-evaluation").disabled = proposal.value.trim() === "";
  $("#structured-evaluation-constraints").querySelectorAll("input,select,button").forEach(control => { control.disabled = true; });
  setLocalStatus("#structured-worksheet-state", message, "error");
  setLocalStatus("#structured-evaluation-preview", "Preview blocked: the worksheet is stale and has not been reconciled with the edited proposal.", "error");
}

function structuredWorksheetIsCurrent() {
  return Boolean(structuredWorksheet && structuredWorksheetProposalSnapshot === proposal.value);
}

function markWorksheetSynchronizedWithProposal() {
  if (structuredWorksheet) structuredWorksheetProposalSnapshot = proposal.value;
}

function draftWorkflowControls() {
  return ["#generate-tracks", "#import-draft", "#load-draft"].map(selector => $(selector));
}

function setDraftWorkflowAvailability(enabled, message = "") {
  draftWorkflowControls().forEach(control => {
    control.disabled = !enabled;
  });
  if (message) {
    $("#extraction-status").textContent = message;
    $("#import-status").textContent = message;
  }
}

function resolveDraftGenerationFlow() {
  const api = window.DraftGenerationFlow;
  if (!api || typeof api.run !== "function" || typeof api.validateResult !== "function") {
    return null;
  }
  return api;
}

function sourceOptions(select, selected = select.multiple ? [] : "") {
  const selectedValues = Array.isArray(selected) ? selected : [selected];
  select.innerHTML = select.multiple ? "" : `<option value="">None declared</option>`;
  stagedEvidence.forEach((item, index) => {
    const option = document.createElement("option");
    option.value = `source_${index + 1}`;
    option.textContent = `source_${index + 1} · ${item.original_filename}`;
    option.selected = selectedValues.includes(option.value);
    select.append(option);
  });
}

function refreshSourceSelectors() {
  document.querySelectorAll("select[data-source-select], #start-source, #end-source, [data-field='source_key']")
    .forEach(select => sourceOptions(select, select.multiple ? [...select.selectedOptions].map(option => option.value) : select.value));
}

function renderStaged() {
  stagedContainer.innerHTML = "";
  if (!stagedEvidence.length) {
    stagedContainer.innerHTML = `<p class="empty">No evidence staged.</p>`;
    refreshSourceSelectors();
    renderCoverage();
    refreshReadiness();
    refreshScreenshotExtractionAvailability();
    return;
  }
  stagedEvidence.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = "entry-card evidence-card";
    card.innerHTML = `
      <div class="entry-head"><strong>source_${index + 1} · ${escapeHtml(item.original_filename)}</strong><span class="status">Exact bytes preserved</span></div>
      <dl><dt>SHA-256</dt><dd>${item.sha256}</dd><dt>Staged path</dt><dd>${escapeHtml(item.local_path)}</dd><dt>Size</dt><dd>${item.size_bytes} bytes</dd></dl>
      <div class="form-grid">
        <label>Source type<input data-source-type type="text" value="${escapeHtml(item.source_type || "")}" placeholder="Explicit source type"></label>
        <label>Source reference<input data-source-reference type="text" value="${escapeHtml(item.source_reference || "")}" placeholder="Explicit source reference"></label>
      </div>`;
    card.querySelector("[data-source-type]").addEventListener("input", event => { item.source_type = event.target.value; invalidateValidation(); refreshReadiness(); });
    card.querySelector("[data-source-reference]").addEventListener("input", event => { item.source_reference = event.target.value; invalidateValidation(); refreshReadiness(); });
    stagedContainer.append(card);
  });
  refreshSourceSelectors();
  renderCoverage();
  refreshReadiness();
  refreshScreenshotExtractionAvailability();
}

function refreshScreenshotExtractionAvailability() {
  if (typeof document.getElementById !== "function" || !document.getElementById("extract-screenshots")) return;
  const eligible = stagedEvidence.some(item => item.screenshot_extraction_supported === true);
  $("#extract-screenshots").disabled = !eligible;
  if (!stagedEvidence.length) {
    setLocalStatus("#screenshot-extraction-status", "Stage a screenshot matching an exact validated Maestro layout to enable extraction.");
  } else if (!eligible) {
    setLocalStatus("#screenshot-extraction-status", "No staged screenshot matches an exact validated Maestro layout. Manual draft tools remain available.");
  }
}

function sourceDeclarationPreview(sourceType, referenceBase) {
  const base = referenceBase.trim();
  if (sourceType !== "SCREENSHOT") throw new Error("Select the established screenshot source type");
  if (!base) throw new Error("Enter an explicit source-reference base");
  if (!stagedEvidence.length) throw new Error("Stage at least one screenshot before previewing declarations");
  return stagedEvidence.map((item, index) => ({
    source_type: sourceType,
    source_reference: `${base} ${index + 1}`,
    original_filename: item.original_filename,
  }));
}

function clearSourceDeclarationPreview(message = "No bulk source declaration preview.") {
  pendingSourceDeclarations = null;
  $("#source-declaration-preview").innerHTML = `<p class="hint">${escapeHtml(message)}</p>`;
}

function previewSourceDeclarations() {
  try {
    pendingSourceDeclarations = sourceDeclarationPreview(
      $("#bulk-source-type").value,
      $("#bulk-source-reference").value,
    );
    $("#source-declaration-preview").innerHTML = `
      <strong>Preview only — nothing has been applied.</strong>
      <ol>${pendingSourceDeclarations.map(item => `<li>${escapeHtml(item.source_reference)} <span class="hint">(${escapeHtml(item.original_filename)})</span></li>`).join("")}</ol>
      <div class="preview-actions"><button id="apply-source-declarations" type="button">Apply these declarations</button><button id="cancel-source-declarations" class="ghost" type="button">Cancel</button></div>`;
    $("#apply-source-declarations").addEventListener("click", applySourceDeclarations);
    $("#cancel-source-declarations").addEventListener("click", () => clearSourceDeclarationPreview("Bulk declaration cancelled. Existing declarations were not changed."));
  } catch (error) {
    clearSourceDeclarationPreview(error.message);
  }
}

function applySourceDeclarations() {
  if (!pendingSourceDeclarations || pendingSourceDeclarations.length !== stagedEvidence.length) {
    clearSourceDeclarationPreview("Preview the complete declaration set before applying it.");
    return;
  }
  pendingSourceDeclarations.forEach((declaration, index) => {
    stagedEvidence[index].source_type = declaration.source_type;
    stagedEvidence[index].source_reference = declaration.source_reference;
  });
  const count = pendingSourceDeclarations.length;
  pendingSourceDeclarations = null;
  renderStaged();
  clearSourceDeclarationPreview(`Applied explicit SCREENSHOT declarations to ${count} distinct staged screenshots. Individual references remain editable below.`);
  setLocalStatus("#stage-status", `Applied ${count} explicit screenshot source declarations.`, "success");
  invalidateValidation();
  refreshReadiness();
}

function renderCoverage() {
  const container = $("#track-coverage");
  const previous = new Map([...container.querySelectorAll(".coverage-row")].map(row => [row.dataset.sourceKey, {
    start: row.querySelector("[data-coverage-start]").value,
    end: row.querySelector("[data-coverage-end]").value,
  }]));
  container.innerHTML = "";
  if (!stagedEvidence.length) {
    container.innerHTML = `<p class="empty">Stage screenshots to declare track coverage.</p>`;
    return;
  }
  stagedEvidence.forEach((item, index) => {
    const sourceKey = `source_${index + 1}`;
    const values = previous.get(sourceKey) || {start: "", end: ""};
    const row = document.createElement("article");
    row.className = "entry-card coverage-row";
    row.dataset.sourceKey = sourceKey;
    row.innerHTML = `<strong>${sourceKey} · ${escapeHtml(item.original_filename)}</strong><div class="coverage-fields"><label>First supported track<input data-coverage-start type="number" min="1" value="${values.start}"></label><span>through</span><label>Final supported track<input data-coverage-end type="number" min="1" value="${values.end}"></label></div>`;
    row.querySelectorAll("input").forEach(input => input.addEventListener("input", () => { invalidateValidation(); refreshReadiness(); }));
    container.append(row);
  });
}

async function stageEvidence() {
  const button = $("#stage");
  const finish = beginOperation(button, "#stage-status", "Staging selected originals");
  const files = [...$("#evidence-files").files];
  try {
    if (!files.length) throw new Error("Select at least one evidence file to stage");
    for (const file of files) {
      const response = await fetch("/api/stage-evidence", {
        method: "POST",
        headers: apiHeaders({"X-Original-Filename": encodeURIComponent(file.name)}),
        body: file
      });
      stagedEvidence.push(await readJsonResponse(response, `Staging ${file.name}`));
    }
    $("#evidence-files").value = "";
    clearSourceDeclarationPreview("Evidence changed. Preview bulk declarations again before applying them.");
    renderStaged();
    const message = `Staged ${files.length} original${files.length === 1 ? "" : "s"}. Verify filenames and SHA-256 values below.`;
    setLocalStatus("#stage-status", message, "success");
    show({staged: stagedEvidence.length, message});
  } catch (error) {
    const message = `Staging failed: ${error.message}`;
    setLocalStatus("#stage-status", message, "error");
    show({error: message});
  } finally {
    finish();
  }
}

function acceptScreenshotExtraction(review) {
  if (review.generated_title !== null) $("#generated-title").value = review.generated_title;
  if (review.generated_description !== null) $("#generated-description").value = review.generated_description;
  $("#draft-tracks").innerHTML = "";
  review.tracks.forEach(track => addDraftRow({...track, canonical_identity_established: false, provenance_type: "DIRECT_OBSERVATION"}));
  acceptedExtractionContinuity = review.continuity_established;
  review.coverage.forEach(item => {
    const row = [...document.querySelectorAll("#track-coverage .coverage-row")]
      .find(candidate => candidate.dataset.sourceKey === item.source_key);
    if (row) {
      row.querySelector("[data-coverage-start]").value = item.start ?? "";
      row.querySelector("[data-coverage-end]").value = item.end ?? "";
    }
  });
  const start = review.coverage.find(item => item.playlist_start === "YES");
  const end = review.coverage.find(item => item.playlist_end === "YES");
  if (start) { $("#captures-start").value = "YES"; $("#start-source").value = start.source_key; }
  if (end) { $("#captures-end").value = "YES"; $("#end-source").value = end.source_key; }
  invalidateConfirmation();
  setLocalStatus("#screenshot-extraction-status", `Accepted ${review.tracks.length} reviewed extraction rows into the unconfirmed draft.`, "success");
}

async function extractScreenshotDraft() {
  const button = $("#extract-screenshots");
  const finish = beginOperation(button, "#screenshot-extraction-status", "Extracting screenshot draft");
  try {
    const response = await fetch("/api/extract-screenshot-draft", {
      method: "POST", headers: apiHeaders({"Content-Type": "application/json"}),
      body: JSON.stringify({staged_sources: stagedEvidence.map((item, index) => ({source_key: `source_${index + 1}`, local_path: item.local_path}))}),
    });
    const review = await readJsonResponse(response, "Screenshot extraction");
    window.ScreenshotExtractionReview.render($("#screenshot-extraction-review"), review, acceptScreenshotExtraction);
    setLocalStatus("#screenshot-extraction-status", "Extraction complete. Review or discard the disposable result.", "success");
  } catch (error) {
    setLocalStatus("#screenshot-extraction-status", `Screenshot extraction failed: ${error.message}`, "error");
  } finally {
    finish();
    refreshScreenshotExtractionAvailability();
  }
}

function optionalText(selector) {
  const value = $(selector).value;
  return value === "" ? undefined : value;
}

function optionalNumber(selector) {
  const value = $(selector).value;
  return value === "" ? undefined : Number(value);
}

function declaredRequestedTrackCount(state, rawValue) {
  if (state !== "KNOWN") return undefined;
  if (rawValue === "") throw new Error("Enter the explicitly known requested track count");
  const value = Number(rawValue);
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error("Requested track count must be an integer greater than zero");
  }
  return value;
}

function declaredSavedStatus(state) {
  if (state === "YES") return true;
  if (state === "NO") return false;
  return undefined;
}

function savedEvidenceReadinessIssue(state, selectedSourceKeys) {
  if (state === "UNKNOWN" || selectedSourceKeys.length) return null;
  return "Link the asserted saved status to supporting evidence";
}

function updateRequestedTrackCountState() {
  const known = $("#requested-count-state").value === "KNOWN";
  $("#requested-count").disabled = !known;
  if (!known) $("#requested-count").value = "";
  invalidateValidation();
  refreshReadiness();
}

function updateSavedStatus() {
  const unknown = $("#saved").value === "UNKNOWN";
  $("#saved-evidence-field").hidden = unknown;
  if (unknown) {
    const selector = document.querySelector("[data-claim-field='saved']");
    [...selector.options].forEach(option => { option.selected = false; });
  }
  invalidateValidation();
  refreshReadiness();
}

function collectStagedEvidence() {
  const sources = stagedEvidence.map((item, index) => {
    const card = stagedContainer.children[index];
    const sourceType = card.querySelector("[data-source-type]").value.trim();
    const sourceReference = card.querySelector("[data-source-reference]").value.trim();
    if (!sourceType || !sourceReference) throw new Error(`source_${index + 1} requires source type and source reference`);
    return {...item, source_type: sourceType, source_reference: sourceReference};
  });
  if ($("#prompt-attested").checked) {
    sources.push({
      source_type: "CONVERSATION_USER_STATEMENT",
      source_reference: "workbench:operator-prompt-attestation",
      notes: "Operator explicitly attested that the supplied prompt is the exact original prompt.",
    });
  }
  return sources;
}

function collectRows(containerSelector, rowSelector) {
  return [...document.querySelectorAll(`${containerSelector} ${rowSelector}`)].map(row => {
    const value = {};
    row.querySelectorAll("[data-field]").forEach(input => {
      if (input.type === "checkbox") value[input.dataset.field] = input.checked;
      else if (input.type === "number") value[input.dataset.field] = input.value === "" ? null : Number(input.value);
      else if (input instanceof HTMLSelectElement && input.multiple) value[input.dataset.field] = [...input.selectedOptions].map(option => option.value);
      else if (input.hasAttribute("data-boolean")) value[input.dataset.field] = input.value === "" ? null : input.value === "true";
      else value[input.dataset.field] = input.value || null;
    });
    return value;
  });
}

function selectedValues(select) {
  return [...select.selectedOptions].map(option => option.value);
}

function collectClaimEvidence() {
  const provenanceType = $("#evidence-provenance").value;
  const supportStatus = $("#evidence-support").value;
  const links = [...document.querySelectorAll("[data-claim-field]")].flatMap(select => {
    if (select.dataset.claimField === "saved" && $("#saved").value === "UNKNOWN") return [];
    return selectedValues(select).map(sourceKey => ({
      source_key: sourceKey,
      field_name: select.dataset.claimField,
      provenance_type: provenanceType,
      support_status: supportStatus,
    }));
  });
  if ($("#prompt-attested").checked) {
    links.push({
      source_key: promptAttestationSourceKey(),
      field_name: "prompt",
      provenance_type: "HUMAN_ASSESSMENT",
      support_status: "FULL",
    });
  }
  return links;
}

function coverageByTrack(trackCount) {
  const result = new Map(Array.from({length: trackCount}, (_, index) => [index + 1, []]));
  document.querySelectorAll(".coverage-row").forEach(row => {
    const startText = row.querySelector("[data-coverage-start]").value;
    const endText = row.querySelector("[data-coverage-end]").value;
    if (startText === "" || endText === "") return;
    const start = Number(startText);
    const end = Number(endText);
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end < start || end > trackCount) return;
    for (let position = start; position <= end; position += 1) result.get(position).push(row.dataset.sourceKey);
  });
  return result;
}

function operatorCoverageComplete(trackCount) {
  if (!trackCount) return false;
  const ranges = [...document.querySelectorAll(".coverage-row")].map(row => ({
    start: row.querySelector("[data-coverage-start]").value,
    end: row.querySelector("[data-coverage-end]").value,
  }));
  return window.ScreenshotExtractionReview.coverageRangesComplete(trackCount, ranges);
}

function tracksWithCoverage() {
  if (!confirmedTracks) return [];
  const coverage = coverageByTrack(confirmedTracks.length);
  const provenanceType = $("#evidence-provenance").value;
  const supportStatus = $("#evidence-support").value;
  return confirmedTracks.map((track, index) => ({
    ...track,
    source_keys: [...new Set([...(track.source_keys || []), ...(coverage.get(index + 1) || [])])],
    provenance_type: provenanceType,
    support_status: supportStatus,
  }));
}

function incompleteSourceDeclarationOrdinals(items) {
  return items.reduce((ordinals, item, index) => {
    if (!(item.source_type || "").trim() || !(item.source_reference || "").trim()) ordinals.push(index + 1);
    return ordinals;
  }, []);
}

function additionalEvidenceLinkIssues() {
  const issues = [];
  document.querySelectorAll("#evidence-links .link-row").forEach((row, index) => {
    const ordinal = index + 1;
    const sourceKey = row.querySelector("[data-field='source_key']").value;
    const fieldName = row.querySelector("[data-field='field_name']").value.trim();
    const provenanceType = row.querySelector("[data-field='provenance_type']").value;
    if (!sourceKey) issues.push(`Choose an evidence source for additional evidence link ${ordinal}`);
    if (!fieldName) issues.push(`Enter a proposal field for additional evidence link ${ordinal}`);
    if (!provenanceType) issues.push(`Choose provenance for additional evidence link ${ordinal}`);
  });
  return issues;
}

function readinessIssues() {
  const issues = [];
  const standard = $("#evidence-standard").value;
  const completeness = $("#completeness").value;
  if (!standard) issues.push("Choose an evidence standard");
  if (!completeness) issues.push("Choose tracklist completeness");
  if (completeness && completeness !== "NOT_OBSERVED") {
    if (!$("#captures-start").value) issues.push("Declare whether capture includes playlist start");
    if (!$("#captures-end").value) issues.push("Declare whether capture includes playlist end");
    if (confirmedTracks === null) issues.push("Confirm the reviewed tracklist");
    const continuityIssue = window.ScreenshotExtractionReview.completeContinuityIssue(
      completeness,
      acceptedExtractionContinuity,
      operatorCoverageComplete(confirmedTracks?.length || 0)
    );
    if (continuityIssue) issues.push(continuityIssue);
  }
  const incompleteSources = incompleteSourceDeclarationOrdinals(stagedEvidence);
  if (!stagedEvidence.length) issues.push("Stage evidence screenshots");
  else if (incompleteSources.length) issues.push(`Complete source declarations for screenshots ${incompleteSources.join(", ")}`);
  issues.push(...additionalEvidenceLinkIssues());
  if (standard === "RECOVERED_HISTORICAL" && kind.value === "historical_experiment") {
    const promptPresent = Boolean($("#prompt").value);
    const promptScreenshotSupport = selectedValues(document.querySelector("[data-claim-field='prompt']")).length > 0;
    const promptAttested = $("#prompt-attested").checked;
    if (!promptPresent) issues.push("Enter the prompt being supported");
    else if (!promptScreenshotSupport && !promptAttested) {
      issues.push("Support the prompt with a visible screenshot or explicitly attest the exact original prompt");
    }
    if (!$("#source-system").value) issues.push("Enter the source system being supported");
    if (!$("#generated-title").value) issues.push("Enter the generated title being supported");
    if (!$("#generated-description").value) issues.push("Enter the generated description being supported");
    if (!$("#evidence-provenance").value) issues.push("Choose evidence provenance");
    if (!$("#evidence-support").value) issues.push("Choose evidence support status");
    for (const [field, label] of REQUIRED_HISTORICAL_CLAIMS) {
      const select = document.querySelector(`[data-claim-field='${field}']`);
      if (!selectedValues(select).length) issues.push(`Link ${label.toLowerCase()} to supporting evidence`);
    }
    if ($("#saved").value !== "UNKNOWN") {
      const savedEvidence = document.querySelector("[data-claim-field='saved']");
      const savedIssue = savedEvidenceReadinessIssue($("#saved").value, selectedValues(savedEvidence));
      if (savedIssue) issues.push(savedIssue);
    }
    if (confirmedTracks?.length) {
      const uncovered = [...coverageByTrack(confirmedTracks.length)].filter(([, keys]) => !keys.length).map(([position]) => position);
      if (uncovered.length) issues.push(`Assign screenshot coverage for tracks ${uncovered.join(", ")}`);
    }
  }
  return issues;
}

function refreshReadiness() {
  refreshResearchReadiness();
  const issues = readinessIssues();
  const target = $("#readiness");
  if (!issues.length) {
    target.dataset.state = "success";
    target.innerHTML = `<strong>Evidence readiness</strong><p>✓ All required explicit declarations are complete.</p><p><strong>READY TO BUILD</strong></p>`;
    return;
  }
  target.dataset.state = "incomplete";
  target.innerHTML = `<strong>Evidence readiness</strong><ul>${issues.map(issue => `<li>${escapeHtml(issue)}</li>`).join("")}</ul>`;
}

function refreshResearchReadiness() {
  const requestedDeclared = $("#requested-count-state").value === "KNOWN";
  const canonicalTotal = confirmedTracks?.length || 0;
  const canonicalEstablished = confirmedTracks
    ? confirmedTracks.filter(track => track.canonical_identity_established === true).length
    : 0;
  const items = [
    ["Assessment Outcome", $("#assessment-outcome").value],
    ["Requested Track Count", requestedDeclared ? `declared (${$("#requested-count").value || "value required"})` : "not declared"],
    ["Tracklist Standard", $("#completeness").value || "not declared"],
    ["Playlist Start", $("#captures-start").value || "not declared"],
    ["Playlist End", $("#captures-end").value || "not declared"],
    ["Notes", $("#notes").value.trim() ? "present" : "absent"],
    ["Canonical Identity Coverage", canonicalTotal ? `${canonicalEstablished}/${canonicalTotal} confirmed tracks` : "not available"],
  ];
  $("#research-readiness").innerHTML = `<strong>Research readiness</strong><ul>${items.map(
    ([label, value]) => `<li><strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}</li>`
  ).join("")}</ul><p class="hint">Informational only; governed build and validation requirements are unchanged.</p>`;
}

function collectDeclarations() {
  const completeness = $("#completeness").value;
  if (!completeness) throw new Error("Tracklist completeness must be explicitly declared");
  const continuityIssue = window.ScreenshotExtractionReview.completeContinuityIssue(
    completeness,
    acceptedExtractionContinuity,
    operatorCoverageComplete(confirmedTracks?.length || 0)
  );
  if (continuityIssue) throw new Error(continuityIssue);
  const values = {
    source_system: optionalText("#source-system"),
    evidence_standard: $("#evidence-standard").value,
    tracklist_completeness: completeness,
    notes: optionalText("#notes"),
    tracks: completeness === "NOT_OBSERVED" ? [] : tracksWithCoverage(),
    top_level_evidence: [...collectClaimEvidence(), ...collectRows("#evidence-links", ".link-row")]
  };
  if (completeness !== "NOT_OBSERVED") {
    if (confirmedTracks === null) throw new Error("Confirm the reviewed tracklist before building a proposal");
    if (!$("#captures-start").value || !$("#captures-end").value) throw new Error("Playlist start and end boundaries must be explicitly declared");
    Object.assign(values, {
      captures_playlist_start: $("#captures-start").value,
      captures_playlist_end: $("#captures-end").value,
      start_source_key: $("#start-source").value || null,
      end_source_key: $("#end-source").value || null,
      boundary_provenance_type: $("#boundary-provenance").value
    });
  }
  if (kind.value === "historical_experiment") {
    Object.assign(values, {
      prompt: optionalText("#prompt"), prompt_title: optionalText("#prompt-title"),
      generated_title: optionalText("#generated-title"),
      generated_description: optionalText("#generated-description"),
      assessment_outcome: $("#assessment-outcome").value
    });
    if (plannedRunContext) {
      values.prompt = plannedRunContext.prompt;
      values.source_system = plannedRunContext.source_system;
      values.constraints = plannedRunContext.constraints.map(definition => {
        if (definition.structured_evaluation_plan) {
          return {
            study_constraint_definition_id: definition.id,
            constraint_type: definition.constraint_type,
            constraint_text: definition.constraint_text,
            is_hard_constraint: definition.is_hard_constraint,
          };
        }
        const status = $(`[data-study-result-status="${definition.id}"]`)?.value || "UNKNOWN";
        const evidence = $(`[data-study-result-evidence="${definition.id}"]`)?.value || null;
        return {
          study_constraint_definition_id: definition.id,
          constraint_type: definition.constraint_type,
          constraint_text: definition.constraint_text,
          is_hard_constraint: definition.is_hard_constraint,
          result: {
            status,
            evidence,
            provenance_type: definition.permitted_result_provenance,
          },
        };
      });
    }
    const requestedTrackCount = declaredRequestedTrackCount(
      $("#requested-count-state").value, $("#requested-count").value
    );
    if (requestedTrackCount !== undefined) values.requested_track_count = requestedTrackCount;
    const savedStatus = declaredSavedStatus($("#saved").value);
    if (savedStatus !== undefined) values.saved = savedStatus;
  } else {
    Object.assign(values, {
      display_title: optionalText("#display-title"), display_description: optionalText("#display-description"),
      visibility_text: optionalText("#visibility-text"), persistence_state: $("#persistence-state").value,
      displayed_track_count: optionalNumber("#displayed-count"), displayed_duration_text: optionalText("#displayed-duration")
    });
  }
  return values;
}

async function buildProposal() {
  const button = $("#build");
  const issues = readinessIssues();
  if (issues.length) {
    const message = `Cannot build yet:\n${issues.map(issue => `• ${issue}`).join("\n")}`;
    setLocalStatus("#build-status", message, "error");
    show({error: message, missing_prerequisites: issues});
    return;
  }
  const finish = beginOperation(button, "#build-status", "Building governed proposal");
  try {
    const response = await fetch("/api/build-proposal", {
      method: "POST", headers: apiHeaders({"Content-Type": "application/json"}),
      body: JSON.stringify({kind: kind.value, declarations: collectDeclarations(), staged_evidence: collectStagedEvidence()})
    });
    const body = await readJsonResponse(response, "Proposal construction");
    proposal.value = JSON.stringify(body.proposal, null, 2);
    invalidateValidation("Proposal built. Validate it before ingestion.");
    const message = `Proposal built: ${body.proposal.tracks?.length || 0} tracks, ${body.proposal.evidence_sources?.length || 0} evidence sources. No write occurred.`;
    setLocalStatus("#build-status", message, "success");
    show({built: true, message, proposal: body.proposal});
    if (plannedRunContext?.constraints.some(item => item.structured_evaluation_plan)) {
      await loadStructuredWorksheet(body.proposal);
    }
  } catch (error) {
    const message = `Proposal build failed: ${error.message}`;
    setLocalStatus("#build-status", message, "error");
    show({error: message});
  } finally {
    finish();
  }
}

function requestBody() {
  return {kind: kind.value, proposal: JSON.parse(proposal.value)};
}

async function validateProposal() {
  const button = $("#validate");
  const finish = beginOperation(button, "#validation-status", "Validating without writing");
  try {
    const request = requestBody();
    const snapshot = proposal.value;
    const response = await fetch("/api/validate", {method: "POST", headers: apiHeaders({"Content-Type": "application/json"}), body: JSON.stringify(request)});
    const body = await readJsonResponse(response, "Validation");
    show(body);
    if (body.valid) {
      validatedProposalSnapshot = snapshot;
      const requiresStructured = Boolean(plannedRunContext?.constraints.some(item => item.structured_evaluation_plan));
      $("#ingest").disabled = requiresStructured && (!structuredPreviewComplete || !structuredWorksheetIsCurrent());
      setLocalStatus("#validation-status", "Schema: valid. Evidence files: valid. No writes performed.", "success");
    } else {
      invalidateValidation();
      const details = [...(body.validation_issues || []).map(issue => issue.message), ...(body.evidence_issues || []).map(issue => issue.message)];
      setLocalStatus("#validation-status", `Validation refused. No writes performed. ${details.join(" ")}`, "error");
    }
  } catch (error) {
    invalidateValidation();
    const message = `Validation failed: ${error.message}. No writes performed.`;
    setLocalStatus("#validation-status", message, "error");
    show({error: message});
  } finally {
    finish();
    $("#ingest").disabled = validatedProposalSnapshot !== proposal.value ||
      Boolean(plannedRunContext?.constraints.some(item => item.structured_evaluation_plan) &&
        (!structuredPreviewComplete || !structuredWorksheetIsCurrent()));
  }
}

function countEvidenceLinks(record) {
  return (record.evidence || []).length + (record.tracks || []).reduce((count, track) => count + (track.evidence || []).length, 0);
}

function renderReadback(record, kindName) {
  const tracks = record.tracks || [];
  const first = tracks[0];
  const final = tracks[tracks.length - 1];
  $("#readback-summary").innerHTML = `<h3>Ingestion successful</h3><dl><dt>${kindName === "experiment" ? "Experiment" : "Artifact"} ID</dt><dd>${record.id}</dd><dt>Prompt</dt><dd>${escapeHtml(record.prompt || "Not supplied")}</dd><dt>Generated title</dt><dd>${escapeHtml(record.generated_title || record.display_title || "Not supplied")}</dd><dt>Generated description</dt><dd>${escapeHtml(record.generated_description || record.display_description || "Not supplied")}</dd><dt>Completeness</dt><dd>${escapeHtml(record.tracklist_completeness || "Not supplied")}</dd><dt>Track count</dt><dd>${tracks.length}</dd><dt>Evidence sources</dt><dd>${(record.evidence_sources || []).length}</dd><dt>Evidence links</dt><dd>${countEvidenceLinks(record)}</dd><dt>First track</dt><dd>${first ? escapeHtml(`${first.position || first.absolute_position}. ${first.title || ""} — ${first.artist || ""}`) : "None"}</dd><dt>Final track</dt><dd>${final ? escapeHtml(`${final.position || final.absolute_position}. ${final.title || ""} — ${final.artist || ""}`) : "None"}</dd></dl><details><summary>View raw projection</summary><pre>${escapeHtml(JSON.stringify(record, null, 2))}</pre></details>`;
}

function governedFieldValue(subject) {
  const field = subject.governed_field;
  const context = subject.displayed_context || {};
  return ({display_title: context.title, display_artist: context.artist,
    explicit_flag: context.explicit_flag,
    version_or_remaster_text: context.version_or_remaster_text})[field];
}

function evidenceFieldForGovernedField(field) {
  return ({display_title: "title", display_artist: "artist",
    explicit_flag: "explicit_flag",
    version_or_remaster_text: "version_or_remaster_text"})[field] || field;
}

function typedInput(definition, value, readOnly = false) {
  const attrs = `data-measurement-value ${readOnly ? "readonly" : ""}`;
  if (definition.value_type === "BOOLEAN") {
    const trueLabel = definition.governed_field === "explicit_flag" ? "Explicit" : "True";
    const falseLabel = definition.governed_field === "explicit_flag" ? "Not Explicit" : "False";
    return `<select ${attrs} ${readOnly ? "disabled" : ""}><option value="">Select…</option><option value="true" ${value === true ? "selected" : ""}>${trueLabel}</option><option value="false" ${value === false ? "selected" : ""}>${falseLabel}</option></select>`;
  }
  if (definition.value_type === "VOCABULARY_TERM") {
    const plan = JSON.parse(decodeURIComponent(definition.plan));
    return `<select ${attrs}><option value="">Select registered term…</option>${plan.vocabulary_terms.filter(item => item.vocabulary_key === definition.vocabulary_key).map(item => `<option value="${escapeHtml(item.term_key)}">${escapeHtml(item.term_key)} — ${escapeHtml(item.term_definition)}</option>`).join("")}</select>`;
  }
  const type = definition.value_type === "DATE" ? "date" : definition.value_type === "INTEGER" || definition.value_type === "DECIMAL" ? "number" : "text";
  const step = definition.value_type === "DECIMAL" ? ' step="any"' : "";
  return `<input ${attrs} type="${type}"${step} value="${escapeHtml(String(value ?? ""))}" ${readOnly ? "readonly" : ""}>`;
}

function isEditableExplicitObservation(measurement, subject) {
  return measurement.authority === "DIRECT_OBSERVATION" &&
    measurement.value_type === "BOOLEAN" &&
    subject.subject_kind === "PLACEMENT_FIELD" &&
    subject.governed_field === "explicit_flag";
}

function updateExplicitObservationDraft(subject, row) {
  const trackOrdinal = Number(subject.dataset.trackOrdinal);
  const valueControl = row.querySelector("[data-measurement-value]");
  const sourceControl = row.querySelector("[data-measurement-source]");
  if (!trackOrdinal || !valueControl || !sourceControl) return;
  const draft = JSON.parse(proposal.value);
  const track = draft.tracks?.[trackOrdinal - 1];
  if (!track) return;
  track.explicit_flag = valueControl.value === "" ? null : valueControl.value === "true";
  track.evidence = (track.evidence || []).filter(link => link.field_name !== "explicit_flag");
  if (sourceControl.value) track.evidence.push({
    source_key: sourceControl.value,
    field_name: "explicit_flag",
    provenance_type: "DIRECT_OBSERVATION",
    support_status: "FULL",
  });
  proposal.value = JSON.stringify(draft, null, 2);
  markWorksheetSynchronizedWithProposal();
  invalidateValidation("Direct observation changed. Preview and validate the proposal again before ingestion.");
}

function updateTargetObservationDraft(subject, row) {
  const trackOrdinal = Number(subject.dataset.trackOrdinal);
  if (!trackOrdinal) return;
  const draft = JSON.parse(proposal.value);
  const track = draft.tracks?.[trackOrdinal - 1];
  if (!track) return;
  const valueControl = row.querySelector("[data-measurement-value]");
  track.explicit_flag = valueControl.value === "" ? null : valueControl.value === "true";
  track.evidence = (track.evidence || []).filter(link => link.field_name !== "explicit_flag");
  row.querySelectorAll("[data-measurement-source]").forEach(control => {
    const duplicate = (track.evidence || []).some(link =>
      link.source_key === control.value && link.field_name === control.dataset.evidenceField);
    if (control.value && !duplicate) track.evidence.push({
      source_key: control.value,
      field_name: control.dataset.evidenceField,
      provenance_type: "DIRECT_OBSERVATION",
      support_status: "FULL",
    });
  });
  proposal.value = JSON.stringify(draft, null, 2);
  markWorksheetSynchronizedWithProposal();
  invalidateValidation("Target observation or identity evidence changed. Preview and validate the proposal again before ingestion.");
}

function renderStructuredWorksheet() {
  const host = $("#structured-evaluation-constraints");
  const builtProposal = JSON.parse(proposal.value);
  const evidenceSources = builtProposal.evidence_sources || [];
  host.innerHTML = structuredWorksheet.constraints.map(item => {
    const definition = item.definition;
    const plan = definition.structured_evaluation_plan;
    const authorityPanels = item.subjects.map(subject => {
      const context = subject.displayed_context;
      const identity = subject.subject_kind === "RUN" ? "Run-level subject" : `Placement ${subject.track_observed_ordinal}: ${context?.title || "Untitled"} — ${context?.artist || "Unknown artist"}`;
      const targetSpecific = plan.subject_selector.evaluator_key === "selector.exact_displayed_title_artist";
      const measurementControls = item.selection_state === "TARGET_AMBIGUOUS" ? '<p class="warning">TARGET_AMBIGUOUS — this placement is retained for audit only. No observation is requested because the registered selector did not identify a unique target.</p>' : plan.measurement_definitions.map(measurement => {
        let autoValue = null;
        if (measurement.authority === "STRUCTURAL_DERIVATION") {
          const derived = item.derived_measurements.find(row => row.subject_key === subject.subject_key && row.measurement_key === measurement.measurement_key);
          autoValue = derived?.boolean_value ?? derived?.integer_value ?? derived?.decimal_value ?? derived?.text_value ?? derived?.date_value ?? derived?.vocabulary_term_key ?? null;
        }
        if (measurement.authority === "DIRECT_OBSERVATION" && subject.subject_kind === "PLACEMENT_FIELD") autoValue = governedFieldValue(subject);
        const editableExplicit = isEditableExplicitObservation(measurement, subject);
        const locked = measurement.authority === "STRUCTURAL_DERIVATION" || (measurement.authority === "DIRECT_OBSERVATION" && !editableExplicit);
        const placement = builtProposal.tracks?.[subject.track_observed_ordinal - 1];
        const evidenceField = evidenceFieldForGovernedField(subject.governed_field);
        const eligibleKeys = measurement.authority === "DIRECT_OBSERVATION" && !editableExplicit ? new Set((placement?.evidence || []).filter(link => link.field_name === evidenceField).map(link => link.source_key)) : null;
        const eligibleSources = editableExplicit ? evidenceSources.filter(source => source.source_type === "SCREENSHOT") : eligibleKeys === null ? evidenceSources : evidenceSources.filter(source => eligibleKeys.has(source.source_key));
        const options = eligibleSources.map(source => `<option value="${escapeHtml(source.source_key)}">${escapeHtml(source.source_key)} — ${escapeHtml(source.source_reference)}</option>`).join("");
        const role = measurement.authority === "EXTERNAL_FACT_VERIFICATION" ? "EXTERNAL_FACT" : measurement.authority === "HUMAN_ASSESSMENT" ? "OPERATOR_JUDGMENT" : "OBSERVED_VALUE";
        const roleControl = measurement.authority === "HUMAN_ASSESSMENT" ? '<label>Judgment evidence role<select data-evidence-role><option value="OPERATOR_JUDGMENT">Operator judgment</option><option value="CORRESPONDENCE">Correspondence judgment</option></select></label>' : '';
        const unavailableControl = measurement.authority !== "STRUCTURAL_DERIVATION" && measurement.unavailable_policy === "MAY_BE_UNAVAILABLE" ? '<label class="unknown-control"><input type="checkbox" data-unavailable> Record UNKNOWN / unavailable</label><label>Unavailable reason<input data-unavailable-reason type="text" disabled></label>' : '';
        const targetIdentity = targetSpecific ? `<p class="hint">Neutral target-state observation. FAIL means the unique target displayed Explicit; it does not mean Condition A violated its prompt.</p><label>Displayed-title identity evidence<select data-measurement-source data-evidence-field="title" data-evidence-role="SUBJECT_IDENTITY"><option value="">Select explicitly…</option>${options}</select></label><label>Displayed-artist identity evidence<select data-measurement-source data-evidence-field="artist" data-evidence-role="SUBJECT_IDENTITY"><option value="">Select explicitly…</option>${options}</select></label>` : "";
        const observedEvidence = measurement.evidence_required ? `<label>Observed-value evidence<select data-measurement-source data-evidence-field="${escapeHtml(evidenceField)}" data-evidence-role="OBSERVED_VALUE"><option value="">Select explicitly…</option>${options}</select></label>` : "";
        return `<div class="structured-measurement" data-structured-measurement data-key="${escapeHtml(measurement.measurement_key)}" data-authority="${measurement.authority}" data-value-type="${measurement.value_type}" data-evidence-required="${measurement.evidence_required}" data-role="${role}" data-editable-explicit="${editableExplicit}" data-target-specific="${targetSpecific}"><strong>${escapeHtml(measurement.measurement_key)}</strong><span class="authority-badge">${escapeHtml(measurement.authority.replaceAll("_", " "))}</span>${measurement.authority === "STRUCTURAL_DERIVATION" ? `<p class="hint">Derived by ${escapeHtml(measurement.derivation_key)}/${escapeHtml(measurement.derivation_version)} from governed Experiment input.</p>` : ""}${typedInput({...measurement, governed_field: subject.governed_field, plan: encodeURIComponent(JSON.stringify(plan))}, autoValue, locked)}${unavailableControl}${roleControl}${targetIdentity}${observedEvidence}${measurement.authority !== "STRUCTURAL_DERIVATION" ? '<label>Recorded by<input data-recorded-by type="text" value="Workbench operator"></label>' : ''}${measurement.authority === "HUMAN_ASSESSMENT" ? '<p class="warning">HUMAN ASSESSMENT — explicit operator judgment, not direct observation.</p>' : ""}</div>`;
      }).join("");
      return `<article class="structured-subject" data-structured-subject data-definition-id="${definition.id}" data-ordinal="${subject.enumeration_ordinal}" data-subject-kind="${subject.subject_kind}" data-track-ordinal="${subject.track_observed_ordinal || ""}" data-governed-field="${subject.governed_field || ""}"><h4>${escapeHtml(identity)}</h4>${subject.governed_field ? `<p class="locked-value">Governed field ${escapeHtml(subject.governed_field)}: ${escapeHtml(String(governedFieldValue(subject) ?? "Not supplied"))}</p>` : ""}${measurementControls}<div class="subject-result" data-subject-result>Not calculated</div></article>`;
    }).join("");
    const selectionNotice = item.selection_state === "TARGET_ABSENT" ? '<p class="warning">TARGET_ABSENT — no accepted exact displayed title-and-artist representation was found. No placement or Boolean observation was manufactured.</p>' : item.selection_state === "TARGET_AMBIGUOUS" ? '<p class="warning">TARGET_AMBIGUOUS — multiple exact matches were retained below for audit. No placement was selected.</p>' : "";
    return `<section class="structured-constraint" data-structured-constraint="${definition.id}"><h3>${escapeHtml(definition.constraint_key)} · ${escapeHtml(definition.constraint_text)}</h3><dl><dt>Evaluation rule</dt><dd>${escapeHtml(definition.evaluation_rule)}</dd><dt>Plan</dt><dd>${escapeHtml(plan.instrumentation_version)}</dd><dt>Subject selector</dt><dd>${escapeHtml(plan.subject_selector.evaluator_key)}/${escapeHtml(plan.subject_selector.evaluator_version)}</dd><dt>Subject evaluator</dt><dd>${escapeHtml(plan.subject_evaluator.evaluator_key)}/${escapeHtml(plan.subject_evaluator.evaluator_version)}</dd><dt>Aggregate evaluator</dt><dd>${escapeHtml(plan.aggregate_evaluator.evaluator_key)}/${escapeHtml(plan.aggregate_evaluator.evaluator_version)}</dd><dt>Completeness</dt><dd>${plan.require_complete_subject_set ? "Complete frozen subject set required" : "Registered partial subject set"}</dd></dl>${selectionNotice}${authorityPanels}<div class="aggregate-result" data-aggregate-result>Aggregate not calculated</div></section>`;
  }).join("");
  host.querySelectorAll("[data-unavailable]").forEach(box => box.addEventListener("change", () => {
    const row = box.closest("[data-structured-measurement]");
    row.querySelector("[data-measurement-value]").disabled = box.checked || row.dataset.authority === "STRUCTURAL_DERIVATION" || row.dataset.authority === "DIRECT_OBSERVATION";
    row.querySelector("[data-unavailable-reason]").disabled = !box.checked;
    structuredPreviewComplete = false; $("#ingest").disabled = true;
  }));
  host.querySelectorAll('[data-editable-explicit="true"]').forEach(row => {
    const subject = row.closest("[data-structured-subject]");
    row.querySelectorAll("[data-measurement-value],[data-measurement-source]").forEach(control =>
      control.addEventListener("change", () => row.dataset.targetSpecific === "true" ? updateTargetObservationDraft(subject, row) : updateExplicitObservationDraft(subject, row)));
  });
  host.querySelectorAll("input,select").forEach(control => control.addEventListener("change", () => { structuredPreviewComplete = false; $("#ingest").disabled = true; }));
}

async function loadStructuredWorksheet(builtProposal) {
  const panel = $("#structured-evaluation-panel"); panel.hidden = false;
  const proposalSnapshot = proposal.value;
  $("#preview-structured-evaluation").disabled = true;
  $("#rebuild-structured-evaluation").disabled = true;
  setLocalStatus("#structured-evaluation-status", "Enumerating frozen subjects…", "busy");
  setLocalStatus("#structured-worksheet-state", "Building worksheet from the current proposal…", "busy");
  try {
    const response = await fetch(`/api/study-runs/${plannedRunContext.run_id}/structured-worksheet`, {method: "POST", headers: apiHeaders({"Content-Type": "application/json"}), body: JSON.stringify({proposal: builtProposal})});
    const worksheet = await readJsonResponse(response, "Structured worksheet");
    if (proposal.value !== proposalSnapshot) {
      invalidateStructuredWorksheet("The proposal changed while the worksheet was building. Rebuild it from the current proposal before preview or realization.");
      return;
    }
    structuredWorksheet = worksheet;
    structuredWorksheetProposalSnapshot = proposalSnapshot;
    renderStructuredWorksheet();
    $("#preview-structured-evaluation").disabled = false;
    $("#rebuild-structured-evaluation").disabled = true;
    setLocalStatus("#structured-evaluation-status", `${structuredWorksheet.constraints.length} structured constraint worksheet(s) ready. Subjects are read-only.`, "success");
    setLocalStatus("#structured-worksheet-state", "Worksheet is aligned with the current proposal.", "success");
  } catch (error) {
    structuredWorksheet = null;
    structuredWorksheetProposalSnapshot = null;
    $("#preview-structured-evaluation").disabled = true;
    $("#rebuild-structured-evaluation").disabled = proposal.value.trim() === "";
    setLocalStatus("#structured-evaluation-status", `Structured worksheet unavailable: ${error.message}. The Experiment draft remains intact.`, "error");
    setLocalStatus("#structured-worksheet-state", "No current worksheet is available. The proposal was not changed.", "error");
  }
}

async function rebuildStructuredWorksheet() {
  let currentProposal;
  try {
    currentProposal = JSON.parse(proposal.value);
  } catch (error) {
    setLocalStatus("#structured-worksheet-state", `Cannot rebuild worksheet: current proposal JSON is invalid (${error.message}).`, "error");
    return;
  }
  await loadStructuredWorksheet(currentProposal);
}

function measurementPayload(row, subject) {
  const unavailable = row.querySelector("[data-unavailable]")?.checked || false;
  const valueType = unavailable ? "UNAVAILABLE" : row.dataset.valueType;
  const result = {measurement_key: row.dataset.key, authority_kind: row.dataset.authority,
    value_type: valueType, recorded_by: row.querySelector("[data-recorded-by]")?.value || "",
    unavailable_reason: unavailable ? row.querySelector("[data-unavailable-reason]").value || null : null, evidence: []};
  if (!unavailable) {
    const value = row.querySelector("[data-measurement-value]").value;
    const key = ({BOOLEAN: "boolean_value", INTEGER: "integer_value", DECIMAL: "decimal_value", TEXT: "text_value", DATE: "date_value", VOCABULARY_TERM: "vocabulary_term_key"})[valueType];
    if (value !== "") result[key] = valueType === "BOOLEAN" ? value === "true" : valueType === "INTEGER" ? Number.parseInt(value, 10) : valueType === "DECIMAL" ? Number(value) : value;
  }
  row.querySelectorAll("[data-measurement-source]").forEach(control => {
    if (control.value) result.evidence.push({source_key: control.value, evidence_link_field: control.dataset.evidenceField || (row.dataset.authority === "DIRECT_OBSERVATION" ? evidenceFieldForGovernedField(subject.dataset.governedField) : null),
      evidence_role: control.dataset.evidenceRole || row.querySelector("[data-evidence-role]")?.value || row.dataset.role, provenance_type: row.dataset.authority === "HUMAN_ASSESSMENT" ? "HUMAN_ASSESSMENT" : "DIRECT_OBSERVATION", support_status: "FULL"});
  });
  return result;
}

function collectStructuredEvaluation() {
  return {constraints: [...document.querySelectorAll("[data-structured-constraint]")].map(constraint => ({
    study_constraint_definition_id: Number(constraint.dataset.structuredConstraint),
    subjects: [...constraint.querySelectorAll("[data-structured-subject]")].map(subject => ({
      subject_kind: subject.dataset.subjectKind, enumeration_ordinal: Number(subject.dataset.ordinal),
      track_observed_ordinal: subject.dataset.trackOrdinal ? Number(subject.dataset.trackOrdinal) : null,
      governed_field: subject.dataset.governedField || null,
      measurements: [...subject.querySelectorAll("[data-structured-measurement]")].filter(row => row.dataset.authority !== "STRUCTURAL_DERIVATION").map(row => measurementPayload(row, subject)),
    })),
  }))};
}

async function previewStructuredEvaluation() {
  if (!structuredWorksheetIsCurrent()) {
    invalidateStructuredWorksheet();
    return;
  }
  try {
    const response = await fetch(`/api/study-runs/${plannedRunContext.run_id}/structured-preview`, {method: "POST", headers: apiHeaders({"Content-Type": "application/json"}), body: JSON.stringify({proposal: JSON.parse(proposal.value), structured_evaluation: collectStructuredEvaluation()})});
    const body = await readJsonResponse(response, "Structured preview");
    body.constraints.forEach(item => {
      const host = document.querySelector(`[data-structured-constraint="${item.study_constraint_definition_id}"]`);
      item.subject_results.forEach(result => { const row = host.querySelector(`[data-ordinal="${result.subject.enumeration_ordinal}"] [data-subject-result]`); row.textContent = `${result.status} — ${result.reason_code} (${result.evaluator_key}/${result.evaluator_version})`; });
      host.querySelector("[data-aggregate-result]").textContent = item.aggregate_constraint_result ? `${item.aggregate_constraint_result.status} — ${item.aggregate_constraint_result.reason_code} (${item.aggregate_constraint_result.aggregate_evaluator_key}/${item.aggregate_constraint_result.aggregate_evaluator_version})` : `INCOMPLETE — ${item.issues.map(issue => issue.message).join("; ")}`;
    });
    structuredPreviewComplete = body.complete;
    setLocalStatus("#structured-evaluation-preview", body.complete ? "Structured evaluation complete. Atomic realization is available after governed proposal validation." : `Structured evaluation incomplete: ${body.constraints.flatMap(item => item.issues.map(issue => issue.message)).join("; ")}`, body.complete ? "success" : "error");
    $("#ingest").disabled = !(structuredPreviewComplete && validatedProposalSnapshot === proposal.value);
  } catch (error) {
    structuredPreviewComplete = false; $("#ingest").disabled = true;
    setLocalStatus("#structured-evaluation-preview", `Structured preview failed: ${error.message}. The Experiment draft remains intact.`, "error");
  }
}

async function ingestProposal() {
  if (ingestionActive) return;
  const requiresStructured = Boolean(plannedRunContext?.constraints.some(item => item.structured_evaluation_plan));
  if (requiresStructured && (!structuredPreviewComplete || !structuredWorksheetIsCurrent())) {
    invalidateStructuredWorksheet();
    setLocalStatus("#ingest-status", "Rebuild and preview the structured worksheet for the current proposal before ingestion.", "error");
    return;
  }
  if (!validatedProposalSnapshot || validatedProposalSnapshot !== proposal.value) {
    setLocalStatus("#ingest-status", "Validate the current proposal before ingestion.", "error");
    return;
  }
  if (!window.confirm("Ingest exactly this one reviewed record?")) {
    setLocalStatus("#ingest-status", "Ingestion cancelled. No write occurred.", "idle");
    return;
  }
  ingestionActive = true;
  const button = $("#ingest");
  const finish = beginOperation(button, "#ingest-status", "Ingesting one reviewed record");
  try {
    const structured = Boolean(plannedRunContext?.constraints.some(item => item.structured_evaluation_plan));
    const endpoint = plannedRunContext ? `/api/study-runs/${plannedRunContext.run_id}/${structured ? "realize-structured-experiment" : "realize-experiment"}` : "/api/ingest";
    const bodyValue = plannedRunContext ? {proposal: JSON.parse(proposal.value), ...(structured ? {structured_evaluation: collectStructuredEvaluation()} : {})} : requestBody();
    const response = await fetch(endpoint, {method: "POST", headers: apiHeaders({"Content-Type": "application/json"}), body: JSON.stringify(bodyValue)});
    const body = await readJsonResponse(response, "Ingestion");
    show(body);
    renderReadback(body.record, body.kind);
    setLocalStatus("#ingest-status", `Ingestion successful. ${body.kind} ${body.record_id} was inserted and read back.`, "success");
    validatedProposalSnapshot = null;
    if (plannedRunContext) {
      if (structured) {
        plannedRunContext = {...plannedRunContext, terminal: true, experiment_id: body.record_id};
        sessionStorage.setItem("pne-planned-run", JSON.stringify(plannedRunContext));
        await renderPersistedStructuredRun();
      } else {
        sessionStorage.removeItem("pne-planned-run");
        plannedRunContext = null;
      }
    }
  } catch (error) {
    const message = `Ingestion failed: ${error.message}`;
    setLocalStatus("#ingest-status", message, "error");
    show({error: message});
  } finally {
    ingestionActive = false;
    finish();
    $("#ingest").disabled = true;
  }
}

function addRow(templateSelector, containerSelector) {
  const fragment = $(templateSelector).content.cloneNode(true);
  const row = fragment.querySelector("article");
  row.querySelector(".remove").addEventListener("click", () => {
    row.remove();
    if (!$(containerSelector).children.length) $(containerSelector).innerHTML = `<p class="empty">None declared.</p>`;
    invalidateValidation();
    refreshReadiness();
  });
  row.querySelectorAll("[data-field]").forEach(input => {
    input.addEventListener("change", () => { invalidateValidation(); refreshReadiness(); });
    input.addEventListener("input", () => { invalidateValidation(); refreshReadiness(); });
  });
  const sourceSelect = row.querySelector("[data-field='source_key']");
  if (sourceSelect) sourceOptions(sourceSelect);
  const container = $(containerSelector);
  container.querySelector(".empty")?.remove();
  container.append(fragment);
  invalidateValidation();
  refreshReadiness();
}

function invalidateConfirmation() {
  confirmedTracks = null;
  $("#confirmed-summary").textContent = "Draft changed after review. Confirm the tracklist again.";
  $("#confirmed-summary").classList.remove("confirmed");
  invalidateValidation();
  refreshReadiness();
}

function draftValues(row) {
  const value = {};
  row.querySelectorAll("[data-field]").forEach(input => {
    if (input.type === "checkbox") value[input.dataset.field] = input.checked;
    else if (input.type === "number") value[input.dataset.field] = input.value === "" ? null : Number(input.value);
    else if (input instanceof HTMLSelectElement && input.multiple) value[input.dataset.field] = [...input.selectedOptions].map(option => option.value);
    else if (input.hasAttribute("data-boolean")) value[input.dataset.field] = input.value === "" ? null : input.value === "true";
    else value[input.dataset.field] = input.value || null;
  });
  return value;
}

function allDraftValues() {
  return [...document.querySelectorAll("#draft-tracks .draft-row")].map(draftValues);
}

function populateDraftRow(row, values = {}) {
  row.querySelectorAll("[data-field]").forEach(input => {
    let value = values[input.dataset.field];
    if (input.dataset.field === "canonical_identity_established" && value == null) value = false;
    if (input.dataset.field === "provenance_type" && value == null) value = "DIRECT_OBSERVATION";
    if (input.type === "checkbox") input.checked = Boolean(value);
    else if (input instanceof HTMLSelectElement && input.multiple) sourceOptions(input, value || []);
    else if (input.hasAttribute("data-boolean")) input.value = value === true ? "true" : value === false ? "false" : "";
    else input.value = value ?? "";
  });
}

function addDraftRow(values = {}, before = null) {
  const fragment = $("#draft-template").content.cloneNode(true);
  const row = fragment.querySelector("article");
  populateDraftRow(row, values);
  row.querySelectorAll("[data-field]").forEach(input => {
    const changed = () => { invalidateConfirmation(); refreshDraftReview(); };
    input.addEventListener("change", changed);
    input.addEventListener("input", changed);
  });
  row.querySelector("[data-remove]").addEventListener("click", () => { row.remove(); invalidateConfirmation(); refreshDraftReview(); });
  row.querySelector("[data-move-up]").addEventListener("click", () => {
    if (row.previousElementSibling) row.parentElement.insertBefore(row, row.previousElementSibling);
    invalidateConfirmation(); refreshDraftReview();
  });
  row.querySelector("[data-move-down]").addEventListener("click", () => {
    if (row.nextElementSibling) row.parentElement.insertBefore(row.nextElementSibling, row);
    invalidateConfirmation(); refreshDraftReview();
  });
  row.querySelector("[data-split]").addEventListener("click", () => {
    const copy = {...draftValues(row), review_status: "UNREVIEWED"};
    addDraftRow(copy, row.nextElementSibling); invalidateConfirmation(); refreshDraftReview();
  });
  const container = $("#draft-tracks");
  container.querySelector(".empty")?.remove();
  if (before) container.insertBefore(fragment, before); else container.append(fragment);
  refreshDraftReview();
}

function refreshDraftReview() {
  const rows = [...document.querySelectorAll("#draft-tracks .draft-row")];
  rows.forEach((row, index) => {
    const position = row.querySelector("[data-field='proposed_position']").value;
    row.querySelector("[data-row-label]").textContent = `Track ${position || index + 1}`;
  });
  if (!rows.length) $("#draft-tracks").innerHTML = `<p class="empty">No draft tracks.</p>`;
  const groups = new Map();
  allDraftValues().forEach((track, index) => {
    const identity = `${track.proposed_title || ""}\u0000${track.proposed_artist || ""}`.trim().toLocaleLowerCase();
    if (identity !== "") groups.set(identity, [...(groups.get(identity) || []), index + 1]);
  });
  const overlaps = [...groups.values()].filter(indices => indices.length > 1);
  $("#overlap-suggestions").textContent = overlaps.length
    ? overlaps.map(indices => `Possible overlap: tracks ${indices.join(" and ")}. Expand row tools only if correction is needed.`).join(" ")
    : "";
  $("#raw-draft").textContent = JSON.stringify(allDraftValues(), null, 2);
}

async function generateDraft(draftGenerationFlow, provider, suppliedText = null) {
  const sourceKeys = provider === "automatic" || provider === "structured_json"
    ? stagedEvidence.map((item, index) => `source_${index + 1}`)
    : [...$("#draft-sources").selectedOptions].map(option => option.value);
  if (provider === "automatic" && !sourceKeys.length) throw new Error("Stage at least one screenshot before extracting a tracklist");
  const automatic = provider === "automatic";
  const button = automatic ? $("#generate-tracks") : provider === "structured_json" ? $("#import-draft") : $("#load-draft");
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  try {
    const body = await draftGenerationFlow.run({
      button,
      status: provider === "structured_json" ? $("#import-status") : $("#extraction-status"),
      loadingText: automatic ? "Generating draft tracklist" : provider === "structured_json" ? "Importing draft tracklist" : "Loading draft",
      invoke: async () => {
        const response = await fetch("/api/generate-draft-tracklist", {
          method: "POST", headers: apiHeaders({"Content-Type": "application/json"}),
          body: JSON.stringify({provider, source_keys: sourceKeys, supplied_text: suppliedText}),
          signal: controller.signal
        });
        const contentType = response.headers.get("Content-Type") || "";
        const result = contentType.includes("application/json") ? await response.json() : null;
        if (!response.ok) {
          const detail = result?.error || `Workbench server returned ${response.status}. Restart it to load the current generation provider route.`;
          throw new Error(detail);
        }
        return result;
      },
      acceptDrafts: draftTracks => {
        acceptedExtractionContinuity = null;
        if (provider === "automatic" || provider === "structured_json") {
          $("#draft-tracks").innerHTML = "";
        }
        draftTracks.forEach(track => addDraftRow(track));
        if (!draftTracks.length) refreshDraftReview();
      }
    });
    if (body.available) invalidateConfirmation();
    show({draft_only: true, ...body});
  } catch (error) {
    if (error.name === "AbortError") {
      const detail = "The provider request timed out. Restart the workbench and try again.";
      $("#extraction-status").textContent = `Draft generation did not complete. ${detail}`;
      throw new Error(detail);
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

function draftImportFailureMessage(error) {
  const detail = error?.message || "unexpected client or server failure";
  return `Draft import failed: ${detail}`;
}

async function importDraftTracklist(draftGenerationFlow, event) {
  event?.preventDefault();
  const button = $("#import-draft");
  const status = $("#import-status");
  try {
    await generateDraft(draftGenerationFlow, "structured_json", $("#structured-draft").value);
  } catch (error) {
    const message = draftImportFailureMessage(error);
    status.textContent = message;
    show({error: message});
  } finally {
    // This outer guard also terminates visibly if the shared generation helper
    // was unavailable before it could enter its own finally block.
    button.disabled = false;
    button.textContent = "Import draft tracklist";
  }
}

function mergeSelectedDrafts() {
  const selected = [...document.querySelectorAll("#draft-tracks .draft-row")].filter(row => row.querySelector("[data-select-row]").checked);
  if (selected.length < 2) throw new Error("Select at least two draft rows to merge");
  const values = selected.map(draftValues);
  const merged = {source_keys: [...new Set(values.flatMap(item => item.source_keys || []))], ambiguity_flag: true, review_status: "UNREVIEWED"};
  for (const field of ["proposed_position", "proposed_title", "proposed_artist", "proposed_version_remaster_text", "canonical_identity_established", "provenance_type"]) {
    const supplied = [...new Set(values.map(item => item[field]).filter(value => value !== null && value !== ""))];
    if (supplied.length > 1) throw new Error(`Selected rows disagree on ${field}; edit them before merging`);
    merged[field] = supplied[0] ?? null;
  }
  selected.forEach(row => row.remove());
  addDraftRow(merged);
  invalidateConfirmation();
}

function confirmReviewedTracks() {
  const drafts = allDraftValues();
  if (!drafts.length) throw new Error("There are no draft tracks to confirm");
  confirmedTracks = drafts.map(track => ({
    absolute_position: track.proposed_position,
    title: track.proposed_title,
    artist: track.proposed_artist,
    version_or_remaster_text: track.proposed_version_remaster_text,
    source_keys: track.source_keys,
    canonical_identity_established: track.canonical_identity_established,
    provenance_type: track.provenance_type,
    notes: track.ambiguity_flag ? "Reviewer marked this track uncertain." : null
  }));
  $("#confirmed-summary").textContent = `${confirmedTracks.length} reviewed track${confirmedTracks.length === 1 ? "" : "s"} confirmed for proposal assembly.`;
  $("#confirmed-summary").classList.add("confirmed");
  show({confirmed: true, track_count: confirmedTracks.length, message: "Human-reviewed rows may now be used by proposal construction."});
  invalidateValidation();
  refreshReadiness();
}

function updateMode() {
  const historical = kind.value === "historical_experiment";
  $("#historical-fields").hidden = !historical;
  $("#artifact-fields").hidden = historical;
  proposal.value = "";
  confirmedTracks = null;
  $("#prompt-attested").checked = false;
  $("#confirmed-summary").textContent = "No tracklist confirmed.";
  $("#confirmed-summary").classList.remove("confirmed");
  invalidateValidation("Mode changed. Build and validate a new proposal.");
  invalidateStructuredWorksheet("Mode changed. Build a new proposal before rebuilding the structured worksheet.");
  show("Mode selected. No operation performed.");
  refreshReadiness();
}

function resetForNextExperiment() {
  document.querySelectorAll("main input, main textarea, main select").forEach(control => {
    if (control.type === "checkbox" || control.type === "radio") control.checked = control.defaultChecked;
    else if (control instanceof HTMLSelectElement) control.selectedIndex = 0;
    else control.value = control.defaultValue;
  });
  stagedEvidence.splice(0, stagedEvidence.length);
  confirmedTracks = null;
  acceptedExtractionContinuity = null;
  validatedProposalSnapshot = null;
  ingestionActive = false;
  pendingSourceDeclarations = null;
  window.ScreenshotExtractionReview.discard($("#screenshot-extraction-review"));
  $("#draft-tracks").innerHTML = '<p class="empty">No draft tracks.</p>';
  $("#evidence-links").innerHTML = '<p class="empty">No additional evidence links declared.</p>';
  $("#proposal").value = "";
  $("#confirmed-summary").textContent = "No tracklist confirmed.";
  $("#confirmed-summary").classList.remove("confirmed");
  $("#import-status").textContent = "No structured draft imported.";
  $("#extraction-status").textContent = "Stage screenshots, then generate a draft tracklist.";
  $("#build-status").textContent = "No proposal built.";
  $("#validation-status").textContent = "No validation performed.";
  $("#ingest-status").textContent = "No ingestion performed.";
  $("#readback-summary").innerHTML = "";
  $("#result").textContent = "No operation performed.";
  $("#ingest").disabled = true;
  renderStaged();
  updateMode();
  window.scrollTo({top: 0, behavior: "smooth"});
}

function updateCompleteness() {
  const hidden = $("#completeness").value === "NOT_OBSERVED";
  document.querySelectorAll(".boundary-field").forEach(field => field.hidden = hidden);
  invalidateValidation();
  refreshReadiness();
}

function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, character => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"})[character]);
}

function initializeDraftTrackWorkflow() {
  const draftGenerationFlow = resolveDraftGenerationFlow();
  if (!draftGenerationFlow) {
    const message = "Workbench initialization failed: draft-track workflow unavailable.";
    setDraftWorkflowAvailability(false, message);
    show({error: message});
    return null;
  }
  setDraftWorkflowAvailability(true);
  $("#generate-tracks").addEventListener("click", () => generateDraft(draftGenerationFlow, "automatic").catch(error => show({error: error.message})));
  $("#import-draft").addEventListener("click", event => importDraftTracklist(draftGenerationFlow, event));
  $("#load-draft").addEventListener("click", () => generateDraft(draftGenerationFlow, "delimited_text", $("#draft-text").value).catch(error => show({error: error.message})));
  return draftGenerationFlow;
}

function initializePlannedRunContext() {
  if (!plannedRunContext) return;
  kind.value = "historical_experiment";
  kind.disabled = true;
  $("#planned-run-context").hidden = false;
  $("#prompt").value = plannedRunContext.prompt;
  $("#prompt").readOnly = true;
  $("#source-system").value = plannedRunContext.source_system || "";
  $("#source-system").readOnly = true;
  $("#planned-run-summary").innerHTML = `<dl><dt>Study</dt><dd>${escapeHtml(plannedRunContext.study_key)}</dd><dt>Protocol version</dt><dd>${plannedRunContext.protocol_version}</dd><dt>Run</dt><dd>${escapeHtml(plannedRunContext.run_key)}</dd><dt>Exact planned prompt</dt><dd class="locked-value">${escapeHtml(plannedRunContext.prompt)}</dd></dl><h3>Frozen constraints and run-specific results</h3>${plannedRunContext.constraints.map(definition => definition.structured_evaluation_plan ? `<article class="study-row"><strong>${escapeHtml(definition.constraint_key)} · ${escapeHtml(definition.constraint_text)}</strong><p class="hint">STRUCTURED_REQUIRED — deterministic results are collected in the worksheet after proposal construction.</p></article>` : `<article class="study-row"><strong>${escapeHtml(definition.constraint_key)} · ${escapeHtml(definition.constraint_text)}</strong><p class="hint">LEGACY_AGGREGATE_ONLY · ${escapeHtml(definition.constraint_type)} · provenance ${escapeHtml(definition.permitted_result_provenance)}</p><div class="form-grid"><label>Result status<select data-study-result-status="${definition.id}"><option>UNKNOWN</option><option>PASS</option><option>PARTIAL</option><option>FAIL</option></select></label><label>Evidence/evaluation text<textarea class="short" data-study-result-evidence="${definition.id}"></textarea></label></div></article>`).join("")}`;
  document.querySelectorAll("[data-study-result-status],[data-study-result-evidence]").forEach(control => control.addEventListener("change", invalidateValidation));
  if (plannedRunContext.terminal) {
    document.querySelectorAll("main input, main select, main textarea, main button").forEach(control => {
      if (control.id !== "leave-planned-run") control.disabled = true;
    });
    $("#leave-planned-run").disabled = false;
    $("#leave-planned-run").textContent = "Return to Studies";
    renderPersistedStructuredRun();
  }
  $("#leave-planned-run").onclick = () => {
    if (!plannedRunContext.terminal && !confirm("Leave this planned-run execution? No Study outcome will be recorded.")) return;
    sessionStorage.removeItem("pne-planned-run");
    location.href = plannedRunContext.terminal ? "/studies.html" : location.href;
  };
}

async function renderPersistedStructuredRun() {
  $("#structured-evaluation-panel").hidden = false;
  try {
    const response = await fetch(`/api/study-runs/${plannedRunContext.run_id}/structured-evaluation`, {headers: apiHeaders()});
    const body = await readJsonResponse(response, "Persisted structured evaluation");
    $("#structured-evaluation-constraints").innerHTML = body.constraints.map(item => `<section class="structured-constraint"><h3>${escapeHtml(item.definition.constraint_key)} · terminal governed evaluation</h3><p class="aggregate-result">${escapeHtml(item.aggregate.status)} — ${escapeHtml(item.aggregate.provenance_notes || "Deterministically aggregated")}</p>${item.structured.subjects.map(subject => `<article class="structured-subject"><strong>${escapeHtml(subject.subject_key)}</strong><p>${escapeHtml(subject.result.status)} — ${escapeHtml(subject.result.reason_code)}</p><details><summary>Persisted provenance</summary><pre>${escapeHtml(JSON.stringify(subject, null, 2))}</pre></details></article>`).join("")}</section>`).join("");
    $("#preview-structured-evaluation").hidden = true;
    $("#rebuild-structured-evaluation").hidden = true;
    setLocalStatus("#structured-evaluation-status", `Terminal realization read from governed persistence. Experiment ${body.experiment.id}.`, "success");
    setLocalStatus("#structured-evaluation-preview", "Instrumentation classification: STRUCTURED_DERIVABLE. No post-realization edits are available.", "success");
  } catch (error) {
    setLocalStatus("#structured-evaluation-status", `Persisted structured evaluation unavailable: ${error.message}`, "error");
  }
}

kind.addEventListener("change", updateMode);
$("#completeness").addEventListener("change", updateCompleteness);
$("#requested-count-state").addEventListener("change", updateRequestedTrackCountState);
$("#saved").addEventListener("change", updateSavedStatus);
$("#stage").addEventListener("click", stageEvidence);
$("#submit-next-experiment").addEventListener("click", resetForNextExperiment);
if (typeof document.getElementById === "function" && document.getElementById("extract-screenshots")) {
  $("#extract-screenshots").addEventListener("click", extractScreenshotDraft);
}
$("#preview-source-declarations").addEventListener("click", previewSourceDeclarations);
$("#structured-draft-file").addEventListener("change", async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    $("#structured-draft").value = await file.text();
    $("#import-status").textContent = `Loaded ${file.name}. Import has not occurred yet.`;
  } catch (error) {
    $("#import-status").textContent = `Could not read ${file.name}. ${error.message}`;
  }
});
$("#add-draft").addEventListener("click", () => { addDraftRow({canonical_identity_established: false, provenance_type: "DIRECT_OBSERVATION"}); invalidateConfirmation(); });
$("#merge-drafts").addEventListener("click", () => { try { mergeSelectedDrafts(); } catch (error) { show({error: error.message}); } });
$("#confirm-tracks").addEventListener("click", () => { try { confirmReviewedTracks(); } catch (error) { show({error: error.message}); } });
$("#add-link").addEventListener("click", () => addRow("#link-template", "#evidence-links"));
$("#build").addEventListener("click", buildProposal);
$("#validate").addEventListener("click", validateProposal);
$("#ingest").addEventListener("click", ingestProposal);
$("#rebuild-structured-evaluation").addEventListener("click", rebuildStructuredWorksheet);
$("#preview-structured-evaluation").addEventListener("click", previewStructuredEvaluation);
proposal.addEventListener("input", () => {
  invalidateValidation();
  invalidateStructuredWorksheet();
});
$("#prompt").addEventListener("input", () => {
  $("#prompt-attested").checked = false;
  invalidateValidation();
  refreshReadiness();
});
document.querySelectorAll("#evidence-standard, #captures-start, #captures-end, #evidence-provenance, #evidence-support, [data-claim-field], #source-system, #prompt, #prompt-attested, #requested-count, #assessment-outcome, #generated-title, #generated-description, #notes")
  .forEach(input => input.addEventListener("change", () => { invalidateValidation(); refreshReadiness(); }));
renderStaged();
$("#requested-count-state").value = "UNKNOWN";
$("#requested-count").value = "";
$("#saved").value = "UNKNOWN";
updateMode();
updateCompleteness();
updateRequestedTrackCountState();
updateSavedStatus();
initializeDraftTrackWorkflow();
initializePlannedRunContext();
