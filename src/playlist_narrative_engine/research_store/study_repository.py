from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from playlist_narrative_engine.research_store.models import (
    Constraint,
    GenerationFailure,
    Study,
    StudyAnalysisDefinition,
    StudyBlock,
    StudyCondition,
    StudyConstraintDefinition,
    StudyOutcomeDefinition,
    StudyPlannedRun,
    StudyPlannedRunConstraint,
    StudyProtocolVersion,
    StudyRunAttempt,
    StudyRunRealization,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    ExperimentInput,
    GenerationFailureInput,
)
from playlist_narrative_engine.research_store.study_protocol import (
    protocol_registration_hash,
)
from playlist_narrative_engine.research_store.study_schemas import (
    StudyOperationalAttemptInput,
    StudyProtocolAmendmentInput,
    StudyProtocolInput,
    StudyRegistrationInput,
    StudyRunDisposition,
)


class StudyRepository:
    """Persistence boundary for prospective study registration and execution."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._research = ResearchRepository(session)

    def register_study(self, draft: StudyRegistrationInput) -> dict[str, object]:
        with self.session.begin():
            if self.session.scalar(select(Study.id).where(Study.study_key == draft.study_key)):
                raise ValueError(f"study_key already exists: {draft.study_key}")
            study = Study(study_key=draft.study_key, title=draft.title)
            self.session.add(study)
            self.session.flush()
            protocol = self._insert_protocol(
                study, draft.protocol, predecessor=None,
                registration_hash=protocol_registration_hash(
                    draft.study_key, draft.title, draft.protocol
                ),
            )
            study_id = study.id
            version = protocol.version_number
            result = self.get_study(study_id)
            if result is None:
                raise RuntimeError("registered study could not be read back")
            result["registered_protocol_version"] = version
            result["registered_protocol"] = self._protocol_dict(study, protocol)
            return result

    def register_protocol_amendment(
        self, study_id: int, draft: StudyProtocolAmendmentInput
    ) -> dict[str, object]:
        with self.session.begin():
            study = self.session.get(Study, study_id)
            if study is None:
                raise ValueError(f"study not found: {study_id}")
            predecessor = self.session.scalar(
                select(StudyProtocolVersion).where(
                    StudyProtocolVersion.study_id == study.id,
                    StudyProtocolVersion.version_number == draft.predecessor_version,
                )
            )
            if predecessor is None or predecessor.registered_at is None:
                raise ValueError("amendment predecessor must be a registered version of the same study")
            existing = self.session.scalar(
                select(StudyProtocolVersion.id).where(
                    StudyProtocolVersion.study_id == study.id,
                    StudyProtocolVersion.version_number == draft.protocol.version_number,
                )
            )
            if existing is not None:
                raise ValueError("protocol version already exists")
            protocol = self._insert_protocol(
                study, draft.protocol, predecessor=predecessor,
                registration_hash=protocol_registration_hash(
                    study.study_key, study.title, draft.protocol
                ),
            )
            version = protocol.version_number
            result = self.get_protocol_version(study_id, version)
            if result is None:
                raise RuntimeError("registered amendment could not be read back")
            return result

    def _insert_protocol(
        self,
        study: Study,
        draft: StudyProtocolInput,
        *,
        predecessor: StudyProtocolVersion | None,
        registration_hash: str,
    ) -> StudyProtocolVersion:
        protocol = StudyProtocolVersion(
            study_id=study.id,
            version_number=draft.version_number,
            predecessor_version_id=None if predecessor is None else predecessor.id,
            registered_at=None,
            registration_hash=None,
            amendment_reason=draft.amendment_reason,
            objective=draft.objective,
            primary_hypothesis=draft.primary_hypothesis,
            null_hypothesis=draft.null_hypothesis,
            design_summary=draft.design_summary,
            planned_sample_size=draft.planned_sample_size,
            randomization_method=draft.randomization_method,
            randomization_seed=draft.randomization_seed,
            operational_failure_policy=draft.operational_failure_policy,
            operational_failure_consumes_run=draft.operational_failure_consumes_run,
            refusal_policy=draft.refusal_policy,
            missing_result_policy=draft.missing_result_policy,
        )
        self.session.add(protocol)
        self.session.flush()

        conditions: dict[str, StudyCondition] = {}
        for item in draft.conditions:
            value = StudyCondition(
                protocol_version_id=protocol.id,
                condition_key=item.condition_key,
                label=item.label,
                role=item.role.value,
                exact_factor_definition=item.exact_factor_definition,
            )
            self.session.add(value)
            conditions[item.condition_key] = value
        blocks: dict[str, StudyBlock] = {}
        for item in draft.blocks:
            value = StudyBlock(
                protocol_version_id=protocol.id,
                block_key=item.block_key,
                label=item.label,
                block_definition=item.block_definition,
            )
            self.session.add(value)
            blocks[item.block_key] = value
        constraint_definitions: dict[str, StudyConstraintDefinition] = {}
        for item in draft.constraint_definitions:
            value = StudyConstraintDefinition(
                protocol_version_id=protocol.id,
                constraint_key=item.constraint_key,
                constraint_type=item.constraint_type,
                constraint_text=item.constraint_text,
                is_hard_constraint=item.is_hard_constraint,
                evaluation_rule=item.evaluation_rule,
                permitted_result_provenance=item.permitted_result_provenance.value,
                unknown_handling=item.unknown_handling,
            )
            self.session.add(value)
            constraint_definitions[item.constraint_key] = value
        outcomes: dict[str, StudyOutcomeDefinition] = {}
        for item in draft.outcome_definitions:
            value = StudyOutcomeDefinition(
                protocol_version_id=protocol.id,
                outcome_key=item.outcome_key,
                role=item.role.value,
                unit_of_analysis=item.unit_of_analysis,
                outcome_definition=item.outcome_definition,
                computation_rule=item.computation_rule,
                missing_data_rule=item.missing_data_rule,
                refusal_handling=item.refusal_handling,
                operational_failure_handling=item.operational_failure_handling,
            )
            self.session.add(value)
            outcomes[item.outcome_key] = value
        self.session.flush()
        for item in draft.analysis_definitions:
            self.session.add(StudyAnalysisDefinition(
                protocol_version_id=protocol.id,
                outcome_definition_id=outcomes[item.outcome_key].id,
                analysis_key=item.analysis_key,
                analysis_population=item.analysis_population,
                comparison_definition=item.comparison_definition,
                aggregation_rule=item.aggregation_rule,
                exclusion_rule=item.exclusion_rule,
                reporting_rule=item.reporting_rule,
            ))
        self.session.flush()

        runs: dict[str, StudyPlannedRun] = {}
        for item in draft.planned_runs:
            value = StudyPlannedRun(
                protocol_version_id=protocol.id,
                condition_id=conditions[item.condition_key].id,
                block_id=blocks[item.block_key].id,
                run_key=item.run_key,
                replicate_number=item.replicate_number,
                randomized_ordinal=item.randomized_ordinal,
                planned_prompt_text=item.planned_prompt_text,
                planned_source_system=item.planned_source_system,
                replacement_for_run_id=None,
            )
            self.session.add(value)
            runs[item.run_key] = value
        self.session.flush()
        for item in draft.planned_runs:
            run = runs[item.run_key]
            if item.replacement_for_run_key is not None:
                run.replacement_for_run_id = runs[item.replacement_for_run_key].id
            for key in item.applicable_constraint_keys:
                self.session.add(StudyPlannedRunConstraint(
                    planned_run_id=run.id,
                    constraint_definition_id=constraint_definitions[key].id,
                ))
        self.session.flush()
        self.session.execute(
            update(StudyProtocolVersion)
            .where(StudyProtocolVersion.id == protocol.id)
            .values(
                registered_at=func.current_timestamp(),
                registration_hash=registration_hash,
            )
        )
        self.session.flush()
        self.session.expire(protocol)
        if protocol.registered_at is None:
            raise RuntimeError("database did not assign protocol registration time")
        return protocol

    def record_operational_attempt(
        self, planned_run_id: int, draft: StudyOperationalAttemptInput
    ) -> dict[str, object]:
        with self.session.begin():
            run = self._registered_open_run(planned_run_id)
            attempt_number = (
                self.session.scalar(
                    select(func.max(StudyRunAttempt.attempt_number)).where(
                        StudyRunAttempt.planned_run_id == run.id
                    )
                ) or 0
            ) + 1
            attempt = StudyRunAttempt(
                planned_run_id=run.id,
                attempt_number=attempt_number,
                attempt_type="OPERATIONAL_FAILURE",
                consumes_planned_run=self.session.get(
                    StudyProtocolVersion, run.protocol_version_id
                ).operational_failure_consumes_run,
                failure_code=draft.failure_code,
                notes=draft.notes,
            )
            self.session.add(attempt)
            self.session.flush()
            return self._attempt_dict(attempt)

    def realize_experiment(
        self, planned_run_id: int, draft: ExperimentInput
    ) -> dict[str, object]:
        with self.session.begin():
            run = self._registered_open_run(planned_run_id)
            self._validate_experiment_against_run(run, draft)
            experiment_id = self._research.insert_experiment(draft)
            realization = StudyRunRealization(
                planned_run_id=run.id,
                disposition=StudyRunDisposition.EXPERIMENT_RECORDED.value,
                experiment_id=experiment_id,
                generation_failure_id=None,
            )
            self.session.add(realization)
            self.session.flush()
            return self._realization_dict(realization)

    def realize_generation_failure(
        self,
        planned_run_id: int,
        draft: GenerationFailureInput,
        disposition: StudyRunDisposition,
    ) -> dict[str, object]:
        if disposition not in {
            StudyRunDisposition.MAESTRO_REFUSAL_RECORDED,
            StudyRunDisposition.MAESTRO_FAILURE_RECORDED,
        }:
            raise ValueError("generation-failure realization requires a Maestro failure disposition")
        with self.session.begin():
            run = self._registered_open_run(planned_run_id)
            if draft.prompt != run.planned_prompt_text:
                raise ValueError("generation-failure prompt must exactly match the planned prompt")
            if run.planned_source_system is not None and draft.source_system != run.planned_source_system:
                raise ValueError("generation-failure source system must match the planned source system")
            failure_id = self._research.record_generation_failure(draft)
            realization = StudyRunRealization(
                planned_run_id=run.id,
                disposition=disposition.value,
                experiment_id=None,
                generation_failure_id=failure_id,
            )
            self.session.add(realization)
            self.session.flush()
            return self._realization_dict(realization)

    def _registered_open_run(self, planned_run_id: int) -> StudyPlannedRun:
        run = self.session.get(StudyPlannedRun, planned_run_id)
        if run is None:
            raise ValueError(f"planned run not found: {planned_run_id}")
        protocol = self.session.get(StudyProtocolVersion, run.protocol_version_id)
        if protocol is None or protocol.registered_at is None:
            raise ValueError("planned run must belong to a registered protocol")
        realized = self.session.scalar(
            select(StudyRunRealization.id).where(StudyRunRealization.planned_run_id == run.id)
        )
        if realized is not None:
            raise ValueError("planned run already has a terminal scientific realization")
        consumed = self.session.scalar(
            select(StudyRunAttempt.id).where(
                StudyRunAttempt.planned_run_id == run.id,
                StudyRunAttempt.consumes_planned_run.is_(True),
            )
        )
        if consumed is not None:
            raise ValueError("planned run was consumed by protocol-authorized operational failure")
        return run

    def _validate_experiment_against_run(
        self, run: StudyPlannedRun, draft: ExperimentInput
    ) -> None:
        if draft.prompt != run.planned_prompt_text:
            raise ValueError("experiment prompt must exactly match the planned prompt")
        if run.planned_source_system is not None and draft.source_system != run.planned_source_system:
            raise ValueError("experiment source system must match the planned source system")
        definitions = list(self.session.scalars(
            select(StudyConstraintDefinition)
            .join(
                StudyPlannedRunConstraint,
                StudyPlannedRunConstraint.constraint_definition_id == StudyConstraintDefinition.id,
            )
            .where(StudyPlannedRunConstraint.planned_run_id == run.id)
            .order_by(StudyConstraintDefinition.id)
        ))
        supplied = {item.study_constraint_definition_id: item for item in draft.constraints}
        expected_ids = {item.id for item in definitions}
        if None in supplied or set(supplied) != expected_ids or len(supplied) != len(draft.constraints):
            raise ValueError("experiment must materialize exactly the planned run constraints")
        for definition in definitions:
            item = supplied[definition.id]
            if (
                item.constraint_type != definition.constraint_type
                or item.constraint_text != definition.constraint_text
                or item.is_hard_constraint != definition.is_hard_constraint
            ):
                raise ValueError("experiment constraint snapshot must exactly match its frozen definition")
            if item.result is not None and item.result.provenance_type.value != definition.permitted_result_provenance:
                raise ValueError("constraint result provenance is not permitted by its frozen definition")

    def get_study(self, study_id_or_key: int | str) -> dict[str, object] | None:
        study = self._resolve_study(study_id_or_key)
        if study is None:
            return None
        versions = list(self.session.scalars(
            select(StudyProtocolVersion)
            .where(StudyProtocolVersion.study_id == study.id)
            .order_by(StudyProtocolVersion.version_number)
        ))
        current = versions[-1] if versions else None
        counts = {
            "planned_run_count": 0,
            "realized_run_count": 0,
            "operational_attempt_count": 0,
            "remaining_executable_run_count": 0,
        }
        if current is not None:
            runs = list(self.session.scalars(select(StudyPlannedRun).where(
                StudyPlannedRun.protocol_version_id == current.id
            )))
            run_ids = [item.id for item in runs]
            realized_ids = set(self.session.scalars(select(StudyRunRealization.planned_run_id).where(
                StudyRunRealization.planned_run_id.in_(run_ids or [-1])
            )))
            attempts = list(self.session.scalars(select(StudyRunAttempt).where(
                StudyRunAttempt.planned_run_id.in_(run_ids or [-1])
            )))
            consumed_ids = {item.planned_run_id for item in attempts if item.consumes_planned_run}
            counts = {
                "planned_run_count": len(runs),
                "realized_run_count": len(realized_ids),
                "operational_attempt_count": len(attempts),
                "remaining_executable_run_count": len(run_ids) - len(realized_ids | consumed_ids),
            }
        return {
            "id": study.id,
            "study_key": study.study_key,
            "title": study.title,
            "created_at": study.created_at.isoformat(),
            "protocol_versions": [self._protocol_summary(item) for item in versions],
            **counts,
        }

    def get_protocol_version(
        self, study_id_or_key: int | str, version: int
    ) -> dict[str, object] | None:
        study = self._resolve_study(study_id_or_key)
        if study is None:
            return None
        protocol = self.session.scalar(select(StudyProtocolVersion).where(
            StudyProtocolVersion.study_id == study.id,
            StudyProtocolVersion.version_number == version,
        ))
        if protocol is None:
            return None
        return self._protocol_dict(study, protocol)

    def list_studies(self) -> list[dict[str, object]]:
        return [self.get_study(item.id) for item in self.session.scalars(select(Study).order_by(Study.study_key))]

    def _resolve_study(self, value: int | str) -> Study | None:
        if isinstance(value, int):
            return self.session.get(Study, value)
        return self.session.scalar(select(Study).where(Study.study_key == value))

    def _protocol_dict(self, study: Study, protocol: StudyProtocolVersion) -> dict[str, object]:
        conditions = list(self.session.scalars(select(StudyCondition).where(StudyCondition.protocol_version_id == protocol.id).order_by(StudyCondition.id)))
        blocks = list(self.session.scalars(select(StudyBlock).where(StudyBlock.protocol_version_id == protocol.id).order_by(StudyBlock.id)))
        constraints = list(self.session.scalars(select(StudyConstraintDefinition).where(StudyConstraintDefinition.protocol_version_id == protocol.id).order_by(StudyConstraintDefinition.id)))
        outcomes = list(self.session.scalars(select(StudyOutcomeDefinition).where(StudyOutcomeDefinition.protocol_version_id == protocol.id).order_by(StudyOutcomeDefinition.id)))
        analyses = list(self.session.scalars(select(StudyAnalysisDefinition).where(StudyAnalysisDefinition.protocol_version_id == protocol.id).order_by(StudyAnalysisDefinition.id)))
        runs = list(self.session.scalars(select(StudyPlannedRun).where(StudyPlannedRun.protocol_version_id == protocol.id).order_by(StudyPlannedRun.randomized_ordinal)))
        condition_by_id = {item.id: item.condition_key for item in conditions}
        block_by_id = {item.id: item.block_key for item in blocks}
        outcome_by_id = {item.id: item.outcome_key for item in outcomes}
        return {
            "study_id": study.id,
            "study_key": study.study_key,
            "title": study.title,
            **self._protocol_summary(protocol),
            "objective": protocol.objective,
            "primary_hypothesis": protocol.primary_hypothesis,
            "null_hypothesis": protocol.null_hypothesis,
            "design_summary": protocol.design_summary,
            "planned_sample_size": protocol.planned_sample_size,
            "randomization_method": protocol.randomization_method,
            "randomization_seed": protocol.randomization_seed,
            "operational_failure_policy": protocol.operational_failure_policy,
            "operational_failure_consumes_run": protocol.operational_failure_consumes_run,
            "refusal_policy": protocol.refusal_policy,
            "missing_result_policy": protocol.missing_result_policy,
            "conditions": [{"id": x.id, "condition_key": x.condition_key, "label": x.label, "role": x.role, "exact_factor_definition": x.exact_factor_definition} for x in conditions],
            "blocks": [{"id": x.id, "block_key": x.block_key, "label": x.label, "block_definition": x.block_definition} for x in blocks],
            "constraint_definitions": [{"id": x.id, "constraint_key": x.constraint_key, "constraint_type": x.constraint_type, "constraint_text": x.constraint_text, "is_hard_constraint": x.is_hard_constraint, "evaluation_rule": x.evaluation_rule, "permitted_result_provenance": x.permitted_result_provenance, "unknown_handling": x.unknown_handling} for x in constraints],
            "outcome_definitions": [{"id": x.id, "outcome_key": x.outcome_key, "role": x.role, "unit_of_analysis": x.unit_of_analysis, "outcome_definition": x.outcome_definition, "computation_rule": x.computation_rule, "missing_data_rule": x.missing_data_rule, "refusal_handling": x.refusal_handling, "operational_failure_handling": x.operational_failure_handling} for x in outcomes],
            "analysis_definitions": [{"id": x.id, "analysis_key": x.analysis_key, "outcome_key": outcome_by_id[x.outcome_definition_id], "analysis_population": x.analysis_population, "comparison_definition": x.comparison_definition, "aggregation_rule": x.aggregation_rule, "exclusion_rule": x.exclusion_rule, "reporting_rule": x.reporting_rule} for x in analyses],
            "planned_runs": [self._run_dict(x, condition_by_id, block_by_id) for x in runs],
        }

    def _run_dict(self, run, condition_by_id, block_by_id):
        applicable = list(self.session.scalars(select(StudyConstraintDefinition.constraint_key).join(StudyPlannedRunConstraint, StudyPlannedRunConstraint.constraint_definition_id == StudyConstraintDefinition.id).where(StudyPlannedRunConstraint.planned_run_id == run.id).order_by(StudyConstraintDefinition.id)))
        attempts = list(self.session.scalars(select(StudyRunAttempt).where(StudyRunAttempt.planned_run_id == run.id).order_by(StudyRunAttempt.attempt_number)))
        realization = self.session.scalar(select(StudyRunRealization).where(StudyRunRealization.planned_run_id == run.id))
        replacement = self.session.get(StudyPlannedRun, run.replacement_for_run_id) if run.replacement_for_run_id else None
        return {"id": run.id, "run_key": run.run_key, "condition_key": condition_by_id[run.condition_id], "block_key": block_by_id[run.block_id], "replicate_number": run.replicate_number, "randomized_ordinal": run.randomized_ordinal, "planned_prompt_text": run.planned_prompt_text, "planned_source_system": run.planned_source_system, "replacement_for_run_key": None if replacement is None else replacement.run_key, "applicable_constraint_keys": applicable, "attempts": [self._attempt_dict(x) for x in attempts], "realization": None if realization is None else self._realization_dict(realization)}

    @staticmethod
    def _protocol_summary(item):
        return {"id": item.id, "version_number": item.version_number, "predecessor_version_id": item.predecessor_version_id, "registered_at": None if item.registered_at is None else item.registered_at.isoformat(), "registration_hash": item.registration_hash, "amendment_reason": item.amendment_reason}

    @staticmethod
    def _attempt_dict(item):
        return {"id": item.id, "planned_run_id": item.planned_run_id, "attempt_number": item.attempt_number, "attempted_at": item.attempted_at.isoformat(), "attempt_type": item.attempt_type, "consumes_planned_run": item.consumes_planned_run, "failure_code": item.failure_code, "notes": item.notes}

    @staticmethod
    def _realization_dict(item):
        return {"id": item.id, "planned_run_id": item.planned_run_id, "disposition": item.disposition, "experiment_id": item.experiment_id, "generation_failure_id": item.generation_failure_id, "realized_at": item.realized_at.isoformat()}
