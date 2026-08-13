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
        constraints = declarations.get("constraints", [])
        if not isinstance(constraints, list):
            raise ValueError("constraints must be an explicit list")
        proposal["constraints"] = constraints
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
        "evidence_standard", "assessment_outcome", "assessment", "notes",
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
        source = {
            "source_key": f"source_{index}",
            "source_type": source_type,
            "source_reference": source_reference,
        }
        for field in ("original_filename", "local_path", "sha256", "notes"):
            value = _optional_text(item.get(field))
            if value is not None:
                source[field] = value
        sources.append(source)
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
        source_keys = item.get("source_keys")
        if source_keys is None:
            source_key = item.get("source_key")
            source_keys = [] if source_key is None else [source_key]
        if not isinstance(source_keys, list) or not all(isinstance(key, str) for key in source_keys):
            raise ValueError(f"track {index} source_keys must be an explicit list")
        if any(key not in valid_keys for key in source_keys):
            raise ValueError(f"track {index} references an unknown staged source")
        track = {
            "observed_ordinal": index,
            "evidence_segment": 1,
            "segment_ordinal": index,
            "absolute_position": item.get("absolute_position"),
            "title": title,
            "artist": artist,
            "version_or_remaster_text": _optional_text(item.get("version_or_remaster_text")),
            "notes": _optional_text(item.get("notes")),
            "canonical_identity_established": _required_bool(item, "canonical_identity_established"),
            "evidence": [],
        }
        if source_keys:
            provenance = item.get("provenance_type", "DIRECT_OBSERVATION")
            support_status = item.get("support_status", "FULL")
            for source_key in source_keys:
                for field in ("title", "artist", "absolute_position", "version_or_remaster_text"):
                    if track[field] is not None:
                        track["evidence"].append({
                            "source_key": source_key,
                            "field_name": field,
                            "provenance_type": provenance,
                            "support_status": support_status,
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
            "support_status": mapping.get("support_status", "FULL"),
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
