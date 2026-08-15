from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
HTML = ROOT / "src/playlist_narrative_engine/maestro_workbench/static/studies.html"
SCRIPT = ROOT / "src/playlist_narrative_engine/maestro_workbench/static/studies.js"


def test_p4_evaluation_surface_is_human_readable_and_auditable():
    html = HTML.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")

    assert "Primary registered outcome" in script
    assert "NARRATIVE − CONTROL" in script
    assert "Block comparison" in html
    assert "Replicate 1" in script and "Replicate 2" in script
    assert "evaluation.summary.primary_block_comparison.map" in script
    assert "evaluation.summary.replicate_consistency?.raw_results" in script
    assert "Registered analyses" in html
    assert "NOT_DERIVABLE" in script
    assert "Required per-track" not in script  # explanation comes from frozen P3 projection
    assert "Per-run governed evidence" in html
    assert "Recorded evidence:" in script
    assert 'id="evaluation-technical"' in html
    assert "Raw evaluation projection / Technical details" in html
    assert "<details id=\"evaluation-technical\"" in html


def test_p4_evaluation_rendering_has_no_mutation_controls_or_requests():
    html = HTML.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    evaluation_html = html.split('<section id="evaluation-panel"', 1)[1]
    assert "<button" not in evaluation_html
    render_start = script.index("function renderEvaluationFailure")
    render_end = script.index("function execute(", render_start)
    render_surface = script[render_start:render_end]
    assert "method:" not in render_surface
    assert "fetch(" not in render_surface
    assert "override" not in render_surface.lower()
    assert "repair" not in render_surface.lower()


def test_p4_uses_projection_values_without_recomputing_p3_semantics():
    script = SCRIPT.read_text(encoding="utf-8")
    assert "evaluation.summary.primary_by_condition" in script
    assert "evaluation.summary.primary_paired_analysis" in script
    assert "evaluation.summary.primary_block_comparison" in script
    assert "evaluation.summary.replicate_consistency" in script
    assert "evaluation.analyses.map" in script
    assert "evaluation.runs.map" in script
    assert "JSON.stringify(evaluation,null,2)" in script
