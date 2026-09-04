"""Intake Quality Gate — deterministic, explicit rules (no DB needed)."""

from __future__ import annotations

import pytest

from arie_sentinel.intake.gate import assess_intake
from arie_sentinel.models.enums import IntakeState


@pytest.mark.parametrize(
    "company",
    ["TBD", "TBA", "??", "n/a", "Unnamed Refinery", "A Trading Company", "Refinery", "the company"],
)
def test_insufficient_labels_require_clarification(company: str) -> None:
    result = assess_intake(company, "Amara")
    assert result.state is IntakeState.CLARIFICATION_REQUIRED
    assert result.reason  # a human-readable reason is always provided


@pytest.mark.parametrize(
    "company",
    ["Vantar - Castellan", "Castellan Trading", "Vantar Energy Trading", "?? Halcyon Oil"],
)
def test_sufficient_labels_pass(company: str) -> None:
    result = assess_intake(company, "Jordan Rivera")
    assert result.state is IntakeState.SUFFICIENT_FOR_DISCOVERY
    assert result.reason is None


def test_gate_is_deterministic() -> None:
    a = assess_intake("Vantar - Castellan", "Jordan Rivera")
    b = assess_intake("Vantar - Castellan", "Jordan Rivera")
    assert a == b
