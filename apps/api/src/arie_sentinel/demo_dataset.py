"""Single source of truth for the non-live management-demo dataset.

Every supported demo identity is defined exactly once here and consumed by:
- ``demo_cases.demo_case_context`` (case-type / display metadata),
- ``providers.fixtures`` (deterministic corporate discovery),
- deployment seeding.

Matching is by EXACT normalised alias only. There is no token, substring, or
fuzzy matching: an unsupported near-match (e.g. "Meridian Energy" vs the
supported "Meridian Energy Supplies Ltd") must NOT resolve into fixture data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .intake.gate import normalise_label
from .providers.base import CandidateEntity

PUBLIC_VALIDATION_CASE = "PUBLIC_VALIDATION_CASE"
FICTIONAL_TEST_CASE = "FICTIONAL_TEST_CASE"

# Truthful curation date for the curated demo summaries. This is the date the
# fixture content was prepared for the management demo, NOT a live retrieval
# time (see ``providers.fixtures`` and ``services.investigations`` provenance).
CURATION_DATE = "2026-09-16T00:00:00Z"

# --- Fictional counterparty fixtures -------------------------------------------------

_VANTAR_FZE = CandidateEntity(
    legal_name="Vantar Energy Trading FZE",
    jurisdiction="AE",
    registry_class="uae_free_zone",
    registry_id="12345",
    status="Active",
    incorporation_date="2025-02-14",
    match_basis="registration number + jurisdiction match",
)
_VANTAR_LTD = CandidateEntity(
    legal_name="Vantar Energy Trading Ltd",
    jurisdiction="GB",
    registry_class="companies_house",
    registry_id="09876543",
    status="Active",
    match_basis="name + jurisdiction (registry number differs)",
)
_VANTAR_LLC = CandidateEntity(
    legal_name="Vantar Energy Trading LLC",
    jurisdiction="US-DE",
    registry_class="us_state_registry",
    registry_id="DE-LLC-2025",
    status="Active",
    match_basis="name only — weak",
)
_CASTELLAN = CandidateEntity(
    legal_name="Castellan Trading FZE",
    jurisdiction="AE",
    registry_class="uae_free_zone",
    registry_id="22345",
    status="Active",
    incorporation_date="2024-06-01",
    match_basis="registration number + jurisdiction match",
)

# Fictional commodities-counterparty scenarios used by the management demo.
_ORION_AE = CandidateEntity(
    legal_name="Orion Petro Trading FZE",
    jurisdiction="AE",
    registry_class="uae_free_zone",
    registry_id="OPT-41001",
    status="Active",
    incorporation_date="2019-04-18",
    registered_address="Demo Trade Centre, Dubai, AE",
    match_basis="name + jurisdiction; analyst selection required",
)
_ORION_GB = CandidateEntity(
    legal_name="Orion Petro Trading Ltd",
    jurisdiction="GB",
    registry_class="companies_house",
    registry_id="14200101",
    status="Active",
    incorporation_date="2021-09-03",
    registered_address="10 Fictional Wharf, London, GB",
    match_basis="name match; different jurisdiction and registry identifier",
)
_ORION_SG = CandidateEntity(
    legal_name="Orion Petro Trading Pte. Ltd.",
    jurisdiction="SG",
    registry_class="acra",
    registry_id="202200101Z",
    status="Active",
    incorporation_date="2022-01-10",
    registered_address="1 Example Quay, Singapore",
    match_basis="name match; different jurisdiction and registry identifier",
)
_PACIFIC = CandidateEntity(
    legal_name="Pacific Energy Procurement Ltd",
    jurisdiction="SG",
    registry_class="acra",
    registry_id="201800202P",
    status="Active",
    incorporation_date="2018-06-12",
    registered_address="20 Demo Harbour Road, Singapore",
    match_basis="exact legal name + jurisdiction + registry identifier",
)
_ATLAS = CandidateEntity(
    legal_name="Atlas Global Fuels FZE",
    jurisdiction="AE",
    registry_class="uae_free_zone",
    registry_id="AGF-52003",
    status="Active",
    incorporation_date="2020-11-08",
    registered_address="5 Fictional Free Zone, Fujairah, AE",
    match_basis="exact legal name + jurisdiction + registry identifier",
)
_NORTHSTAR = CandidateEntity(
    legal_name="Northstar Petroleum Trading Ltd",
    jurisdiction="GB",
    registry_class="companies_house",
    registry_id="15100404",
    status="Active",
    incorporation_date="2023-02-21",
    registered_address="24 Example Street, London, GB",
    match_basis="exact legal name + jurisdiction + registry identifier",
)
_MERIDIAN = CandidateEntity(
    legal_name="Meridian Energy Supplies Ltd",
    jurisdiction="GB",
    registry_class="companies_house",
    registry_id="13700505",
    status="Active",
    incorporation_date="2020-07-15",
    registered_address="8 Test Square, London, GB",
    match_basis="exact legal name + jurisdiction + registry identifier",
)

_ZENITH = CandidateEntity(
    legal_name="Zenith Global Traders Ltd",
    jurisdiction="GB",
    registry_class="companies_house",
    registry_id="14750888",
    status="Active",
    incorporation_date="2023-05-09",
    registered_address="3 Example Court, Manchester, GB",
    match_basis="exact legal name + jurisdiction + registry identifier",
)

# --- Public validation record --------------------------------------------------------

_ARIE_FINANCE = CandidateEntity(
    legal_name="ARIE Finance Ltd",
    jurisdiction="MU",
    registry_class="mauritius_corporate_and_business_registration",
    registry_id="C221997",
    status="Current status not established from cited source",
    alternative_names=("ARIE Finance",),
    source_ref=(
        "https://companies.govmu.org/Communique/"
        "List%20of%20Companies%20with%20Registration%20Fees%20Due%202026%20"
        "as%20at%2016%20December%202025.pdf"
    ),
    retrieved_at=CURATION_DATE,
    match_basis=(
        "exact legal name + Mauritius company registration identifier in an official public "
        "corporate-registry publication"
    ),
)


@dataclass(frozen=True)
class DemoCase:
    """One deliberately-approved demo identity and its fixture candidates."""

    case_type: str
    candidates: tuple[CandidateEntity, ...]
    context: dict[str, str] = field(default_factory=dict)


# The ONLY supported demo identities, keyed by exact normalised alias.
# Adding an entry here is the single, deliberate act of approving a demo case;
# nothing else grants fixture data to a submitted name.
DEMO_CASES: dict[str, DemoCase] = {
    "vantar - castellan": DemoCase(FICTIONAL_TEST_CASE, (_VANTAR_FZE,)),
    "vantar energy trading": DemoCase(FICTIONAL_TEST_CASE, (_VANTAR_FZE, _VANTAR_LTD, _VANTAR_LLC)),
    "castellan trading": DemoCase(FICTIONAL_TEST_CASE, (_CASTELLAN,)),
    "orion petro trading": DemoCase(FICTIONAL_TEST_CASE, (_ORION_AE, _ORION_GB, _ORION_SG)),
    "pacific energy procurement ltd": DemoCase(FICTIONAL_TEST_CASE, (_PACIFIC,)),
    "atlas global fuels": DemoCase(FICTIONAL_TEST_CASE, (_ATLAS,)),
    "northstar petroleum trading": DemoCase(FICTIONAL_TEST_CASE, (_NORTHSTAR,)),
    "meridian energy supplies ltd": DemoCase(FICTIONAL_TEST_CASE, (_MERIDIAN,)),
    "zenith global traders ltd": DemoCase(
        FICTIONAL_TEST_CASE,
        (_ZENITH,),
        {"website": "https://zenith-global.example.test"},
    ),
    "arie finance": DemoCase(
        PUBLIC_VALIDATION_CASE, (_ARIE_FINANCE,), {"website": "https://www.ariefinance.com"}
    ),
    "arie finance ltd": DemoCase(
        PUBLIC_VALIDATION_CASE, (_ARIE_FINANCE,), {"website": "https://www.ariefinance.com"}
    ),
}


def lookup_demo_case(company_label: str) -> DemoCase | None:
    """Return the DemoCase for an EXACT supported alias, else None."""
    return DEMO_CASES.get(normalise_label(company_label))


# --- Management-demo seed selection --------------------------------------------------
#
# Which supported cases the deployment seeder preloads, and their canonical labels,
# originate HERE — not in a separate list inside the seeder — so the seeder and the
# canonical dataset cannot drift (B1). Each label MUST be a supported alias in
# DEMO_CASES; iter_seed_cases() enforces that. Adding a seedable demo company is done
# by adding it to DEMO_CASES and listing its canonical label here.
SEED_CASE_LABELS: tuple[str, ...] = (
    "Orion Petro Trading",
    "Pacific Energy Procurement Ltd",
    "Atlas Global Fuels",
    "Northstar Petroleum Trading",
    "Meridian Energy Supplies Ltd",
    "Zenith Global Traders Ltd",
    "ARIE Finance",
)

# Optional demo contact person per seed case. Contacts are scenario INPUTS, not
# corporate-identity aliases, so they are kept as separate metadata keyed by the
# canonical seed label. A seed case with no entry is preloaded company-only, so a
# new seedable company never requires editing this mapping.
SEED_CONTACTS: dict[str, str] = {
    "Orion Petro Trading": "Karim Mansour",
    "Pacific Energy Procurement Ltd": "Daniel Kim",
    "Atlas Global Fuels": "Michael Grant",
    "Northstar Petroleum Trading": "Victor Lane",
    "Meridian Energy Supplies Ltd": "Amira Hassan",
    "Zenith Global Traders Ltd": "Robert Vance",
}

# Optional subject claims per seed case, tested against discovered evidence by the
# contradiction engine. Non-evidentiary intake inputs, kept as separate metadata.
SEED_CLAIMS: dict[str, dict[str, object]] = {
    "Zenith Global Traders Ltd": {
        "operating_since_year": 2008,
        "registration_number": "GB-OLD-0001",
        "jurisdiction": "GB",
        "website": "https://zenith-global.example.test",
        "contact_email": "robert@zenith-holdings-different.example",
        "licence": "FCA authorised",
    },
}


def iter_seed_cases() -> list[tuple[str, str, str]]:
    """Return ``(company_label, contact_label, case_type)`` per management-demo seed case.

    Company identity and case type come from the canonical ``DEMO_CASES``; the contact
    is optional scenario metadata. Raises ``RuntimeError`` if a seed label is not a
    supported case, so the seeder can never silently drift from the canonical dataset.
    """
    cases: list[tuple[str, str, str]] = []
    for label in SEED_CASE_LABELS:
        case = lookup_demo_case(label)
        if case is None:
            raise RuntimeError(
                f"Seed label {label!r} is not a supported demo case in DEMO_CASES; "
                "add it to the canonical dataset instead of maintaining a separate list."
            )
        cases.append((label, SEED_CONTACTS.get(label, ""), case.case_type))
    return cases
