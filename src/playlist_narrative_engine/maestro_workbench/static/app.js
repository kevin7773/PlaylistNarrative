const kind = document.querySelector("#kind");
const proposal = document.querySelector("#proposal");
const result = document.querySelector("#result");
const staged = document.querySelector("#staged");
const accessToken = new URLSearchParams(window.location.search).get("token");

function apiHeaders(additional = {}) {
  return accessToken
    ? {...additional, "X-Workbench-Token": accessToken}
    : additional;
}

const templates = {
  historical_experiment: {
    prompt: null,
    source_system: "Maestro Beta",
    tracklist_completeness: "NOT_OBSERVED",
    tracks: [],
    evidence_sources: [],
    evidence: []
  },
  current_persisted_artifact: {
    source_system: "Amazon Music",
    persistence_state: "UNKNOWN",
    tracklist_completeness: "NOT_OBSERVED",
    segments: [],
    tracks: [],
    evidence_sources: [],
    evidence: []
  }
};

function resetTemplate() {
  proposal.value = JSON.stringify(templates[kind.value], null, 2);
  result.textContent = "No operation performed.";
}

async function stageEvidence() {
  const files = [...document.querySelector("#evidence-files").files];
  for (const file of files) {
    const response = await fetch("/api/stage-evidence", {
      method: "POST",
      headers: apiHeaders({"X-Original-Filename": encodeURIComponent(file.name)}),
      body: file
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "Evidence staging failed");
    const entry = document.createElement("details");
    entry.open = true;
    entry.innerHTML = `<summary>${body.original_filename} · ${body.size_bytes} bytes</summary><pre>${JSON.stringify(body, null, 2)}</pre>`;
    staged.append(entry);
  }
}

function requestBody() {
  return {kind: kind.value, proposal: JSON.parse(proposal.value)};
}

async function invoke(path, confirmationRequired = false) {
  if (confirmationRequired && !window.confirm("Ingest exactly this reviewed record?")) return;
  result.textContent = "Working…";
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: apiHeaders({"Content-Type": "application/json"}),
      body: JSON.stringify(requestBody())
    });
    const body = await response.json();
    result.textContent = JSON.stringify(body, null, 2);
  } catch (error) {
    result.textContent = JSON.stringify({error: error.message}, null, 2);
  }
}

kind.addEventListener("change", resetTemplate);
document.querySelector("#stage").addEventListener("click", () => stageEvidence().catch(error => {
  result.textContent = JSON.stringify({error: error.message}, null, 2);
}));
document.querySelector("#validate").addEventListener("click", () => invoke("/api/validate"));
document.querySelector("#ingest").addEventListener("click", () => invoke("/api/ingest", true));
resetTemplate();
