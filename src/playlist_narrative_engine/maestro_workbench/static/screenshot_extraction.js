(function () {
  "use strict";

  let activeReview = null;

  function renumberAcceptedTracks(tracks) {
    return tracks.map((track, index) => ({...track, proposed_position: index + 1}));
  }

  function renumberReviewRows(container) {
    [...container.querySelectorAll(".extraction-track")].forEach((row, index) => {
      row.querySelector("[data-review-row-label]").textContent = `Track ${index + 1}`;
      row.querySelector('[data-extracted-field="proposed_position"]').value = String(index + 1);
    });
  }

  function acceptanceIssue(tracks) {
    return tracks.length ? null : "Retain at least one extracted track before accepting the draft.";
  }

  function coverageRangesComplete(trackCount, ranges) {
    if (!Number.isInteger(trackCount) || trackCount < 1) return false;
    const covered = new Set();
    let priorStart = 0;
    let priorEnd = 0;
    for (const range of ranges) {
      const start = Number(range.start);
      const end = Number(range.end);
      if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end < start || end > trackCount) return false;
      if (start < priorStart || end < priorEnd) return false;
      for (let position = start; position <= end; position += 1) covered.add(position);
      priorStart = start;
      priorEnd = end;
    }
    return covered.size === trackCount;
  }

  function completeContinuityIssue(completeness, continuityEstablished, operatorCoverageComplete = false) {
    return completeness === "COMPLETE" && continuityEstablished === false && !operatorCoverageComplete
      ? "Resolve screenshot continuity before declaring the tracklist COMPLETE"
      : null;
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[character]);
  }

  function render(container, result, accept) {
    activeReview = JSON.parse(JSON.stringify(result));
    const supported = activeReview.observations.filter(item => item.supported);
    const unsupported = activeReview.observations.filter(item => !item.supported);
    container.hidden = false;
    container.innerHTML = `
      <div class="entry-head"><h3>Extraction Review</h3><span class="status">Disposable draft</span></div>
      <p class="hint">Machine extraction is not governed evidence. Review every retained value before accepting it into the existing unconfirmed draft.</p>
      ${unsupported.map(item => `<p class="warning">${escapeHtml(item.source_key)}: ${escapeHtml(item.warnings.join(" "))}</p>`).join("")}
      <div class="form-grid">
        <label>Generated Title<input data-review-title value="${escapeHtml(activeReview.generated_title)}"></label>
        <label>Generated Description<input data-review-description value="${escapeHtml(activeReview.generated_description)}"></label>
      </div>
      <h4>Track observations</h4>
      <div data-review-tracks class="card-list"></div>
      <p data-review-error class="warning" hidden></p>
      <h4>Evidence coverage</h4>
      <div data-review-coverage class="card-list">${activeReview.coverage.map(item => `<article class="entry-card" data-coverage-source="${escapeHtml(item.source_key)}"><strong>${escapeHtml(item.source_key)}</strong><div class="form-grid"><label>Proposed first position<input data-range-start type="number" min="1" value="${escapeHtml(item.start)}"></label><label>Proposed last position<input data-range-end type="number" min="1" value="${escapeHtml(item.end)}"></label><label>Playlist start<select data-playlist-start><option ${item.playlist_start === "UNRESOLVED" ? "selected" : ""}>UNRESOLVED</option><option ${item.playlist_start === "YES" ? "selected" : ""}>YES</option><option ${item.playlist_start === "NO" ? "selected" : ""}>NO</option></select></label><label>Playlist end<select data-playlist-end><option ${item.playlist_end === "UNRESOLVED" ? "selected" : ""}>UNRESOLVED</option><option ${item.playlist_end === "YES" ? "selected" : ""}>YES</option><option ${item.playlist_end === "NO" ? "selected" : ""}>NO</option></select></label></div></article>`).join("")}</div>
      <div class="transition-list">${activeReview.transitions.map(item => `<p class="${item.status === "UNRESOLVED_CONTINUITY" ? "warning" : "hint"}">${escapeHtml(item.source_keys.join(" → "))}: ${escapeHtml(item.status)}</p>`).join("")}</div>
      <div class="actions"><button data-accept-extraction type="button">Accept Extracted Draft</button><button data-discard-extraction class="secondary" type="button">Discard Extracted Draft</button></div>`;

    const rows = container.querySelector("[data-review-tracks]");
    activeReview.draft_tracks.forEach((track, index) => {
      const card = document.createElement("article");
      card.className = "entry-card extraction-track";
      card.dataset.structuralStatus = track.structural_status;
      card.dataset.completenessStatus = track.completeness_status;
      card.innerHTML = `<div class="entry-head"><strong data-review-row-label>Track ${index + 1}</strong><div class="row-actions"><span class="${track.structural_status === "STRUCTURALLY_CLEAR" && track.completeness_status === "COMPLETE_AS_OBSERVED" ? "status" : "warning"}">${escapeHtml(track.structural_status)} · ${escapeHtml(track.completeness_status)}</span><button data-remove-extraction-row class="ghost" type="button">Delete</button></div></div><div class="track-fields"><label>Position<input data-extracted-field="proposed_position" type="number" min="1" value="${escapeHtml(track.proposed_position)}" readonly></label><label>Title<input data-extracted-field="title" value="${escapeHtml(track.title)}"></label><label>Artist<input data-extracted-field="artist" value="${escapeHtml(track.artist)}"></label><label>Source key(s)<input data-extracted-field="source_keys" value="${escapeHtml(track.source_keys.join(","))}"></label></div><p class="hint">OCR ${(Number(track.ocr_confidence) * 100).toFixed(1)}% ${escapeHtml(track.warnings.join(" "))}</p>`;
      card.querySelector("[data-remove-extraction-row]").addEventListener("click", () => {
        card.remove();
        renumberReviewRows(container);
        const error = container.querySelector("[data-review-error]");
        error.hidden = true;
        error.textContent = "";
      });
      rows.append(card);
    });

    container.querySelector("[data-discard-extraction]").addEventListener("click", () => discard(container));
    container.querySelector("[data-accept-extraction]").addEventListener("click", () => {
      const tracks = renumberAcceptedTracks([...container.querySelectorAll(".extraction-track")].map(row => ({
        proposed_position: Number(row.querySelector('[data-extracted-field="proposed_position"]').value) || null,
        proposed_title: row.querySelector('[data-extracted-field="title"]').value || null,
        proposed_artist: row.querySelector('[data-extracted-field="artist"]').value || null,
        proposed_version_remaster_text: null,
        source_keys: row.querySelector('[data-extracted-field="source_keys"]').value.split(",").map(value => value.trim()).filter(Boolean),
        ambiguity_flag: row.dataset.structuralStatus !== "STRUCTURALLY_CLEAR" || row.dataset.completenessStatus !== "COMPLETE_AS_OBSERVED",
      })));
      const issue = acceptanceIssue(tracks);
      if (issue) {
        const error = container.querySelector("[data-review-error]");
        error.textContent = issue;
        error.hidden = false;
        return;
      }
      const coverage = [...container.querySelectorAll("[data-coverage-source]")].map(row => ({
        source_key: row.dataset.coverageSource,
        start: Number(row.querySelector("[data-range-start]").value) || null,
        end: Number(row.querySelector("[data-range-end]").value) || null,
        playlist_start: row.querySelector("[data-playlist-start]").value,
        playlist_end: row.querySelector("[data-playlist-end]").value,
      }));
      accept({
        generated_title: container.querySelector("[data-review-title]").value || null,
        generated_description: container.querySelector("[data-review-description]").value || null,
        tracks,
        coverage,
        continuity_established: activeReview.continuity_established === true,
      });
      discard(container);
    });
  }

  function discard(container) {
    activeReview = null;
    container.innerHTML = "";
    container.hidden = true;
  }

  const api = {
    render, discard, renumberAcceptedTracks, renumberReviewRows,
    acceptanceIssue, coverageRangesComplete, completeContinuityIssue,
    hasActiveReview: () => activeReview !== null,
  };
  if (typeof window !== "undefined") window.ScreenshotExtractionReview = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
