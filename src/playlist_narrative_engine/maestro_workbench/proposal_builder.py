from __future__ import annotations

from typing import Any


SUPPORTED_KINDS = {"historical_experiment", "current_persisted_artifact"}


def build_governed_proposal(
    kind: str,
    declarations: dict[str, Any],
    staged_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Mechanically assemble existing schema fields from explicit declarations."""
    if kind not in SUPPORTED_KINDS:
        raise ValueError(f"unsupported workbench proposal kind: {kind}")
    completeness = _required_text(declarations, "tracklist_completeness")
    sources = _build_sources(staged_evidence)
    tracks = _build_tracks(declarations.get("tracks", []), sources)
    segments = _build_segments(declarations, completeness, sources, bool(tracks))
    if kind == "historical_experiment":
        proposal = _historical_proposal(declarations)
        if completeness == "COMPLETE":
            proposal["generated_track_count"] = len(tracks)
    else:
        proposal = _artifact_proposal(declarations)
    proposal.update(
        tracklist_completeness=completeness,
        segments=segments,
        tracks=tracks,
        evidence_sources=sources,
        evidence=_build_top_level_evidence(kind, declarations, sources),
    )
    return proposal


def _historical_proposal(values: dict[str, Any]) -> dict[str, Any]:
    return _present(values, (
        "prompt", "prompt_title", "source_system", "generated_title",
        "generated_description", "requested_track_count", "saved",
        "evidence_standard", "assessment", "notes",
    ))


def _artifact_proposal(values: dict[str, Any]) -> dict[str, Any]:
    if not values.get("persistence_state"):
        raise ValueError("persistence_state must be explicitly declared")
    return _present(values, (
        "source_system", "display_title", "display_description", "visibility_text",
        "persistence_state", "displayed_track_count", "displayed_duration_text",
        "evidence_standard", "notes",
    ))


def _build_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = []
    for index, item in enumerate(items, start=1):
        source_type = _required_text(item, "source_type")
        source_reference = _required_text(item, "source_reference")
        sources.append({
            "source_key": f"source_{index}",
            "source_type": source_type,
            "source_reference": source_reference,
            "original_filename": _required_text(item, "original_filename"),
            "local_path": _required_text(item, "local_path"),
            "sha256": _required_text(item, "sha256"),
        })
    return sources


def _build_tracks(items: object, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise ValueError("tracks must be an explicit list")
    valid_keys = {item["source_key"] for item in sources}
    result = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError("every track declaration must be an object")
        title = _optional_text(item.get("title"))
        artist = _optional_text(item.get("artist"))
        if title is None and artist is None:
            raise ValueError(f"track {index} requires an explicit title or artist")
        source_key = item.get("source_key")
        if source_key is not None and source_key not in valid_keys:
            raise ValueError(f"track {index} references an unknown staged source")
        track = {
            "observed_ordinal": index,
            "evidence_segment": 1,
            "segment_ordinal": index,
            "absolute_position": item.get("absolute_position"),
            "title": title,
            "artist": artist,
            "canonical_identity_established": _required_bool(item, "canonical_identity_established"),
            "evidence": [],
        }
        if source_key is not None:
            provenance = item.get("provenance_type", "DIRECT_OBSERVATION")
            for field in ("title", "artist", "absolute_position"):
                if track[field] is not None:
                    track["evidence"].append({
                        "source_key": source_key,
                        "field_name": field,
                        "provenance_type": provenance,
                    })
        result.append(track)
    return result


def _build_segments(
    values: dict[str, Any],
    completeness: str,
    sources: list[dict[str, Any]],
    has_tracks: bool,
) -> list[dict[str, Any]]:
    if completeness == "NOT_OBSERVED":
        if has_tracks:
            raise ValueError("NOT_OBSERVED cannot include track declarations")
        return []
    if not has_tracks:
        raise ValueError(f"{completeness} requires at least one explicit track declaration")
    start = _required_text(values, "captures_playlist_start")
    end = _required_text(values, "captures_playlist_end")
    segment = {
        "segment_ordinal": 1,
        "relationship_to_previous": "FIRST",
        "captures_playlist_start": start,
        "captures_playlist_end": end,
        "evidence": [],
    }
    valid_keys = {item["source_key"] for item in sources}
    for field, source_field in (
        ("captures_playlist_start", "start_source_key"),
        ("captures_playlist_end", "end_source_key"),
    ):
        source_key = values.get(source_field)
        if source_key:
            if source_key not in valid_keys:
                raise ValueError(f"{source_field} references an unknown staged source")
            segment["evidence"].append({
                "source_key": source_key,
                "field_name": field,
                "provenance_type": values.get("boundary_provenance_type", "DIRECT_OBSERVATION"),
            })
    return [segment]


def _build_top_level_evidence(
    kind: str,
    values: dict[str, Any],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    valid_keys = {item["source_key"] for item in sources}
    result = []
    mappings = values.get("top_level_evidence", [])
    if not isinstance(mappings, list):
        raise ValueError("top_level_evidence must be an explicit list")
    for index, mapping in enumerate(mappings, start=1):
        if not isinstance(mapping, dict):
            raise ValueError(f"top-level evidence link {index} must be an object")
        source_key = _required_text(mapping, "source_key")
        if source_key not in valid_keys:
            raise ValueError(f"top-level evidence link {index} references an unknown staged source")
        result.append({
            "source_key": source_key,
            "field_name": _required_text(mapping, "field_name"),
            "provenance_type": _required_text(mapping, "provenance_type"),
        })
    return result


def _present(values: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: values[field] for field in fields if values.get(field) not in (None, "")}


def _required_text(values: dict[str, Any], field: str) -> str:
    value = values.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be explicitly supplied")
    return value


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value != "" else None


def _required_bool(values: dict[str, Any], field: str) -> bool:
    value = values.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be explicitly supplied as true or false")
    return value
