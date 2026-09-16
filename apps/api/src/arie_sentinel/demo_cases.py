"""Management-demo case classification and non-evidentiary metadata."""

from __future__ import annotations

from .intake.gate import normalise_label

PUBLIC_VALIDATION_CASE = "PUBLIC_VALIDATION_CASE"
FICTIONAL_TEST_CASE = "FICTIONAL_TEST_CASE"

_PUBLIC_ALIASES = {"arie finance", "arie finance ltd"}
_FICTIONAL_ALIASES = {
    "vantar - castellan",
    "vantar energy trading",
    "castellan trading",
    "orion petro trading",
    "pacific energy procurement ltd",
    "atlas global fuels",
    "northstar petroleum trading",
    "meridian energy supplies ltd",
}


def demo_case_context(company_label: str) -> dict[str, str]:
    """Return display/context metadata only for explicitly supported demo cases."""
    normalized = normalise_label(company_label)
    if normalized in _PUBLIC_ALIASES:
        return {
            "demo_case_type": PUBLIC_VALIDATION_CASE,
            "website": "https://www.ariefinance.com",
        }
    if normalized in _FICTIONAL_ALIASES:
        return {"demo_case_type": FICTIONAL_TEST_CASE}
    return {}
