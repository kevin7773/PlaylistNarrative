from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
HTML = ROOT / "src/playlist_narrative_engine/maestro_workbench/static/studies.html"
SCRIPT = ROOT / "src/playlist_narrative_engine/maestro_workbench/static/studies.js"


def test_section_08_is_projection_only_and_keeps_prior_sections_separate():
    html = HTML.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    before, closeout = html.split('<section id="closeout-panel"', 1)
    assert "Study Evaluation" in before and "Exploratory Post-Study Analysis" in before
    assert "Study Closeout" in closeout
    assert "not a new scientific record" in closeout
    assert "REGISTERED RESULTS" in script
    assert "EXPLORATORY — NOT PREREGISTERED" in script
    assert "Download JSON research bundle" in script
    assert "Download Markdown report" in script
    assert "<button" not in closeout


def test_closeout_ui_retains_manifest_and_has_no_write_request():
    html = HTML.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    assert '<details id="closeout-provenance">' in html
    start = script.index("function closeoutDownloadUrl")
    end = script.index("function execute(", start)
    surface = script[start:end]
    assert "method:" not in surface
    assert "report_generation.timestamp_semantics" in surface
    assert "deterministic_payload_sha256" in surface
