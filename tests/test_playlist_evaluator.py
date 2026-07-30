from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.evaluation import (
    EVALUATION_SCHEMA_VERSION,
    EvaluationDisposition,
    EvaluationIssueSeverity,
    EvaluationMetric,
    EvidenceSource,
    MetricApplicability,
    PlaylistJourneyEvaluator,
)
from playlist_narrative_engine.journey import (
    ActiveFocusRequest,
    JourneyPlanner,
)
from playlist_narrative_engine.sequencing import (
    ConstructionPolicy,
    ConstructionResult,
    ConstructionState,
    ConstructionStatus,
    ConstructionSummary,
    SequentialPlaylistConstructor,
    TrackCandidate,
    TrackScorer,
)


def candidate(track_id: str, **overrides: object) -> TrackCandidate:
    values: dict[str, object] = {
        "track_id": track_id,
        "title": f"Synthetic {track_id}",
        "artist_name": f"Artist {track_id}",
        "duration_seconds": 210,
        "energy": 0.65,
        "familiarity": 0.70,
        "preference": 0.85,
        "context_fit": 0.90,
        "instrumentalness": 0.70,
        "lyrical_distraction": 0.10,
        "groove": 0.80,
    }
    values.update(overrides)
    return TrackCandidate(**values)


@pytest.fixture
def journey_plan():
    return JourneyPlanner().plan_active_focus(ActiveFocusRequest())


@pytest.fixture
def policy():
    return ConstructionPolicy()


def construct(journey_plan, policy, pool, requested_count):
    return SequentialPlaylistConstructor(policy=policy).construct(
        journey_plan=journey_plan,
        candidate_pool=pool,
        state=ConstructionState(),
        requested_track_count=requested_count,
    )


def metric(report, code):
    return next(item for item in report.metrics if item.code == code)


def test_complete_result_has_separate_objective_and_quality_metrics(
    journey_plan,
    policy,
) -> None:
    result = construct(
        journey_plan,
        policy,
        tuple(candidate(f"track-{index}") for index in range(4)),
        4,
    )
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )

    assert report.disposition is EvaluationDisposition.COMPLETE_EVALUATED
    assert metric(report, "completion_fidelity").value == 1.0
    phase_metric = metric(report, "mean_phase_score")
    assert phase_metric.applicability is MetricApplicability.MEASURED
    assert phase_metric.evidence_source is EvidenceSource.STORED_SCORE_AGGREGATION
    assert phase_metric.denominator == 4
    assert phase_metric.sample_count == 4


def test_partial_result_keeps_prefix_quality_separate_from_attainment(
    journey_plan,
    policy,
) -> None:
    result = construct(
        journey_plan,
        policy,
        (candidate("a"), candidate("b")),
        4,
    )
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )

    assert report.disposition is EvaluationDisposition.PARTIAL_EVALUATED
    assert metric(report, "completion_fidelity").value == 0.5
    assert metric(report, "mean_phase_score").sample_count == 2
    assert metric(report, "mean_transition_score").sample_count == 1
    assert any(
        issue.code == "partial_objective_coverage"
        for issue in report.issues
    )


def test_infeasible_result_is_inconclusive_but_preserves_source_issue(
    journey_plan,
    policy,
) -> None:
    result = construct(journey_plan, policy, (), 3)
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )

    assert result.summary.status is ConstructionStatus.INFEASIBLE
    assert report.disposition is EvaluationDisposition.INCONCLUSIVE
    assert metric(report, "completion_fidelity").value == 0.0
    assert metric(
        report, "mean_transition_score"
    ).applicability is MetricApplicability.NOT_APPLICABLE
    assert any(
        issue.code == "construction:candidate_pool_exhausted"
        for issue in report.issues
    )


def test_empty_complete_claim_is_observed_without_being_trusted(
    journey_plan,
    policy,
) -> None:
    empty = ConstructionResult(
        tracks=(),
        summary=ConstructionSummary(
            status=ConstructionStatus.COMPLETE,
            requested_track_count=1,
            achieved_track_count=0,
            total_duration_seconds=0,
            discovery_count=0,
            discovery_ratio=0.0,
            artist_counts=(),
            phase_track_counts=(),
            role_counts=(),
            rejection_counts=(),
        ),
        issues=(),
    )
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=empty,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    assert report.disposition is EvaluationDisposition.INCONCLUSIVE
    assert any(
        issue.code == "summary_completion_status_mismatch"
        for issue in report.issues
    )
    assert metric(
        report, "discovery_ratio"
    ).applicability is MetricApplicability.NOT_APPLICABLE
    assert metric(report, "discovery_ratio").value is None


def test_resumed_construction_result_is_evaluated_as_complete(
    journey_plan,
    policy,
) -> None:
    pool = tuple(candidate(f"track-{index}") for index in range(5))
    state = ConstructionState()
    constructor = SequentialPlaylistConstructor(policy=policy)
    constructor.construct(
        journey_plan=journey_plan,
        candidate_pool=pool,
        state=state,
        requested_track_count=2,
    )
    resumed = constructor.construct(
        journey_plan=journey_plan,
        candidate_pool=pool,
        state=state,
        requested_track_count=4,
    )
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=resumed,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    assert report.disposition is EvaluationDisposition.COMPLETE_EVALUATED
    assert metric(report, "completion_fidelity").numerator == 4
    assert metric(report, "completion_fidelity").denominator == 4


def test_transition_metric_excludes_opening_track(
    journey_plan,
    policy,
) -> None:
    result = construct(
        journey_plan,
        policy,
        tuple(candidate(f"track-{index}") for index in range(4)),
        4,
    )
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    transition = metric(report, "mean_transition_score")
    expected = sum(
        track.score_breakdown.transition_score for track in result.tracks[1:]
    )
    assert transition.numerator == pytest.approx(expected)
    assert transition.denominator == 3
    assert transition.sample_count == 3
    assert transition.evidence_positions == (2, 3, 4)
    assert len(report.transition_series) == 3


def test_evaluator_consumes_stored_scores_without_rescoring(
    journey_plan,
    policy,
    monkeypatch,
) -> None:
    result = construct(
        journey_plan,
        policy,
        (candidate("a"), candidate("b")),
        2,
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("TrackScorer must not be called by evaluation")

    monkeypatch.setattr(TrackScorer, "score", fail_if_called)
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    expected = sum(
        track.score_breakdown.context_score for track in result.tracks
    )
    assert metric(report, "mean_context_score").numerator == pytest.approx(
        expected
    )


def test_unsupported_measurements_are_explicitly_unavailable(
    journey_plan,
    policy,
) -> None:
    result = construct(journey_plan, policy, (candidate("a"),), 1)
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    for code in (
        "album_repetition_fidelity",
        "vocal_salience",
        "emotional_continuity",
        "narrative_continuity",
        "phase_energy_contour_fidelity",
        "anchor_spacing_fidelity",
    ):
        unavailable = metric(report, code)
        assert unavailable.applicability is MetricApplicability.UNAVAILABLE
        assert unavailable.value is None
        assert unavailable.evidence_source is EvidenceSource.UNSUPPORTED
    assert metric(
        report, "mean_absolute_energy_delta"
    ).applicability is MetricApplicability.NOT_APPLICABLE


def test_evaluation_is_deterministic_and_byte_identical(
    journey_plan,
    policy,
) -> None:
    result = construct(
        journey_plan,
        policy,
        tuple(candidate(f"track-{index}") for index in range(4)),
        4,
    )
    evaluator = PlaylistJourneyEvaluator()
    first = evaluator.evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    second = evaluator.evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    assert first == second
    assert first.model_dump_json().encode() == second.model_dump_json().encode()


def test_public_enum_wire_values_are_explicit() -> None:
    assert [item.value for item in EvaluationDisposition] == [
        "complete_evaluated",
        "partial_evaluated",
        "inconclusive",
    ]
    assert [item.value for item in MetricApplicability] == [
        "measured",
        "not_applicable",
        "unavailable",
    ]
    assert [item.value for item in EvidenceSource] == [
        "direct_fact",
        "stored_score_aggregation",
        "objective_comparison",
        "unsupported",
    ]
    assert [item.value for item in EvaluationIssueSeverity] == [
        "info",
        "warning",
        "error",
    ]


def test_report_json_field_order_and_schema_version_are_stable(
    journey_plan,
    policy,
) -> None:
    result = construct(journey_plan, policy, (candidate("only"),), 1)
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    payload = json.loads(report.model_dump_json())
    assert EVALUATION_SCHEMA_VERSION == "1.0"
    assert list(payload) == [
        "schema_version",
        "disposition",
        "construction_status",
        "metrics",
        "phase_diagnostics",
        "transition_series",
        "energy_series",
        "lyrical_distraction_series",
        "discovery_positions",
        "role_positions",
        "issues",
    ]
    assert payload["schema_version"] == "1.0"
    assert payload["disposition"] == "complete_evaluated"
    assert payload["construction_status"] == "complete"
    assert "schema_version" in type(report).model_json_schema()["required"]
    assert list(payload["metrics"][0]) == [
        "code",
        "applicability",
        "value",
        "unit",
        "numerator",
        "denominator",
        "denominator_description",
        "sample_count",
        "target",
        "evidence_source",
        "explanation",
        "evidence_positions",
        "evidence_phases",
    ]


def test_metric_applicability_semantics_are_schema_enforced() -> None:
    common = {
        "code": "example",
        "unit": "ratio",
        "denominator_description": "example denominator",
        "explanation": "Example metric.",
    }
    with pytest.raises(ValidationError, match="require a value"):
        EvaluationMetric(
            **common,
            applicability=MetricApplicability.MEASURED,
            sample_count=1,
            evidence_source=EvidenceSource.DIRECT_FACT,
        )
    with pytest.raises(ValidationError, match="cannot contain"):
        EvaluationMetric(
            **common,
            applicability=MetricApplicability.NOT_APPLICABLE,
            value=0.0,
            sample_count=0,
            evidence_source=EvidenceSource.DIRECT_FACT,
        )
    with pytest.raises(ValidationError, match="unsupported evidence"):
        EvaluationMetric(
            **common,
            applicability=MetricApplicability.UNAVAILABLE,
            sample_count=0,
            evidence_source=EvidenceSource.DIRECT_FACT,
        )


def test_unknown_public_schema_fields_are_rejected(
    journey_plan,
    policy,
) -> None:
    result = construct(journey_plan, policy, (candidate("only"),), 1)
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    payload = report.model_dump()
    payload["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        type(report).model_validate(payload)
    payload = report.model_dump()
    del payload["schema_version"]
    with pytest.raises(ValidationError, match="Field required"):
        type(report).model_validate(payload)


def test_evaluation_mutates_neither_inputs_nor_evaluator_state(
    journey_plan,
    policy,
) -> None:
    result = construct(
        journey_plan,
        policy,
        (candidate("a"), candidate("b")),
        2,
    )
    result_snapshot = repr(result)
    plan_snapshot = journey_plan.model_dump_json()
    policy_snapshot = repr(policy)
    evaluator = PlaylistJourneyEvaluator()

    report = evaluator.evaluate(
        construction_result=result,
        journey_plan=journey_plan,
        construction_policy=policy,
    )

    assert repr(result) == result_snapshot
    assert journey_plan.model_dump_json() == plan_snapshot
    assert repr(policy) == policy_snapshot
    assert not hasattr(evaluator, "__dict__")
    with pytest.raises(ValidationError):
        report.disposition = EvaluationDisposition.INCONCLUSIVE


def test_pool_order_independent_construction_has_identical_evaluation(
    journey_plan,
    policy,
) -> None:
    pool = tuple(candidate(f"track-{index}") for index in range(5))
    forward = construct(journey_plan, policy, pool, 4)
    reverse = construct(journey_plan, policy, reversed(pool), 4)
    evaluator = PlaylistJourneyEvaluator()
    forward_report = evaluator.evaluate(
        construction_result=forward,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    reverse_report = evaluator.evaluate(
        construction_result=reverse,
        journey_plan=journey_plan,
        construction_policy=policy,
    )
    assert forward_report == reverse_report
    assert (
        forward_report.model_dump_json()
        == reverse_report.model_dump_json()
    )
