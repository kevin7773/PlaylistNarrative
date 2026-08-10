const $ = selector => document.querySelector(selector);
const kind = $("#kind");
const proposal = $("#proposal");
const result = $("#result");
const stagedContainer = $("#staged");
const accessToken = new URLSearchParams(window.location.search).get("token");
const stagedEvidence = [];

function apiHeaders(additional = {}) {
  return accessToken ? {...additional, "X-Workbench-Token": accessToken} : additional;
}

function show(value) {
  result.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function sourceOptions(select, selected = "") {
  select.innerHTML = `<option value="">None declared</option>`;
  stagedEvidence.forEach((item, index) => {
    const option = document.createElement("option");
    option.value = `source_${index + 1}`;
    option.textContent = `source_${index + 1} · ${item.original_filename}`;
    option.selected = option.value === selected;
    select.append(option);
  });
}

function refreshSourceSelectors() {
  document.querySelectorAll("select[data-source-select], #start-source, #end-source, [data-field='source_key']")
    .forEach(select => sourceOptions(select, select.value));
}

function renderStaged() {
  stagedContainer.innerHTML = "";
  if (!stagedEvidence.length) {
    stagedContainer.innerHTML = `<p class="empty">No evidence staged.</p>`;
    refreshSourceSelectors();
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
    card.querySelector("[data-source-type]").addEventListener("input", event => { item.source_type = event.target.value; });
    card.querySelector("[data-source-reference]").addEventListener("input", event => { item.source_reference = event.target.value; });
    stagedContainer.append(card);
  });
  refreshSourceSelectors();
}

async function stageEvidence() {
  const files = [...$("#evidence-files").files];
  if (!files.length) throw new Error("Select at least one evidence file to stage");
  for (const file of files) {
    const response = await fetch("/api/stage-evidence", {
      method: "POST",
      headers: apiHeaders({"X-Original-Filename": encodeURIComponent(file.name)}),
      body: file
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "Evidence staging failed");
    stagedEvidence.push(body);
  }
  $("#evidence-files").value = "";
  renderStaged();
  show({staged: stagedEvidence.length, message: "Exact source bytes staged; source declarations remain required."});
}

function optionalText(selector) {
  const value = $(selector).value;
  return value === "" ? undefined : value;
}

function optionalNumber(selector) {
  const value = $(selector).value;
  return value === "" ? undefined : Number(value);
}

function collectStagedEvidence() {
  return stagedEvidence.map((item, index) => {
    const card = stagedContainer.children[index];
    const sourceType = card.querySelector("[data-source-type]").value.trim();
    const sourceReference = card.querySelector("[data-source-reference]").value.trim();
    if (!sourceType || !sourceReference) throw new Error(`source_${index + 1} requires source type and source reference`);
    return {...item, source_type: sourceType, source_reference: sourceReference};
  });
}

function collectRows(containerSelector, rowSelector) {
  return [...document.querySelectorAll(`${containerSelector} ${rowSelector}`)].map(row => {
    const value = {};
    row.querySelectorAll("[data-field]").forEach(input => {
      if (input.type === "checkbox") value[input.dataset.field] = input.checked;
      else if (input.type === "number") value[input.dataset.field] = input.value === "" ? null : Number(input.value);
      else if (input.hasAttribute("data-boolean")) value[input.dataset.field] = input.value === "" ? null : input.value === "true";
      else value[input.dataset.field] = input.value || null;
    });
    return value;
  });
}

function collectDeclarations() {
  const completeness = $("#completeness").value;
  if (!completeness) throw new Error("Tracklist completeness must be explicitly declared");
  const values = {
    source_system: optionalText("#source-system"),
    evidence_standard: $("#evidence-standard").value,
    tracklist_completeness: completeness,
    notes: optionalText("#notes"),
    tracks: collectRows("#tracks", ".track-row"),
    top_level_evidence: collectRows("#evidence-links", ".link-row")
  };
  if (completeness !== "NOT_OBSERVED") {
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
      requested_track_count: optionalNumber("#requested-count"), generated_title: optionalText("#generated-title"),
      generated_description: optionalText("#generated-description"), assessment: optionalText("#assessment")
    });
    if ($("#saved").value !== "") values.saved = $("#saved").value === "true";
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
  show("Building proposal from explicit declarations…");
  const response = await fetch("/api/build-proposal", {
    method: "POST", headers: apiHeaders({"Content-Type": "application/json"}),
    body: JSON.stringify({kind: kind.value, declarations: collectDeclarations(), staged_evidence: collectStagedEvidence()})
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Proposal construction failed");
  proposal.value = JSON.stringify(body.proposal, null, 2);
  show({built: true, message: "Review the advanced JSON. No validation or write has occurred."});
}

function requestBody() {
  return {kind: kind.value, proposal: JSON.parse(proposal.value)};
}

async function invoke(path, confirmationRequired = false) {
  if (confirmationRequired && !window.confirm("Ingest exactly this one reviewed record?")) return;
  show("Working…");
  try {
    const response = await fetch(path, {method: "POST", headers: apiHeaders({"Content-Type": "application/json"}), body: JSON.stringify(requestBody())});
    const body = await response.json();
    show(body);
  } catch (error) { show({error: error.message}); }
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

function updateMode() {
  const historical = kind.value === "historical_experiment";
  $("#historical-fields").hidden = !historical;
  $("#artifact-fields").hidden = historical;
  proposal.value = "";
  show("Mode selected. No operation performed.");
}

function updateCompleteness() {
  const hidden = $("#completeness").value === "NOT_OBSERVED";
  document.querySelectorAll(".boundary-field").forEach(field => field.hidden = hidden);
  $("#tracks").closest("div")?.toggleAttribute("data-disabled", hidden);
}

function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, character => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"})[character]);
}

kind.addEventListener("change", updateMode);
$("#completeness").addEventListener("change", updateCompleteness);
$("#stage").addEventListener("click", () => stageEvidence().catch(error => show({error: error.message})));
$("#add-track").addEventListener("click", () => addRow("#track-template", "#tracks"));
$("#add-link").addEventListener("click", () => addRow("#link-template", "#evidence-links"));
$("#build").addEventListener("click", () => buildProposal().catch(error => show({error: error.message})));
$("#validate").addEventListener("click", () => invoke("/api/validate"));
$("#ingest").addEventListener("click", () => invoke("/api/ingest", true));
renderStaged();
updateMode();
updateCompleteness();
