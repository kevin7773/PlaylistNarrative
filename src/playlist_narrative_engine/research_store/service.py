from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Literal, TypeVar

from pydantic import ValidationError

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    EvidenceSourceInput,
    ExperimentInput,
    PersistedPlaylistArtifactInput,
)


ValidatedValue = TypeVar("ValidatedValue")
RecordKind = Literal["experiment", "persisted_artifact"]


@dataclass(frozen=True)
class ValidationIssue:
    location: tuple[str | int, ...]
    message: str
    issue_type: str


@dataclass(frozen=True)
class ValidationResult(Generic[ValidatedValue]):
    value: ValidatedValue | None
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return self.value is not None and not self.issues


@dataclass(frozen=True)
class EvidenceVerificationIssue:
    source_key: str
    local_path: str
    issue_type: Literal["file_not_found", "checksum_mismatch"]
    message: str


@dataclass(frozen=True)
class EvidenceVerificationResult:
    issues: tuple[EvidenceVerificationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class IngestedRecord:
    kind: RecordKind
    record_id: int
    record: dict[str, object]


class ResearchStoreService:
    """Orchestrate existing research-store operations without adding semantics."""

    def __init__(self, repository: ResearchRepository) -> None:
        self._repository = repository

    @staticmethod
    def validate_experiment(proposal: object) -> ValidationResult[ExperimentInput]:
        return _validate(ExperimentInput, proposal)

    @staticmethod
    def validate_persisted_artifact(
        proposal: object,
    ) -> ValidationResult[PersistedPlaylistArtifactInput]:
        return _validate(PersistedPlaylistArtifactInput, proposal)

    @staticmethod
    def verify_experiment_evidence(
        proposal: ExperimentInput,
    ) -> EvidenceVerificationResult:
        return _verify_sources(proposal.evidence_sources)

    @staticmethod
    def verify_persisted_artifact_evidence(
        proposal: PersistedPlaylistArtifactInput,
    ) -> EvidenceVerificationResult:
        return _verify_sources(proposal.evidence_sources)

    def ingest_experiment(self, proposal: ExperimentInput) -> IngestedRecord:
        _require_type(proposal, ExperimentInput)
        record_id = self._repository.insert_experiment(proposal)
        record = self._repository.get_experiment(record_id)
        if record is None:
            raise RuntimeError("inserted experiment could not be read back")
        return IngestedRecord("experiment", record_id, record)

    def ingest_persisted_artifact(
        self, proposal: PersistedPlaylistArtifactInput
    ) -> IngestedRecord:
        _require_type(proposal, PersistedPlaylistArtifactInput)
        record_id = self._repository.insert_persisted_artifact(proposal)
        record = self._repository.get_persisted_artifact(record_id)
        if record is None:
            raise RuntimeError("inserted persisted artifact could not be read back")
        return IngestedRecord("persisted_artifact", record_id, record)

    def get_experiment(self, record_id: int) -> dict[str, object] | None:
        return self._repository.get_experiment(record_id)

    def get_persisted_artifact(self, record_id: int) -> dict[str, object] | None:
        return self._repository.get_persisted_artifact(record_id)


def _validate(model_type: type[ValidatedValue], proposal: object) -> ValidationResult[ValidatedValue]:
    try:
        value = model_type.model_validate(proposal)  # type: ignore[attr-defined]
    except ValidationError as exc:
        issues = tuple(
            ValidationIssue(
                location=tuple(item["loc"]),
                message=item["msg"],
                issue_type=item["type"],
            )
            for item in exc.errors()
        )
        return ValidationResult(value=None, issues=issues)
    return ValidationResult(value=value)


def _verify_sources(sources: list[EvidenceSourceInput]) -> EvidenceVerificationResult:
    issues: list[EvidenceVerificationIssue] = []
    for source in sources:
        if source.local_path is None:
            continue
        path = Path(source.local_path)
        if not path.is_file():
            issues.append(EvidenceVerificationIssue(
                source_key=source.source_key,
                local_path=source.local_path,
                issue_type="file_not_found",
                message=f"local evidence file not found: {path}",
            ))
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.lower() != source.sha256.lower():
            issues.append(EvidenceVerificationIssue(
                source_key=source.source_key,
                local_path=source.local_path,
                issue_type="checksum_mismatch",
                message=f"evidence checksum mismatch: {path}",
            ))
    return EvidenceVerificationResult(tuple(issues))


def _require_type(value: object, expected: type[object]) -> None:
    if not isinstance(value, expected):
        raise TypeError(f"ingestion requires a validated {expected.__name__}")
