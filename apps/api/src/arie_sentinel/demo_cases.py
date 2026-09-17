"""Management-demo case classification and non-evidentiary metadata.

Thin adapter over ``demo_dataset`` (the single source of truth). Case type and
context are derived from the same exact-alias map that drives fixture discovery,
so the two can never drift.
"""

from __future__ import annotations

from .demo_dataset import (
    FICTIONAL_TEST_CASE,
    PUBLIC_VALIDATION_CASE,
    lookup_demo_case,
)

__all__ = ["FICTIONAL_TEST_CASE", "PUBLIC_VALIDATION_CASE", "demo_case_context"]


def demo_case_context(company_label: str) -> dict[str, str]:
    """Return display/context metadata only for explicitly supported demo cases."""
    case = lookup_demo_case(company_label)
    if case is None:
        return {}
    context: dict[str, str] = {"demo_case_type": case.case_type}
    context.update(case.context)
    return context
