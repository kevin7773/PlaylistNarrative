from __future__ import annotations

import os
import json
import threading
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pytest
from PIL import Image

from playlist_narrative_engine.maestro_workbench.screenshot_extraction import (
    Maestro590x1280Segmenter,
    MAESTRO_1179X2556,
    MAESTRO_590X1280,
    RapidOCRScreenshotExtractor,
    ScreenshotDraftReconciler,
    ScreenshotObservation,
    ScreenshotTrackObservation,
    TextLine,
    maestro_layout_profile,
)
from playlist_narrative_engine.maestro_workbench.server import MaestroWorkbenchServer


def line(text: str, y: float, *, x0: float = 128, x1: float = 400, confidence: float = 0.999) -> TextLine:
    return TextLine(text, confidence, x0, x1, y, y + 22)


def validated_image():
    image = np.zeros((1280, 590, 3), dtype=np.uint8)
    image[1076:1078, :] = 220
    return image


def validated_large_image():
    return np.zeros((2556, 1179, 3), dtype=np.uint8)


def track(title: str, artist: str, source: str, **changes) -> ScreenshotTrackObservation:
    values = {
        "proposed_position": None, "title": title, "artist": artist,
        "source_keys": (source,), "ocr_confidence": 0.999,
        "structural_status": "STRUCTURALLY_CLEAR",
        "completeness_status": "COMPLETE_AS_OBSERVED", "warnings": (),
    }
    values.update(changes)
    return ScreenshotTrackObservation(**values)


def test_validated_layout_excludes_player_and_separates_confidence_dimensions() -> None:
    rows = Maestro590x1280Segmenter().segment("source_1", validated_image(), [
        line("Visible Title", 300), line("Visible Artist", 332),
        line("Now Playing Title", 1120, x0=90), line("Now Playing Artist", 1150, x0=90),
    ])
    assert rows.supported is True
    assert len(rows.tracks) == 1
    assert rows.tracks[0].title == "Visible Title"
    assert rows.tracks[0].artist == "Visible Artist"
    assert rows.tracks[0].structural_status == "STRUCTURALLY_CLEAR"
    assert rows.tracks[0].completeness_status == "COMPLETE_AS_OBSERVED"


def test_exact_layout_profile_selection_is_deterministic_and_nearby_sizes_fail_closed() -> None:
    assert maestro_layout_profile(590, 1280) is MAESTRO_590X1280
    assert maestro_layout_profile(1179, 2556) is MAESTRO_1179X2556
    assert maestro_layout_profile(1178, 2556) is None
    assert maestro_layout_profile(1179, 2555) is None
    assert maestro_layout_profile(832, 1792) is None


def test_large_layout_excludes_header_player_navigation_album_art_and_floating_controls() -> None:
    result = Maestro590x1280Segmenter().segment("source_1", validated_large_image(), [
        TextLine("Staring Into The Void At 3AM", 0.999, 47, 910, 383, 466),
        line("Hypnotic heavy music", 517, x0=52, x1=700), line("contemplation", 599, x0=53, x1=376),
        line("Track Title", 950, x0=255, x1=700), line("Track Artist", 1006, x0=257, x1=500),
        line("Album Art Text", 1100, x0=60, x1=180),
        line("Alexa", 1600, x0=980, x1=1100),
        line("Now Playing", 2188, x0=187, x1=600), line("Player Artist", 2243, x0=187, x1=400),
        line("Library", 2425, x0=873, x1=987),
    ])
    assert result.supported is True
    assert result.generated_title_candidates == ("Staring Into The Void At 3AM",)
    assert result.generated_description_candidates == ("Hypnotic heavy music contemplation",)
    assert [(item.title, item.artist) for item in result.tracks] == [("Track Title", "Track Artist")]


def test_large_continuation_screen_does_not_manufacture_header_metadata() -> None:
    result = Maestro590x1280Segmenter().segment("source_2", validated_large_image(), [
        line("ALBUM ART", 434, x0=61, x1=225),
        line("Track Title", 232, x0=255, x1=700), line("Track Artist", 287, x0=257, x1=500),
    ])
    assert result.generated_title_candidates == ()
    assert result.generated_description_candidates == ()


def test_false_candidate_is_not_clear_and_complete() -> None:
    result = Maestro590x1280Segmenter().segment("source_1", validated_image(), [line("Unpaired", 300)])
    candidate = result.tracks[0]
    assert candidate.structural_status == "STRUCTURALLY_AMBIGUOUS"
    assert (candidate.structural_status, candidate.completeness_status) != ("STRUCTURALLY_CLEAR", "COMPLETE_AS_OBSERVED")


def test_clipped_and_source_truncated_rows_receive_distinct_completeness_warnings() -> None:
    result = Maestro590x1280Segmenter().segment("source_1", validated_image(), [
        line("Clipped Title", 300, x1=530), line("Artist", 332),
        line("Title Two", 500), line("Artist Two...", 532),
    ])
    assert result.tracks[0].completeness_status == "POSSIBLY_CLIPPED"
    assert result.tracks[1].completeness_status == "TRUNCATED_IN_SOURCE"


def test_unsupported_dimensions_are_rejected_before_ocr_and_remain_manual(tmp_path: Path) -> None:
    path = tmp_path / "unsupported.png"
    Image.new("RGB", (591, 1280)).save(path)

    class MustNotRun:
        def __call__(self, _path):
            raise AssertionError("OCR must not run for unsupported dimensions")

    result = RapidOCRScreenshotExtractor(engine=MustNotRun()).extract("source_1", path)
    assert result.supported is False
    assert result.tracks == ()
    assert "manual" not in " ".join(result.warnings).lower()  # staging/manual behavior is not altered here


def test_exact_overlap_reconciles_and_preserves_both_sources() -> None:
    review = ScreenshotDraftReconciler().reconcile((
        ScreenshotObservation("source_1", True, 590, 1280, tracks=(track("A", "One", "source_1"), track("Same", "Artist", "source_1"))),
        ScreenshotObservation("source_2", True, 590, 1280, tracks=(track("Same", "Artist", "source_2"), track("B", "Two", "source_2"))),
    ))
    assert [item.title for item in review.draft_tracks] == ["A", "Same", "B"]
    assert [item.proposed_position for item in review.draft_tracks] == [1, 2, 3]
    assert review.draft_tracks[1].source_keys == ("source_1", "source_2")
    assert review.transitions[0]["status"] == "EXACT_OVERLAP_ACCEPTED"
    assert review.continuity_established is True


def test_nonexact_overlap_is_unresolved_and_duplicate_title_different_artist_stays_distinct() -> None:
    review = ScreenshotDraftReconciler().reconcile((
        ScreenshotObservation("source_1", True, 590, 1280, tracks=(track("Same", "Artist A", "source_1"),)),
        ScreenshotObservation("source_2", True, 590, 1280, tracks=(track("Same", "Artist B", "source_2"),)),
    ))
    assert len(review.draft_tracks) == 2
    assert [item.proposed_position for item in review.draft_tracks] == [1, 2]
    assert review.transitions[0]["status"] == "UNRESOLVED_CONTINUITY"
    assert review.continuity_established is False
    assert all(item.completeness_status == "TEXT_AMBIGUOUS" for item in review.draft_tracks)


def test_unsupported_observation_does_not_prevent_supported_review() -> None:
    review = ScreenshotDraftReconciler().reconcile((
        ScreenshotObservation("unsupported", False, 400, 800, warnings=("unsupported",)),
        ScreenshotObservation("source_2", True, 590, 1280, tracks=(track("A", "Artist", "source_2"),)),
    ))
    assert [item.title for item in review.draft_tracks] == ["A"]
    assert review.observations[0].supported is False


@pytest.mark.skipif(os.environ.get("PNE_RUN_LIVE_OCR_TESTS") != "1", reason="live RapidOCR inference is opt-in")
def test_live_rapidocr_provider_on_validated_fixture(tmp_path: Path) -> None:
    from PIL import ImageDraw

    path = tmp_path / "validated.png"
    image = Image.new("RGB", (590, 1280), "black")
    draw = ImageDraw.Draw(image)
    draw.text((128, 300), "Visible Title", fill="white")
    draw.text((128, 340), "Visible Artist", fill="white")
    draw.line((0, 1076, 589, 1076), fill="white", width=2)
    image.save(path)
    result = RapidOCRScreenshotExtractor().extract("source_1", path)
    assert result.supported is True


def test_static_review_flow_keeps_accept_and_discard_explicit() -> None:
    root = Path("src/playlist_narrative_engine/maestro_workbench/static")
    html = (root / "index.html").read_text(encoding="utf-8")
    javascript = (root / "screenshot_extraction.js").read_text(encoding="utf-8")
    app = (root / "app.js").read_text(encoding="utf-8")
    assert "Extract Draft From Screenshots" in html
    assert "Accept Extracted Draft" in javascript
    assert "Discard Extracted Draft" in javascript
    assert "invalidateConfirmation()" in app
    assert "/api/extract-screenshot-draft" in app
    assert "validateProposal" not in javascript
    assert "ingestProposal" not in javascript
    assert "screenshot_extraction_supported === true" in app
    assert "item.width === 590" not in app
    assert "completeContinuityIssue" in app


def test_browser_acceptance_renumbers_retained_extraction_rows_without_changing_identity() -> None:
    import subprocess

    script_path = Path("src/playlist_narrative_engine/maestro_workbench/static/screenshot_extraction.js").resolve()
    script = r'''const api = require(process.argv[1]);
const rows = api.renumberAcceptedTracks([
  {proposed_position: 1, proposed_title: "Same", proposed_artist: "Artist A", source_keys: ["source_1"]},
  {proposed_position: 3, proposed_title: "Same", proposed_artist: "Artist B", source_keys: ["source_2"]},
  {proposed_position: 4, proposed_title: "Final", proposed_artist: "Artist", source_keys: ["source_2"]},
]);
process.stdout.write(JSON.stringify(rows));'''
    completed = subprocess.run(
        ["node", "-e", script, str(script_path)],
        check=True, capture_output=True, text=True,
    )
    rows = json.loads(completed.stdout)
    assert [item["proposed_position"] for item in rows] == [1, 2, 3]
    assert [(item["proposed_title"], item["proposed_artist"]) for item in rows[:2]] == [
        ("Same", "Artist A"), ("Same", "Artist B"),
    ]


def test_unresolved_extraction_continuity_blocks_only_complete_extraction_drafts() -> None:
    import subprocess

    script_path = Path("src/playlist_narrative_engine/maestro_workbench/static/screenshot_extraction.js").resolve()
    script = r'''const api = require(process.argv[1]);
process.stdout.write(JSON.stringify({
  unresolvedComplete: api.completeContinuityIssue("COMPLETE", false, false),
  coveredUnresolvedComplete: api.completeContinuityIssue("COMPLETE", false, true),
  establishedComplete: api.completeContinuityIssue("COMPLETE", true),
  manualComplete: api.completeContinuityIssue("COMPLETE", null),
  unresolvedPartial: api.completeContinuityIssue("PARTIAL", false),
}));'''
    completed = subprocess.run(
        ["node", "-e", script, str(script_path)],
        check=True, capture_output=True, text=True,
    )
    result = json.loads(completed.stdout)
    assert result["unresolvedComplete"] == "Resolve screenshot continuity before declaring the tracklist COMPLETE"
    assert result["coveredUnresolvedComplete"] is None
    assert result["establishedComplete"] is None
    assert result["manualComplete"] is None
    assert result["unresolvedPartial"] is None


def test_explicit_operator_coverage_can_satisfy_complete_continuity_readiness() -> None:
    import subprocess

    script_path = Path("src/playlist_narrative_engine/maestro_workbench/static/screenshot_extraction.js").resolve()
    script = r'''const api = require(process.argv[1]);
const cases = {
  production: api.coverageRangesComplete(40, [[1,5],[5,13],[13,21],[21,29],[29,37],[34,40]].map(([start,end]) => ({start,end}))),
  singleOverlap: api.coverageRangesComplete(10, [{start:1,end:5},{start:5,end:10}]),
  multiOverlap: api.coverageRangesComplete(10, [{start:1,end:7},{start:4,end:10}]),
  adjacent: api.coverageRangesComplete(10, [{start:1,end:5},{start:6,end:10}]),
  internalGap: api.coverageRangesComplete(13, [{start:1,end:5},{start:7,end:13}]),
  missingFirst: api.coverageRangesComplete(10, [{start:2,end:10}]),
  missingFinal: api.coverageRangesComplete(10, [{start:1,end:9}]),
  reversedSources: api.coverageRangesComplete(10, [{start:6,end:10},{start:1,end:5}]),
};
process.stdout.write(JSON.stringify(cases));'''
    completed = subprocess.run(
        ["node", "-e", script, str(script_path)],
        check=True, capture_output=True, text=True,
    )
    result = json.loads(completed.stdout)
    assert result == {
        "production": True,
        "singleOverlap": True,
        "multiOverlap": True,
        "adjacent": True,
        "internalGap": False,
        "missingFirst": False,
        "missingFinal": False,
        "reversedSources": False,
    }


def test_extraction_review_removal_renumbers_retained_rows_and_refuses_empty_acceptance() -> None:
    import subprocess

    script_path = Path("src/playlist_narrative_engine/maestro_workbench/static/screenshot_extraction.js").resolve()
    script = r'''const api = require(process.argv[1]);
function row(position) {
  const label = {textContent: `Track ${position}`};
  const input = {value: String(position)};
  return {label, input, querySelector(selector) {
    return selector === "[data-review-row-label]" ? label : input;
  }};
}
const retainedRows = [row(1), row(3)];
api.renumberReviewRows({querySelectorAll() { return retainedRows; }});
const retained = api.renumberAcceptedTracks([
  {proposed_position: 1, proposed_title: "First", proposed_artist: "Artist", source_keys: ["source_1"]},
  {proposed_position: 3, proposed_title: "Same", proposed_artist: "Different Artist", source_keys: ["source_2", "source_3"]},
]);
process.stdout.write(JSON.stringify({
  labels: retainedRows.map(row => row.label.textContent),
  displayedPositions: retainedRows.map(row => row.input.value),
  retained,
  emptyIssue: api.acceptanceIssue([]),
  retainedIssue: api.acceptanceIssue(retained),
  continuityAfterRemoval: api.completeContinuityIssue("COMPLETE", false, false),
}));'''
    completed = subprocess.run(
        ["node", "-e", script, str(script_path)],
        check=True, capture_output=True, text=True,
    )
    result = json.loads(completed.stdout)
    assert result["labels"] == ["Track 1", "Track 2"]
    assert result["displayedPositions"] == ["1", "2"]
    assert [item["proposed_position"] for item in result["retained"]] == [1, 2]
    assert result["retained"][1]["source_keys"] == ["source_2", "source_3"]
    assert result["retained"][1]["proposed_artist"] == "Different Artist"
    assert result["emptyIssue"] == "Retain at least one extracted track before accepting the draft."
    assert result["retainedIssue"] is None
    assert result["continuityAfterRemoval"] == "Resolve screenshot continuity before declaring the tracklist COMPLETE"


def test_extraction_review_delete_is_disposable_and_does_not_manufacture_overlap() -> None:
    javascript = Path(
        "src/playlist_narrative_engine/maestro_workbench/static/screenshot_extraction.js"
    ).read_text(encoding="utf-8")
    delete_handler = javascript[javascript.index('card.querySelector("[data-remove-extraction-row]")'):]
    delete_handler = delete_handler[:delete_handler.index("rows.append(card)")]
    assert "card.remove()" in delete_handler
    assert "renumberReviewRows(container)" in delete_handler
    assert "accept(" not in delete_handler
    assert "activeReview.transitions" not in delete_handler
    assert "EXACT_OVERLAP_ACCEPTED" not in delete_handler


def test_extraction_review_playlist_boundaries_are_independently_mutually_exclusive() -> None:
    import subprocess

    script_path = Path("src/playlist_narrative_engine/maestro_workbench/static/screenshot_extraction.js").resolve()
    script = r'''const api = require(process.argv[1]);
function row(start = "UNRESOLVED", end = "UNRESOLVED") {
  const values = {"[data-playlist-start]": {value: start}, "[data-playlist-end]": {value: end}};
  return {querySelector(selector) { return values[selector]; }, values};
}
const a = row("YES", "YES");
const b = row("YES", "NO");
const c = row("NO", "YES");
const rows = [a, b, c];
const single = row("YES", "YES");
api.applyExclusiveBoundary([single], single, "[data-playlist-start]");
api.applyExclusiveBoundary([single], single, "[data-playlist-end]");
api.applyExclusiveBoundary(rows, b, "[data-playlist-start]");
const afterStart = rows.map(row => ({start: row.values["[data-playlist-start]"].value, end: row.values["[data-playlist-end]"].value}));
api.applyExclusiveBoundary(rows, c, "[data-playlist-end]");
const afterEnd = rows.map(row => ({start: row.values["[data-playlist-start]"].value, end: row.values["[data-playlist-end]"].value}));
b.values["[data-playlist-start]"].value = "NO";
api.applyExclusiveBoundary(rows, b, "[data-playlist-start]");
c.values["[data-playlist-end]"].value = "NO";
api.applyExclusiveBoundary(rows, c, "[data-playlist-end]");
process.stdout.write(JSON.stringify({single: {start: single.values["[data-playlist-start]"].value, end: single.values["[data-playlist-end]"].value}, afterStart, afterEnd, afterClearing: rows.map(row => ({start: row.values["[data-playlist-start]"].value, end: row.values["[data-playlist-end]"].value}))}));'''
    completed = subprocess.run(
        ["node", "-e", script, str(script_path)], check=True, capture_output=True, text=True,
    )
    result = json.loads(completed.stdout)
    assert result["single"] == {"start": "YES", "end": "YES"}
    assert [item["start"] for item in result["afterStart"]] == ["NO", "YES", "NO"]
    assert [item["end"] for item in result["afterStart"]] == ["YES", "NO", "YES"]
    assert [item["start"] for item in result["afterEnd"]] == ["NO", "YES", "NO"]
    assert [item["end"] for item in result["afterEnd"]] == ["NO", "NO", "YES"]
    assert [item["start"] for item in result["afterClearing"]] == ["NO", "NO", "NO"]
    assert [item["end"] for item in result["afterClearing"]] == ["NO", "NO", "NO"]


def test_staging_does_not_assign_playlist_boundaries() -> None:
    app = Path("src/playlist_narrative_engine/maestro_workbench/static/app.js").read_text(encoding="utf-8")
    stage = app[app.index("async function stageEvidence()") : app.index("function acceptScreenshotExtraction")]
    assert '$("#captures-start").value = "YES"' not in stage
    assert '$("#captures-end").value = "YES"' not in stage


def test_http_extraction_returns_disposable_review_without_research_store_access(tmp_path: Path) -> None:
    class FixtureExtractor:
        def extract(self, source_key: str, _path: Path) -> ScreenshotObservation:
            return ScreenshotObservation(source_key, True, 590, 1280, tracks=(track("Title", "Artist", source_key),))

    server = MaestroWorkbenchServer(("127.0.0.1", 0), staging_root=tmp_path, screenshot_extractor=FixtureExtractor())
    server.staged_paths.add(str((tmp_path / "capture.png").resolve()))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/extract-screenshot-draft",
            data=json.dumps({"staged_sources": [{"source_key": "source_1", "local_path": str(tmp_path / "capture.png")}]}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urlopen(request) as response:
            result = json.load(response)
        assert result["draft_tracks"][0]["title"] == "Title"
        assert result["draft_tracks"][0]["source_keys"] == ["source_1"]
        assert "proposal" not in result
        assert "validated" not in result
        assert "ingested" not in result
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_staging_response_uses_server_profile_selection(tmp_path: Path) -> None:
    buffer = BytesIO()
    Image.new("RGB", (1179, 2556)).save(buffer, format="PNG")
    server = MaestroWorkbenchServer(("127.0.0.1", 0), staging_root=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/stage-evidence",
            data=buffer.getvalue(), headers={"X-Original-Filename": "capture.png"}, method="POST",
        )
        with urlopen(request) as response:
            result = json.load(response)
        assert result["screenshot_extraction_supported"] is True
        assert result["screenshot_layout_profile"] == "maestro_1179x2556"
        assert (result["width"], result["height"]) == (1179, 2556)
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
