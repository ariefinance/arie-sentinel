"""Investigation Board: the primary at-a-glance view of an investigation.

Each row states, in explicit evidence language, what Sentinel checked, what it
established, what it could not establish, and whether analyst attention is needed.
Every row is derived from stored records and carries the source ids behind it.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.core import EntityCandidate, Identifier, Investigation
from ..models.enums import (
    AuditAction,
    CompanyIdentityStatus,
    CompletenessState,
    EvidenceState,
    FindingType,
    ReviewStatus,
    ScreeningState,
    SourceClass,
)
from ..models.evidence import Evidence, Finding, ScreeningResult, Source
from ..models.ops import AuditEvent
from .contradictions import REGULATOR_LICENCE_LICENSE_CLASS

_CONTRADICTION_TYPES = {
    FindingType.CONTRADICTION,
    FindingType.INCONSISTENCY,
    FindingType.ANOMALY,
    FindingType.UNVERIFIED_CLAIM,
}


@dataclass(frozen=True)
class BoardRow:
    key: str
    label: str
    state: str  # an EvidenceState or ScreeningState token — never colour alone
    detail: str
    action_required: bool = False
    source_ids: list[uuid.UUID] = field(default_factory=list)


def _resolved_candidate(session: Session, investigation: Investigation) -> EntityCandidate | None:
    event = session.scalar(
        select(AuditEvent)
        .where(
            AuditEvent.investigation_id == investigation.investigation_id,
            AuditEvent.action == AuditAction.RESOLVE_IDENTITY,
        )
        .order_by(AuditEvent.created_at.asc())
    )
    candidate_id = (event.payload or {}).get("candidate_id") if event else None
    if not isinstance(candidate_id, str):
        return None
    try:
        return session.get(EntityCandidate, uuid.UUID(candidate_id))
    except (ValueError, TypeError):
        return None


def build_board(session: Session, investigation: Investigation) -> list[BoardRow]:
    inv = investigation
    counterparty = inv.counterparty
    resolved = _resolved_candidate(session, inv)
    sources = list(
        session.scalars(select(Source).where(Source.investigation_id == inv.investigation_id))
    )
    findings = list(
        session.scalars(select(Finding).where(Finding.investigation_id == inv.investigation_id))
    )
    screening = list(
        session.scalars(
            select(ScreeningResult).where(ScreeningResult.investigation_id == inv.investigation_id)
        )
    )
    officer_evidence = list(
        session.execute(
            select(Evidence, Source)
            .join(Source, Evidence.source_id == Source.source_id)
            .where(
                Source.investigation_id == inv.investigation_id,
                Source.source_class == SourceClass.CORPORATE_REGISTRY,
            )
        )
    )
    officer_count = sum(1 for e, _ in officer_evidence if (e.observed_value or {}).get("position"))

    def source_ids(predicate: Callable[[Source], bool]) -> list[uuid.UUID]:
        return [s.source_id for s in sources if predicate(s)]

    # The resolved registry record backs identity/status/registration/incorporation/
    # address; the GLEIF record backs the LEI row. Rows carry the real source ids so
    # drill-down is row-specific; a claim with no independent source gets none.
    registry_source_ids = source_ids(
        lambda s: (
            s.source_class is SourceClass.CORPORATE_REGISTRY
            and s.title.startswith("Registry candidate")
        )
    )
    gleif_source_ids = source_ids(
        lambda s: (
            s.source_class is SourceClass.CORPORATE_REGISTRY
            and s.title.startswith("GLEIF LEI record")
        )
    )

    rows: list[BoardRow] = []

    # Legal identity
    if inv.company_identity_status is CompanyIdentityStatus.CONFIRMED:
        identity_state, identity_detail = (
            EvidenceState.CONFIRMED,
            (counterparty.legal_name if counterparty else "Confirmed"),
        )
        identity_action = False
    elif inv.company_identity_status is CompanyIdentityStatus.AMBIGUOUS:
        identity_state = EvidenceState.REPORTED
        identity_detail = f"{len(inv.entity_candidates)} candidates — analyst resolution required"
        identity_action = True
    elif inv.investigation_state.value == "SOURCE_UNAVAILABLE":
        identity_state, identity_detail, identity_action = (
            EvidenceState.SOURCE_UNAVAILABLE,
            inv.clarification_reason or "Not available in the management-demo dataset",
            False,
        )
    else:
        identity_state, identity_detail, identity_action = (
            EvidenceState.UNVERIFIED,
            "Not established",
            False,
        )
    rows.append(
        BoardRow(
            "legal_identity",
            "Legal identity",
            identity_state.value,
            identity_detail,
            identity_action,
            source_ids(lambda s: s.source_class is SourceClass.CORPORATE_REGISTRY),
        )
    )

    # Corporate status
    status = counterparty.status if counterparty else None
    rows.append(
        BoardRow(
            "corporate_status",
            "Corporate status",
            EvidenceState.REPORTED.value if status else EvidenceState.NOT_ASSESSED.value,
            status or "Not established from cited source",
            source_ids=registry_source_ids if status else [],
        )
    )

    # Registration
    has_registration = bool(counterparty and counterparty.registry_id)
    rows.append(
        BoardRow(
            "registration",
            "Registration",
            EvidenceState.CONFIRMED.value if has_registration else EvidenceState.UNVERIFIED.value,
            counterparty.registry_id if counterparty and counterparty.registry_id else "Not found",
            source_ids=registry_source_ids if has_registration else [],
        )
    )

    # Incorporation
    inc = resolved.incorporation_date if resolved else None
    rows.append(
        BoardRow(
            "incorporation",
            "Incorporation",
            EvidenceState.REPORTED.value if inc else EvidenceState.NOT_ASSESSED.value,
            inc or "Not established",
            source_ids=registry_source_ids if inc else [],
        )
    )

    # Registered address
    address = resolved.registered_address if resolved else None
    rows.append(
        BoardRow(
            "registered_address",
            "Registered address",
            EvidenceState.REPORTED.value if address else EvidenceState.NOT_ASSESSED.value,
            address or "Not established",
            source_ids=registry_source_ids if address else [],
        )
    )

    # Directors / officers
    rows.append(
        BoardRow(
            "directors_officers",
            "Directors / officers",
            EvidenceState.CORROBORATED.value if officer_count else EvidenceState.NOT_ASSESSED.value,
            f"{officer_count} identified" if officer_count else "None identified",
            source_ids=source_ids(
                lambda s: (
                    s.source_class is SourceClass.CORPORATE_REGISTRY
                    and s.title.startswith("Registry officer")
                )
            ),
        )
    )

    # LEI
    lei = None
    if counterparty is not None:
        lei = session.scalar(
            select(Identifier.id_value).where(
                Identifier.counterparty_id == counterparty.counterparty_id,
                Identifier.id_type == "lei",
            )
        )
    rows.append(
        BoardRow(
            "lei",
            "LEI",
            EvidenceState.CONFIRMED.value if lei else EvidenceState.UNVERIFIED.value,
            lei or "No LEI located",
            source_ids=gleif_source_ids if lei else [],
        )
    )

    # Named contact + relationship
    contact = inv.contact_label.strip()
    if not contact:
        rows.append(
            BoardRow(
                "named_contact", "Named contact", EvidenceState.NOT_ASSESSED.value, "Not supplied"
            )
        )
    else:
        rel = inv.candidates[0].relationship_state if inv.candidates else None
        rel_map = {
            "VERIFIED": EvidenceState.CONFIRMED,
            "CORROBORATED": EvidenceState.CORROBORATED,
            "SELF_ASSERTED": EvidenceState.CLAIMED,
            "UNVERIFIED": EvidenceState.UNVERIFIED,
            "CONTRADICTED": EvidenceState.CONTRADICTED,
        }
        rel_state = (
            rel_map.get(rel.value, EvidenceState.UNVERIFIED) if rel else EvidenceState.UNVERIFIED
        )
        rows.append(
            BoardRow("named_contact", "Named contact", EvidenceState.REPORTED.value, contact)
        )
        rows.append(
            BoardRow(
                "contact_company",
                "Contact ↔ company",
                rel_state.value,
                inv.candidates[0].match_basis or "Relationship not established"
                if inv.candidates
                else "Relationship not established",
                action_required=rel_state in {EvidenceState.UNVERIFIED, EvidenceState.CONTRADICTED},
            )
        )

    # Domain / website
    domain_sources = source_ids(lambda s: s.source_class is SourceClass.DOMAIN_REGISTRATION)
    web_sources = source_ids(lambda s: s.source_class is SourceClass.WEB_PUBLIC)
    has_domain = bool(domain_sources) or bool((inv.case_context or {}).get("website"))
    rows.append(
        BoardRow(
            "domain_website",
            "Domain / website",
            EvidenceState.CORROBORATED.value
            if domain_sources
            else (EvidenceState.REPORTED.value if has_domain else EvidenceState.NOT_ASSESSED.value),
            "Established" if has_domain else "Not established",
            source_ids=domain_sources,
        )
    )

    # Regulatory footprint — only a regulator's verification of THIS entity's
    # licence counts; a corporate registry / generic government source does not.
    regulator_sources = source_ids(
        lambda s: (
            s.license_class == REGULATOR_LICENCE_LICENSE_CLASS
            and s.source_class is not SourceClass.CORPORATE_REGISTRY
        )
    )
    rows.append(
        BoardRow(
            "regulatory_footprint",
            "Regulatory footprint",
            EvidenceState.CORROBORATED.value
            if regulator_sources
            else EvidenceState.NOT_ASSESSED.value,
            f"{len(regulator_sources)} regulator record(s)"
            if regulator_sources
            else "No regulator verification retained",
            source_ids=regulator_sources,
        )
    )

    # Sanctions
    if inv.case_type == "PUBLIC_VALIDATION_CASE" and inv.screening_state is None:
        sanction_state, sanction_detail, sanction_action = (
            "LIVE_SCREENING_NOT_PERFORMED",
            "Live sanctions/PEP screening was not performed",
            False,
        )
    elif inv.screening_state is None:
        sanction_state, sanction_detail, sanction_action = (
            EvidenceState.SOURCE_UNAVAILABLE.value,
            "Screening source unavailable",
            False,
        )
    else:
        sanction_state = inv.screening_state.value
        sanction_action = inv.screening_state in {
            ScreeningState.POTENTIAL_MATCH,
            ScreeningState.MATCH_REQUIRES_REVIEW,
        }
        sanction_detail = {
            ScreeningState.NO_MATERIAL_MATCH: "No material match",
            ScreeningState.POTENTIAL_MATCH: "Potential match — analyst review required",
            ScreeningState.MATCH_REQUIRES_REVIEW: "Match requires review",
            ScreeningState.CONFIRMED_MATCH: "Confirmed match",
        }[inv.screening_state]
    rows.append(
        BoardRow(
            "sanctions",
            "Sanctions / PEP",
            sanction_state,
            sanction_detail,
            sanction_action,
            source_ids(lambda s: s.source_class is SourceClass.SANCTIONS_PEP_SCREENING),
        )
    )

    # Public footprint
    rows.append(
        BoardRow(
            "public_footprint",
            "Public footprint",
            EvidenceState.REPORTED.value if web_sources else EvidenceState.NOT_ASSESSED.value,
            f"{len(web_sources)} source(s)" if web_sources else "None established",
            source_ids=web_sources,
        )
    )

    # Contradictions
    open_contradictions = [
        f
        for f in findings
        if f.finding_type in _CONTRADICTION_TYPES and f.review_status is ReviewStatus.OPEN
    ]
    rows.append(
        BoardRow(
            "contradictions",
            "Contradictions",
            EvidenceState.CONTRADICTED.value
            if open_contradictions
            else EvidenceState.NOT_ASSESSED.value,
            f"{len(open_contradictions)} require review"
            if open_contradictions
            else "None established",
            action_required=bool(open_contradictions),
        )
    )

    # Evidence coverage — four distinct states. Zero collection errors is NOT the same
    # as confirmed coverage; coverage is descriptive (what was retained), never itself an
    # authoritative confirmation.
    running = inv.investigation_state.value in {"NOT_STARTED", "RUNNING"}
    unavailable = inv.completeness_state is CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
    if running:
        coverage_state, coverage_detail = (
            EvidenceState.NOT_ASSESSED.value,
            "Assessment in progress",
        )
    elif unavailable:
        coverage_state, coverage_detail = (
            EvidenceState.SOURCE_UNAVAILABLE.value,
            f"{len(sources)} source(s) — a material source was unavailable",
        )
    elif not sources:
        coverage_state, coverage_detail = (
            EvidenceState.UNVERIFIED.value,
            "Completed with no evidence retained",
        )
    else:
        coverage_state, coverage_detail = (
            EvidenceState.REPORTED.value,
            f"{len(sources)} source(s) collected",
        )
    rows.append(BoardRow("evidence_coverage", "Evidence coverage", coverage_state, coverage_detail))

    # Analyst actions
    open_findings = [f for f in findings if f.review_status is ReviewStatus.OPEN]
    pending_screening = [
        s
        for s in screening
        if s.analyst_disposition is None
        and s.state in {ScreeningState.POTENTIAL_MATCH, ScreeningState.MATCH_REQUIRES_REVIEW}
    ]
    outstanding = len(open_findings) + len(pending_screening) + (1 if identity_action else 0)
    rows.append(
        BoardRow(
            "analyst_actions",
            "Analyst actions",
            EvidenceState.NOT_ASSESSED.value,
            f"{outstanding} outstanding" if outstanding else "None outstanding",
            action_required=bool(outstanding),
        )
    )

    return rows
