"""Intake Quality Gate — deterministic, explicit, testable.

Decides whether a raw ``company_label`` is good enough to *begin* reliable
discovery. This is code, never an LLM verdict (docs/BUILD-PLAN.md M0):
``CLARIFICATION_REQUIRED`` must never trigger discovery or create a counterparty.

The rules are intentionally simple and inspectable. They are conservative: when
in doubt we ask for clarification rather than manufacturing an entity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..models.enums import IntakeState

# Placeholder tokens that carry no identifying information on their own.
PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
    {"tbd", "tba", "tbc", "na", "n/a", "none", "unknown", "unnamed", "pending", "?", "??", "???"}
)

# Generic industry/descriptor words that are not a distinctive legal name.
GENERIC_DESCRIPTORS: frozenset[str] = frozenset(
    {
        "refinery",
        "company",
        "trader",
        "trading",
        "supplier",
        "buyer",
        "seller",
        "corporation",
        "group",
        "holdings",
        "energy",
        "oil",
        "gas",
        "petroleum",
        "logistics",
    }
)

# Country/qualifier words that do not make a generic descriptor distinctive.
_QUALIFIERS: frozenset[str] = frozenset(
    {"us", "usa", "uk", "eu", "uae", "international", "global", "national", "the", "a", "an"}
)

_WORD_RE = re.compile(r"[a-z0-9&]+")


@dataclass(frozen=True)
class IntakeAssessment:
    state: IntakeState
    reason: str | None  # human-readable reason when CLARIFICATION_REQUIRED, else None


def normalise_label(label: str) -> str:
    """Lower-case, collapse whitespace. Non-destructive to the stored raw label."""
    return re.sub(r"\s+", " ", label.strip().lower())


def _tokens(normalised: str) -> list[str]:
    return _WORD_RE.findall(normalised)


def assess_intake(company_label: str, contact_label: str) -> IntakeAssessment:
    """Return SUFFICIENT_FOR_DISCOVERY or CLARIFICATION_REQUIRED with a reason.

    ``contact_label`` is accepted for symmetry/future use; company resolvability
    is what gates discovery in Phase 1.
    """
    norm = normalise_label(company_label)

    if not norm:
        return IntakeAssessment(
            IntakeState.CLARIFICATION_REQUIRED,
            "No company label was supplied.",
        )

    # Whole label is a placeholder token (e.g. "TBD", "??").
    if norm in PLACEHOLDER_TOKENS:
        return IntakeAssessment(
            IntakeState.CLARIFICATION_REQUIRED,
            "The company label is a placeholder and does not identify a company.",
        )

    tokens = _tokens(norm)
    if not tokens:
        return IntakeAssessment(
            IntakeState.CLARIFICATION_REQUIRED,
            "The company label contains no usable characters.",
        )

    # Any placeholder token present anywhere disqualifies (e.g. "?? Halcyon" stays,
    # but "?? unknown" does not — handled by the distinctive-name check below).
    meaningful = [t for t in tokens if t not in PLACEHOLDER_TOKENS]
    if not meaningful:
        return IntakeAssessment(
            IntakeState.CLARIFICATION_REQUIRED,
            "The company label is only placeholder text.",
        )

    # A distinctive name = a token that is neither a generic descriptor nor a
    # qualifier/country word. Generic descriptors alone ("Unnamed Refinery",
    # "Unnamed Refinery", "Trading Company") are not a resolvable legal name.
    distinctive = [t for t in meaningful if t not in GENERIC_DESCRIPTORS and t not in _QUALIFIERS]
    if not distinctive:
        return IntakeAssessment(
            IntakeState.CLARIFICATION_REQUIRED,
            "The company label is a generic descriptor without a distinctive name.",
        )

    # A single very short distinctive token (< 3 chars) is too weak to resolve.
    if all(len(t) < 3 for t in distinctive):
        return IntakeAssessment(
            IntakeState.CLARIFICATION_REQUIRED,
            "The company label is too short to identify a company reliably.",
        )

    return IntakeAssessment(IntakeState.SUFFICIENT_FOR_DISCOVERY, None)
