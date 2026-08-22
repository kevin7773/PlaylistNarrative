from __future__ import annotations

import ast
from pathlib import Path


RESULT_CONSTRUCTORS = {"AcceptedObjectiveArtifact", "DeclinedObjectiveArtifact"}


def test_only_objective_safety_evaluator_constructs_production_results() -> None:
    source_root = Path("src/playlist_narrative_engine")
    allowed = Path("src/playlist_narrative_engine/objective_safety/evaluator.py")
    violations: list[str] = []

    for path in sorted(source_root.rglob("*.py")):
        if path == allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else None
            )
            if name in RESULT_CONSTRUCTORS:
                violations.append(f"{path}:{node.lineno}:{name}")

    assert violations == []


def test_product_code_never_imports_objective_safety_test_helpers() -> None:
    for path in Path("src/playlist_narrative_engine").rglob("*.py"):
        assert "objective_safety_helpers" not in path.read_text(encoding="utf-8")
