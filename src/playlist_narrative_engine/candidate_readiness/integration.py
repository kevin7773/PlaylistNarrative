from __future__ import annotations

from playlist_narrative_engine.candidate_formation import CandidateFormer, CandidateFormationRequest
from playlist_narrative_engine.candidate_formation.request_assembler import FormationRequestAssembler, FormationRequestAssemblyInput
from playlist_narrative_engine.journey import JourneyPlanArtifact
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact

from .producer import active_focus_candidate_formation_policy
from .verifier import (
    ActiveFocusCandidateReadinessVerifier,
    VerifiedActiveFocusCandidateReadiness,
)


class GuardedActiveFocusCandidateFormationBridge:
    def __init__(
        self,
        verifier: ActiveFocusCandidateReadinessVerifier,
        *,
        accepted_objective: AcceptedObjectiveArtifact,
        journey_plan: JourneyPlanArtifact,
    ) -> None:
        if type(verifier) is not ActiveFocusCandidateReadinessVerifier:
            raise TypeError("the concrete governed readiness verifier is required")
        self._verifier = verifier
        self._accepted_objective = accepted_objective
        self._journey_plan = journey_plan

    def assemble(
        self,
        *,
        verified_readiness: VerifiedActiveFocusCandidateReadiness,
        request_id: str,
    ) -> CandidateFormationRequest:
        occurrence = self._verifier.recover_verified(verified_readiness)
        if (
            occurrence.accepted_objective is not self._accepted_objective
            or occurrence.journey_plan is not self._journey_plan
        ):
            raise ValueError("verified readiness does not match the bound objective and journey")
        return FormationRequestAssembler().assemble(FormationRequestAssemblyInput(
            request_id=request_id,
            accepted_objective=occurrence.accepted_objective,
            journey_plan=occurrence.journey_plan,
            acquisition=occurrence.acquisition_authority.source_neutral_acquisition_result,
            track_validation=occurrence.track_validation,
            taste_evidence=occurrence.local_taste_evidence,
            familiarity_evidence=occurrence.familiarity_evidence,
            track_feature_evidence=occurrence.track_feature_evidence,
            objective_context_evidence=occurrence.objective_context_evidence,
            policy=active_focus_candidate_formation_policy(),
        ))

    def form(
        self,
        *,
        verified_readiness: VerifiedActiveFocusCandidateReadiness,
        request_id: str,
    ):
        return CandidateFormer().form(
            self.assemble(
                verified_readiness=verified_readiness,
                request_id=request_id,
            )
        )
