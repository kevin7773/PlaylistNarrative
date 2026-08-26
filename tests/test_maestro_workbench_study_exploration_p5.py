from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
HTML = ROOT / "src/playlist_narrative_engine/maestro_workbench/static/studies.html"
SCRIPT = ROOT / "src/playlist_narrative_engine/maestro_workbench/static/studies.js"


def test_section_07_is_separate_exploratory_and_read_only():
    html = HTML.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    section_06, section_07 = html.split('<section id="exploration-panel"', 1)
    assert "Registered analyses" in section_06
    assert "EXPLORATORY — NOT PREREGISTERED" in section_07
    assert "synopsis.label" in script
    assert "Track-level exploratory analysis is unavailable" not in script
    assert "exploration.constraint_matrix.map" in script
    assert "exploration.constraint_by_replicate" in script
    assert "exploration.metadata_cross_view.cells.map" in script
    assert "Contributing governed runs" in script
    assert "<button" not in section_07


def test_exploratory_projection_is_technical_detail_not_primary_ui():
    html = HTML.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    assert '<details id="exploration-technical">' in html
    assert "Raw exploratory projection / Technical details" in html
    start = script.index("function renderExplorationMatrix")
    end = script.index("function execute(", start)
    surface = script[start:end]
    assert "method:" not in surface
    assert "JSON.stringify(exploration,null,2)" in surface
    assert "significant" not in surface.lower()
    assert "causes" not in surface.lower()


def test_finite_vocabulary_failure_modes_are_readable_and_remain_exploratory():
    script = SCRIPT.read_text(encoding="utf-8")
    assert "function renderFiniteVocabularyFailures" in script
    assert "Finite-vocabulary field-boundary failures" in script
    assert "Vocabulary match in displayed artist only" in script
    assert "Semantic/associative relation remains NOT_DERIVABLE" in script
    assert "Recurring non-PASS displayed title/artist pairs" in script
