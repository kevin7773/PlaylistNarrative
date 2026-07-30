from __future__ import annotations

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.journey import (
    ActiveFocusRequest,
    EnergyLevel,
    JourneyPlanner,
)


def test_default_active_focus_plan_is_deterministic_and_complete() -> None:
    request = ActiveFocusRequest()
    planner = JourneyPlanner()

    first = planner.plan_active_focus(request)
    second = planner.plan_active_focus(request)

    assert first == second
    assert first.context == "Active Focus"
    assert [phase.name for phase in first.phases] == [
        "Settle In",
        "Sustained Focus",
        "Controlled Landing",
    ]
    assert [phase.duration_minutes for phase in first.phases] == [14, 62, 14]
    assert sum(phase.duration_minutes for phase in first.phases) == 90


@pytest.mark.parametrize("duration", [30, 31, 90, 239, 240])
def test_phase_rounding_always_preserves_requested_duration(duration: int) -> None:
    plan = JourneyPlanner().plan_active_focus(
        ActiveFocusRequest(duration_minutes=duration)
    )
    assert sum(phase.duration_minutes for phase in plan.phases) == duration
    assert all(phase.duration_minutes > 0 for phase in plan.phases)


def test_discovery_budget_and_energy_endpoints_are_preserved() -> None:
    plan = JourneyPlanner().plan_active_focus(
        ActiveFocusRequest(
            discovery_percent=35,
            starting_energy=EnergyLevel.LOW,
            ending_energy=EnergyLevel.LOW,
        )
    )
    assert plan.phases[0].start_energy is EnergyLevel.LOW
    assert plan.phases[-1].end_energy is EnergyLevel.LOW
    for phase in plan.phases:
        assert phase.familiarity.discovery_percent == 35
        assert phase.familiarity.familiar_percent == 65


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_minutes", 29),
        ("duration_minutes", 241),
        ("discovery_percent", -1),
        ("discovery_percent", 51),
    ],
)
def test_request_rejects_out_of_bounds_values(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        ActiveFocusRequest(**{field: value})
