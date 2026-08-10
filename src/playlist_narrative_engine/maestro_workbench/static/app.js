const $ = selector => document.querySelector(selector);
const kind = $("#kind");
const proposal = $("#proposal");
const result = $("#result");
const stagedContainer = $("#staged");
const accessToken = new URLSearchParams(window.location.search).get("session") || new URLSearchParams(window.location.search).get("token");
const stagedEvidence = [];
let confirmedTracks = null;
let validatedProposalSnapshot = null;
let ingestionActive = false;
let pendingSourceDeclarations = null;

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
  $("#ingest").disabled = true;
  setLocalStatus("#validation-status", message, "idle");
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
  return Number(rawValue);
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
  }
  const incompleteSources = incompleteSourceDeclarationOrdinals(stagedEvidence);
  if (!stagedEvidence.length) issues.push("Stage evidence screenshots");
  else if (incompleteSources.length) issues.push(`Complete source declarations for screenshots ${incompleteSources.join(", ")}`);
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

function collectDeclarations() {
  const completeness = $("#completeness").value;
  if (!completeness) throw new Error("Tracklist completeness must be explicitly declared");
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
      generated_description: optionalText("#generated-description"), assessment: optionalText("#assessment")
    });
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
      $("#ingest").disabled = false;
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
    $("#ingest").disabled = validatedProposalSnapshot !== proposal.value;
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

async function ingestProposal() {
  if (ingestionActive) return;
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
    const response = await fetch("/api/ingest", {method: "POST", headers: apiHeaders({"Content-Type": "application/json"}), body: JSON.stringify(requestBody())});
    const body = await readJsonResponse(response, "Ingestion");
    show(body);
    renderReadback(body.record, body.kind);
    setLocalStatus("#ingest-status", `Ingestion successful. ${body.kind} ${body.record_id} was inserted and read back.`, "success");
    validatedProposalSnapshot = null;
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
  });
  const sourceSelect = row.querySelector("[data-field='source_key']");
  if (sourceSelect) sourceOptions(sourceSelect);
  const container = $(containerSelector);
  container.querySelector(".empty")?.remove();
  container.append(fragment);
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
  show("Mode selected. No operation performed.");
  refreshReadiness();
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

kind.addEventListener("change", updateMode);
$("#completeness").addEventListener("change", updateCompleteness);
$("#requested-count-state").addEventListener("change", updateRequestedTrackCountState);
$("#saved").addEventListener("change", updateSavedStatus);
$("#stage").addEventListener("click", stageEvidence);
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
proposal.addEventListener("input", () => invalidateValidation());
$("#prompt").addEventListener("input", () => {
  $("#prompt-attested").checked = false;
  invalidateValidation();
  refreshReadiness();
});
document.querySelectorAll("#evidence-standard, #captures-start, #captures-end, #evidence-provenance, #evidence-support, [data-claim-field], #source-system, #prompt, #prompt-attested, #generated-title, #generated-description, #notes")
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
