from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from playlist_narrative_engine.track_evidence.schemas import (
    ISSUE_EXPLANATIONS,
    ISSUE_PRECEDENCE,
    EvidenceProvenance,
    RejectedTrackEvidence,
    TrackEvidenceIssue,
    TrackEvidenceIssueCode,
    TrackEvidenceValidationArtifact,
    TrackEvidenceValidationRequest,
    TrackEvidenceValidationSummary,
    ValidatedTrackEvidence,
)


_SUPPORTED_FIELDS = frozenset(
    {"track_id", "title", "artist_name", "duration_seconds", "provenance"}
)
_PROVENANCE_FIELDS = frozenset(
    {"source_type", "source_reference", "rationale"}
)
_ISSUE_INDEX = {code: index for index, code in enumerate(ISSUE_PRECEDENCE)}


class _DuplicateJsonKeyError(ValueError):
    pass


@dataclass
class _RecordState:
    record_id: str
    payload_json: str
    issues: list[TrackEvidenceIssue] = field(default_factory=list)
    track_id: str | None = None
    title: str | None = None
    artist_name: str | None = None
    duration_seconds: int | None = None
    provenance: EvidenceProvenance | None = None


def _utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(key)
        result[key] = value
    return result


def _issue(code: TrackEvidenceIssueCode, field_path: str) -> TrackEvidenceIssue:
    return TrackEvidenceIssue(
        code=code,
        field_path=field_path,
        explanation=ISSUE_EXPLANATIONS[code],
    )


def _valid_exact_string(value: object, *, max_length: int = 500) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= max_length
        and value == value.strip()
    )


class TrackEvidenceValidator:
    """Partition a source-neutral evidence snapshot without external access."""

    def validate(
        self,
        request: TrackEvidenceValidationRequest,
    ) -> TrackEvidenceValidationArtifact:
        artist_scope = tuple(
            sorted(
                (entry.artist_name for entry in request.artist_questionnaire.entries),
                key=_utf8_key,
            )
        )
        scope_set = set(artist_scope)
        states = [
            self._inspect_record(
                record.record_id,
                record.payload_json,
                scope_set,
            )
            for record in request.snapshot.records
        ]
        self._reject_all_duplicate_track_ids(states)
        states.sort(key=lambda state: _utf8_key(state.record_id))

        validated: list[ValidatedTrackEvidence] = []
        rejected: list[RejectedTrackEvidence] = []
        for state in states:
            if state.issues:
                rejected.append(
                    RejectedTrackEvidence(
                        record_id=state.record_id,
                        source_payload_json=state.payload_json,
                        issues=self._ordered_issues(state.issues),
                    )
                )
                continue
            if (
                state.track_id is None
                or state.title is None
                or state.artist_name is None
                or state.duration_seconds is None
                or state.provenance is None
            ):
                raise AssertionError("issue-free evidence must be complete")
            validated.append(
                ValidatedTrackEvidence(
                    ordinal=len(validated) + 1,
                    record_id=state.record_id,
                    source_payload_json=state.payload_json,
                    track_id=state.track_id,
                    title=state.title,
                    artist_name=state.artist_name,
                    duration_seconds=state.duration_seconds,
                    provenance=state.provenance,
                )
            )

        objective = request.objective_assessment.objective
        input_record_ids = tuple(state.record_id for state in states)
        return TrackEvidenceValidationArtifact(
            snapshot_id=request.snapshot.snapshot_id,
            objective_id=objective.objective_id,
            objective_statement=objective.statement,
            artist_inspection_scope=artist_scope,
            input_record_ids=input_record_ids,
            validated_records=tuple(validated),
            rejected_records=tuple(rejected),
            summary=TrackEvidenceValidationSummary(
                input_record_count=len(states),
                validated_record_count=len(validated),
                rejected_record_count=len(rejected),
            ),
        )

    def _inspect_record(
        self,
        record_id: str,
        payload_json: str,
        artist_scope: set[str],
    ) -> _RecordState:
        state = _RecordState(record_id=record_id, payload_json=payload_json)
        try:
            payload = json.loads(
                payload_json,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
        except _DuplicateJsonKeyError:
            state.issues.append(
                _issue(TrackEvidenceIssueCode.RECORD_DUPLICATE_KEY, "$")
            )
            return state
        except (json.JSONDecodeError, ValueError):
            state.issues.append(
                _issue(TrackEvidenceIssueCode.RECORD_INVALID_JSON, "$")
            )
            return state

        if not isinstance(payload, dict):
            state.issues.append(
                _issue(TrackEvidenceIssueCode.RECORD_NOT_OBJECT, "$")
            )
            return state

        for extra_field in sorted(set(payload) - _SUPPORTED_FIELDS, key=_utf8_key):
            state.issues.append(
                _issue(
                    TrackEvidenceIssueCode.RECORD_EXTRA_FIELD,
                    f"$.{extra_field}",
                )
            )

        state.track_id = self._inspect_text_field(
            payload,
            "track_id",
            TrackEvidenceIssueCode.TRACK_ID_MISSING,
            TrackEvidenceIssueCode.TRACK_ID_INVALID,
            state.issues,
        )
        state.title = self._inspect_text_field(
            payload,
            "title",
            TrackEvidenceIssueCode.TRACK_TITLE_MISSING,
            TrackEvidenceIssueCode.TRACK_TITLE_INVALID,
            state.issues,
        )
        state.artist_name = self._inspect_text_field(
            payload,
            "artist_name",
            TrackEvidenceIssueCode.TRACK_ARTIST_MISSING,
            TrackEvidenceIssueCode.TRACK_ARTIST_INVALID,
            state.issues,
        )
        if state.artist_name is not None and state.artist_name not in artist_scope:
            state.issues.append(
                _issue(
                    TrackEvidenceIssueCode.TRACK_ARTIST_OUT_OF_SCOPE,
                    "$.artist_name",
                )
            )

        if "duration_seconds" not in payload:
            state.issues.append(
                _issue(
                    TrackEvidenceIssueCode.TRACK_DURATION_MISSING,
                    "$.duration_seconds",
                )
            )
        else:
            duration = payload["duration_seconds"]
            if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
                state.issues.append(
                    _issue(
                        TrackEvidenceIssueCode.TRACK_DURATION_INVALID,
                        "$.duration_seconds",
                    )
                )
            else:
                state.duration_seconds = duration

        state.provenance = self._inspect_provenance(payload, state.issues)
        return state

    @staticmethod
    def _inspect_text_field(
        payload: dict[str, Any],
        field_name: str,
        missing_code: TrackEvidenceIssueCode,
        invalid_code: TrackEvidenceIssueCode,
        issues: list[TrackEvidenceIssue],
    ) -> str | None:
        if field_name not in payload:
            issues.append(_issue(missing_code, f"$.{field_name}"))
            return None
        value = payload[field_name]
        if not _valid_exact_string(value):
            issues.append(_issue(invalid_code, f"$.{field_name}"))
            return None
        return value

    @staticmethod
    def _inspect_provenance(
        payload: dict[str, Any],
        issues: list[TrackEvidenceIssue],
    ) -> EvidenceProvenance | None:
        if "provenance" not in payload:
            issues.append(
                _issue(
                    TrackEvidenceIssueCode.EVIDENCE_PROVENANCE_MISSING,
                    "$.provenance",
                )
            )
            return None
        provenance = payload["provenance"]
        if (
            not isinstance(provenance, dict)
            or set(provenance) != _PROVENANCE_FIELDS
            or any(
                not _valid_exact_string(provenance.get(field_name), max_length=1_000)
                for field_name in _PROVENANCE_FIELDS
            )
        ):
            issues.append(
                _issue(
                    TrackEvidenceIssueCode.EVIDENCE_PROVENANCE_INVALID,
                    "$.provenance",
                )
            )
            return None
        return EvidenceProvenance.model_validate(provenance)

    @staticmethod
    def _reject_all_duplicate_track_ids(states: list[_RecordState]) -> None:
        by_track_id: dict[str, list[_RecordState]] = {}
        for state in states:
            if state.track_id is not None:
                by_track_id.setdefault(state.track_id, []).append(state)
        for duplicate_states in by_track_id.values():
            if len(duplicate_states) < 2:
                continue
            for state in duplicate_states:
                state.issues.append(
                    _issue(
                        TrackEvidenceIssueCode.DUPLICATE_TRACK_ID,
                        "$.track_id",
                    )
                )

    @staticmethod
    def _ordered_issues(
        issues: list[TrackEvidenceIssue],
    ) -> tuple[TrackEvidenceIssue, ...]:
        return tuple(
            sorted(
                issues,
                key=lambda issue: (
                    _ISSUE_INDEX[issue.code],
                    _utf8_key(issue.field_path),
                ),
            )
        )


def serialize_track_evidence_validation(
    artifact: TrackEvidenceValidationArtifact,
) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    serialized = json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return serialized.encode("utf-8")
