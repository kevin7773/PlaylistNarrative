from __future__ import annotations

from playlist_narrative_engine.evidence_authentication.schemas import (
    APPROVED_AUTHENTICATION_RULE_SET,
    APPROVED_AUTHENTICATION_RULE_SET_SHA256,
    AUTHENTICATION_REASON_EXPLANATIONS,
    GOVERNED_CHARACTERISTIC_BY_KEY,
    AuthenticationAttempt,
    AuthenticationMethod,
    AuthenticationReason,
    AuthenticationReasonCode,
    AuthenticationSourceObservation,
    AuthenticationSummary,
    AuthenticationRule,
    AuthenticatedStructuredCharacteristic,
    AuthenticatedStructuredCharacteristicArtifact,
    AuthenticatedStructuredCharacteristicArtifactContent,
    DerivationLineage,
    EvidenceAuthenticationRequest,
    ExactConfirmationAttempt,
    ExactConfirmationLineage,
    VersionedDerivationAttempt,
    WithheldAuthenticationAttempt,
    _canonical_model_bytes,
    _sha256,
    authentication_failure_specs,
)


def _reason(
    code: AuthenticationReasonCode,
    field_path: str,
) -> AuthenticationReason:
    return AuthenticationReason(
        code=code,
        field_path=field_path,
        explanation=AUTHENTICATION_REASON_EXPLANATIONS[code],
    )


def _referenced_observations(
    attempt: AuthenticationAttempt,
    observations_by_id: dict[str, AuthenticationSourceObservation],
) -> tuple[AuthenticationSourceObservation, ...]:
    ids = (
        (attempt.confirmation_evidence_id,)
        if isinstance(attempt, ExactConfirmationAttempt)
        else attempt.input_evidence_ids
    )
    return tuple(
        observations_by_id[evidence_id]
        for evidence_id in ids
        if evidence_id in observations_by_id
    )


class EvidenceAuthenticationBoundary:
    """Mint governed characteristics only through approved authentication paths."""

    def authenticate(
        self,
        request: EvidenceAuthenticationRequest,
        *,
        artifact_id: str,
    ) -> AuthenticatedStructuredCharacteristicArtifact:
        observations_by_id = {
            observation.evidence_id: observation for observation in request.observations
        }
        rules_by_id = {
            rule.rule_id: rule for rule in request.authentication_rule_set.rules
        }
        authenticated: list[AuthenticatedStructuredCharacteristic] = []
        withheld: list[WithheldAuthenticationAttempt] = []

        for attempt in request.attempts:
            if isinstance(attempt, ExactConfirmationAttempt):
                result, reasons = self._authenticate_confirmation(
                    attempt, observations_by_id
                )
            else:
                result, reasons = self._authenticate_derivation(
                    attempt, observations_by_id, rules_by_id
                )
            if result is not None:
                authenticated.append(result)
            else:
                withheld.append(
                    WithheldAuthenticationAttempt(
                        attempt_id=attempt.attempt_id,
                        attempt=attempt,
                        referenced_observations=_referenced_observations(
                            attempt, observations_by_id
                        ),
                        reasons=tuple(reasons),
                    )
                )

        content = AuthenticatedStructuredCharacteristicArtifactContent(
            artifact_id=artifact_id,
            request_id=request.request_id,
            accepted_objective=request.accepted_objective,
            accepted_objective_sha256=request.accepted_objective_sha256,
            characteristic_value_schema_id=request.characteristic_value_schema_id,
            characteristic_value_schema_version=request.characteristic_value_schema_version,
            authentication_policy_id=request.authentication_policy_id,
            authentication_policy_version=request.authentication_policy_version,
            authentication_rule_set=request.authentication_rule_set,
            authentication_rule_set_sha256=request.authentication_rule_set_sha256,
            source_observations=request.observations,
            authentication_attempts=request.attempts,
            authenticated_characteristics=tuple(authenticated),
            withheld_authentication_attempts=tuple(withheld),
            summary=AuthenticationSummary(
                attempt_count=len(request.attempts),
                authenticated_count=len(authenticated),
                withheld_count=len(withheld),
            ),
        )
        return AuthenticatedStructuredCharacteristicArtifact(
            content=content,
            artifact_content_sha256=_sha256(_canonical_model_bytes(content)),
        )

    @staticmethod
    def _authenticate_confirmation(
        attempt: ExactConfirmationAttempt,
        observations_by_id: dict[str, AuthenticationSourceObservation],
    ) -> tuple[
        AuthenticatedStructuredCharacteristic | None,
        list[AuthenticationReason],
    ]:
        rules_by_id = {
            rule.rule_id: rule for rule in APPROVED_AUTHENTICATION_RULE_SET.rules
        }
        reasons = [
            _reason(code, field_path)
            for code, field_path in authentication_failure_specs(
                attempt, observations_by_id, rules_by_id
            )
        ]
        definition = GOVERNED_CHARACTERISTIC_BY_KEY.get(
            (attempt.proposal.role, attempt.proposal.characteristic_id)
        )
        observation = observations_by_id.get(attempt.confirmation_evidence_id)
        if reasons:
            return None, reasons
        assert definition is not None
        assert observation is not None
        return (
            AuthenticatedStructuredCharacteristic(
                authenticated_characteristic_id=attempt.attempt_id,
                attempt_id=attempt.attempt_id,
                role=attempt.proposal.role,
                characteristic_id=attempt.proposal.characteristic_id,
                canonical_value_json=attempt.proposal.canonical_value_json,
                source_observations=(observation,),
                authentication_method=AuthenticationMethod.EXACT_USER_CONFIRMATION,
                lineage=ExactConfirmationLineage(
                    confirmation_evidence_id=observation.evidence_id
                ),
            ),
            [],
        )

    @staticmethod
    def _authenticate_derivation(
        attempt: VersionedDerivationAttempt,
        observations_by_id: dict[str, AuthenticationSourceObservation],
        rules_by_id: dict[str, AuthenticationRule],
    ) -> tuple[
        AuthenticatedStructuredCharacteristic | None,
        list[AuthenticationReason],
    ]:
        reasons = [
            _reason(code, field_path)
            for code, field_path in authentication_failure_specs(
                attempt, observations_by_id, rules_by_id
            )
        ]
        rule = rules_by_id.get(attempt.rule_id)
        referenced = _referenced_observations(attempt, observations_by_id)
        if reasons:
            return None, reasons
        assert rule is not None
        return (
            AuthenticatedStructuredCharacteristic(
                authenticated_characteristic_id=attempt.attempt_id,
                attempt_id=attempt.attempt_id,
                role=rule.output.role,
                characteristic_id=rule.output.characteristic_id,
                canonical_value_json=rule.output.canonical_value_json,
                source_observations=referenced,
                authentication_method=AuthenticationMethod.VERSIONED_DERIVATION,
                lineage=DerivationLineage(
                    rule_set_sha256=APPROVED_AUTHENTICATION_RULE_SET_SHA256,
                    rule_id=rule.rule_id,
                    rule_version=rule.rule_version,
                    input_evidence_ids=attempt.input_evidence_ids,
                ),
            ),
            [],
        )
