from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from playlist_narrative_engine.research_store.service import (
    EvidenceVerificationResult,
    ResearchStoreService,
    ValidationResult,
)
from playlist_narrative_engine.research_store.schemas import GenerationFailureInput
from playlist_narrative_engine.research_store.study_schemas import (
    StudyOperationalAttemptInput,
    StudyRegistrationInput,
    StudyRunDisposition,
)


ProposalKind = Literal["historical_experiment", "current_persisted_artifact"]


@dataclass(frozen=True)
class StagedEvidence:
    original_filename: str
    local_path: str
    sha256: str
    size_bytes: int


def default_staging_root() -> Path:
    configured = os.getenv("PNE_MAESTRO_WORKBENCH_STAGING")
    if configured:
        return Path(configured)
    local_data = os.getenv("LOCALAPPDATA")
    if local_data:
        return Path(local_data) / "PlaylistNarrativeEngine" / "MaestroWorkbench" / "evidence"
    return Path(tempfile.gettempdir()) / "PlaylistNarrativeEngine" / "MaestroWorkbench" / "evidence"


class EvidenceStager:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or default_staging_root()

    def stage(self, filename: str, content: bytes) -> StagedEvidence:
        original_filename = Path(filename).name
        if not original_filename or original_filename in {".", ".."}:
            raise ValueError("an original filename is required")
        destination_directory = self._root / uuid.uuid4().hex
        destination_directory.mkdir(parents=True, exist_ok=False)
        destination = destination_directory / original_filename
        destination.write_bytes(content)
        return StagedEvidence(
            original_filename=original_filename,
            local_path=str(destination.resolve()),
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
        )


class WorkbenchOperations:
    def __init__(self, service: ResearchStoreService) -> None:
        self._service = service

    def validate(self, kind: str, proposal: object) -> dict[str, object]:
        validation = self._validate(kind, proposal)
        if not validation.valid:
            return {
                "valid": False,
                "validation_issues": [asdict(item) for item in validation.issues],
                "evidence_valid": None,
                "evidence_issues": [],
            }
        evidence = self._verify(kind, validation.value)
        return {
            "valid": evidence.valid,
            "validation_issues": [],
            "evidence_valid": evidence.valid,
            "evidence_issues": [asdict(item) for item in evidence.issues],
        }

    def ingest(self, kind: str, proposal: object) -> dict[str, object]:
        validation = self._validate(kind, proposal)
        if not validation.valid:
            raise ValueError("proposal failed governed schema validation")
        evidence = self._verify(kind, validation.value)
        if not evidence.valid:
            raise ValueError("proposal failed governed evidence verification")
        if kind == "historical_experiment":
            inserted = self._service.ingest_experiment(validation.value)
        else:
            inserted = self._service.ingest_persisted_artifact(validation.value)
        return {
            "kind": inserted.kind,
            "record_id": inserted.record_id,
            "record": inserted.record,
        }

    def validate_study(self, proposal: object) -> dict[str, object]:
        validation = self._service.validate_study_protocol(proposal)
        return {
            "valid": validation.valid,
            "validation_issues": [asdict(item) for item in validation.issues],
            "canonical_proposal": None if validation.value is None else validation.value.model_dump(mode="json"),
        }

    def register_study(self, proposal: object) -> dict[str, object]:
        validation = self._service.validate_study_protocol(proposal)
        if not validation.valid:
            raise ValueError("study proposal failed governed schema validation")
        return self._service.register_study(validation.value)

    def list_studies(self) -> list[dict[str, object]]:
        return self._service.list_studies()

    def get_study(self, study_id_or_key: int | str) -> dict[str, object] | None:
        return self._service.get_study(study_id_or_key)

    def get_protocol(self, study_id_or_key: int | str, version: int) -> dict[str, object] | None:
        return self._service.get_protocol_version(study_id_or_key, version)

    def record_operational_attempt(self, planned_run_id: int, proposal: object) -> dict[str, object]:
        draft = StudyOperationalAttemptInput.model_validate(proposal)
        return self._service.record_study_operational_attempt(planned_run_id, draft)

    def record_study_failure(
        self, planned_run_id: int, disposition: str, proposal: object
    ) -> dict[str, object]:
        draft = GenerationFailureInput.model_validate(proposal)
        return self._service.record_planned_generation_failure(
            planned_run_id, draft, StudyRunDisposition(disposition)
        )

    def realize_study_experiment(self, planned_run_id: int, proposal: object) -> dict[str, object]:
        validation = self._service.validate_experiment(proposal)
        if not validation.valid:
            raise ValueError("proposal failed governed schema validation")
        evidence = self._service.verify_experiment_evidence(validation.value)
        if not evidence.valid:
            raise ValueError("proposal failed governed evidence verification")
        realization = self._service.ingest_planned_experiment(planned_run_id, validation.value)
        record = self._service.get_experiment(int(realization["experiment_id"]))
        return {"kind": "experiment", "record_id": realization["experiment_id"], "record": record, "realization": realization}

    def _validate(self, kind: str, proposal: object) -> ValidationResult:
        _require_supported_kind(kind)
        if kind == "historical_experiment":
            return self._service.validate_experiment(proposal)
        return self._service.validate_persisted_artifact(proposal)

    def _verify(self, kind: str, proposal) -> EvidenceVerificationResult:
        if kind == "historical_experiment":
            return self._service.verify_experiment_evidence(proposal)
        return self._service.verify_persisted_artifact_evidence(proposal)


def _require_supported_kind(kind: str) -> None:
    if kind not in {"historical_experiment", "current_persisted_artifact"}:
        raise ValueError(f"unsupported workbench proposal kind: {kind}")
