"""Investigation lifecycle services.

Enforced invariants (also guarded structurally in the DB):
- raw labels are immutable and never overwritten by resolution;
- CLARIFICATION_REQUIRED launches NO discovery and creates NO counterparty;
- counterparties are deduped on authoritative identity_key, never on labels;
- ambiguous identity is never silently confirmed;
- every state change / creation is audited.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..intake.gate import assess_intake
from ..models.core import Counterparty, Investigation, PersonCandidate
from ..models.enums import (
    AuditAction,
    CompanyIdentityStatus,
    CompletenessState,
    IntakeState,
    InvestigationState,
    JobStatus,
    PersonEvidenceStatus,
    RelationshipState,
    ScreeningState,
)
from ..models.evidence import ScreeningResult
from ..models.ops import Job
from ..providers import ProviderUnavailable
from ..providers.fixtures import FixtureProviders, build_fixture_providers


def get_or_create_counterparty(session: Session, candidate: Any) -> tuple[Counterparty, bool]:
    """Return (counterparty, created). Dedup on identity_key; repeats link, not duplicate."""
    key = candidate.identity_key()
    existing = session.scalar(select(Counterparty).where(Counterparty.identity_key == key))
    if existing is not None:
        return existing, False
    cp = Counterparty(
        legal_name=candidate.legal_name,
        registry_class=candidate.registry_class,
        registry_id=candidate.registry_id,
        jurisdiction=candidate.jurisdiction,
        status=candidate.status,
        identity_key=key,
        first_resolved_at=datetime.now(UTC),
    )
    session.add(cp)
    session.flush()
    return cp, True


def _derive_person_candidates(
    session: Session, investigation: Investigation, providers: FixtureProviders
) -> None:
    """0..N PersonCandidates from the raw contact_label. Model proposes; never confirms."""
    fragments = providers.model.extract_person_candidates(investigation.contact_label)
    for frag in fragments:
        session.add(
            PersonCandidate(
                investigation_id=investigation.investigation_id,
                label_fragment=frag,
                person_evidence_status=None,  # unresolved until discovery/evidence
                relationship_state=RelationshipState.UNVERIFIED,
                created_by="system",
            )
        )


def create_investigation(
    session: Session,
    *,
    company_label: str,
    contact_label: str,
    actor: str,
    case_context: dict[str, Any] | None = None,
    import_batch_id: uuid.UUID | None = None,
    source_row_ref: str | None = None,
) -> Investigation:
    """Create one Investigation, run the intake gate, and enqueue discovery when sufficient."""
    assessment = assess_intake(company_label, contact_label)

    investigation = Investigation(
        company_label=company_label,
        contact_label=contact_label,
        intake_state=assessment.state,
        clarification_reason=assessment.reason,
        investigation_state=InvestigationState.NOT_STARTED,
        case_context=case_context,
        import_batch_id=import_batch_id,
        source_row_ref=source_row_ref,
        created_by=actor,
    )
    session.add(investigation)
    session.flush()

    record_audit(
        session,
        actor=actor,
        action=AuditAction.INVESTIGATION_CREATED,
        object_type="investigation",
        investigation_id=investigation.investigation_id,
        payload={"intake_state": assessment.state.value},
    )

    if assessment.state is IntakeState.CLARIFICATION_REQUIRED:
        # Hard stop: no discovery, no counterparty, no candidates.
        record_audit(
            session,
            actor="system",
            action=AuditAction.REQUEST_CLARIFICATION,
            object_type="investigation",
            investigation_id=investigation.investigation_id,
            rationale=assessment.reason,
        )
        return investigation

    # Sufficient for discovery: derive candidates and enqueue the discovery job.
    _derive_person_candidates(session, investigation, build_fixture_providers())
    session.add(
        Job(
            investigation_id=investigation.investigation_id,
            job_type="discovery",
            status=JobStatus.PENDING,
            payload={"investigation_id": str(investigation.investigation_id)},
        )
    )
    return investigation


def run_discovery(
    session: Session,
    investigation_id: uuid.UUID,
    providers: FixtureProviders | None = None,
) -> None:
    """Discovery job task: resolve identity via the registry provider and set state.

    Single candidate -> CONFIRMED (+dedup/create counterparty). Multiple -> AMBIGUOUS.
    None -> NOT_VERIFIED. Provider unavailable -> SOURCE_UNAVAILABLE. Never auto-confirms
    an ambiguous result.
    """
    providers = providers or build_fixture_providers()
    inv = session.get(Investigation, investigation_id)
    if inv is None:
        return
    # Guard: never run discovery for a clarification-required intake.
    if inv.intake_state is not IntakeState.SUFFICIENT_FOR_DISCOVERY:
        return

    inv.investigation_state = InvestigationState.RUNNING

    try:
        candidates = providers.registry.discover_candidates(inv.company_label)
    except ProviderUnavailable as exc:
        inv.investigation_state = InvestigationState.SOURCE_UNAVAILABLE
        inv.completeness_state = CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
        inv.company_identity_status = CompanyIdentityStatus.NOT_VERIFIED
        record_audit(
            session,
            actor="adapter:corporate_registry",
            action=AuditAction.STATE_CHANGE,
            object_type="investigation",
            investigation_id=inv.investigation_id,
            rationale=str(exc),
            payload={"investigation_state": inv.investigation_state.value},
        )
        return

    if len(candidates) == 0:
        inv.company_identity_status = CompanyIdentityStatus.NOT_VERIFIED
        inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
    elif len(candidates) == 1:
        candidate = candidates[0]
        cp, _created = get_or_create_counterparty(session, candidate)
        inv.counterparty_id = cp.counterparty_id
        inv.company_identity_status = CompanyIdentityStatus.CONFIRMED
        inv.company_match_basis = candidate.match_basis
        inv.completeness_state = CompletenessState.COMPLETE
        record_audit(
            session,
            actor="adapter:corporate_registry",
            action=AuditAction.LINK_COUNTERPARTY,
            object_type="counterparty",
            investigation_id=inv.investigation_id,
            target_ref=str(cp.counterparty_id),
            payload={"identity_key": cp.identity_key, "match_basis": candidate.match_basis},
        )
        _run_screening(session, inv, providers)
    else:
        # Ambiguous: NEVER silently pick one.
        inv.company_identity_status = CompanyIdentityStatus.AMBIGUOUS
        inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
        record_audit(
            session,
            actor="adapter:corporate_registry",
            action=AuditAction.STATE_CHANGE,
            object_type="investigation",
            investigation_id=inv.investigation_id,
            rationale="Multiple plausible legal entities; analyst disambiguation required.",
            payload={"candidate_count": len(candidates)},
        )

    inv.investigation_state = InvestigationState.COMPLETED


def _run_screening(session: Session, inv: Investigation, providers: FixtureProviders) -> None:
    """Record screening hits for the counterparty + contact candidates (adjudicated later)."""
    subjects = [inv.company_label]
    subjects += [c.label_fragment for c in inv.candidates]
    highest = ScreeningState.NO_MATERIAL_MATCH
    order = {
        ScreeningState.NO_MATERIAL_MATCH: 0,
        ScreeningState.POTENTIAL_MATCH: 1,
        ScreeningState.MATCH_REQUIRES_REVIEW: 2,
        ScreeningState.CONFIRMED_MATCH: 3,
    }
    for subject in subjects:
        for hit in providers.screening.screen(subject):
            state = ScreeningState(hit.state)
            session.add(
                ScreeningResult(
                    investigation_id=inv.investigation_id,
                    subject_label=hit.subject_label,
                    list_or_source=hit.list_or_source,
                    state=state,
                    match_basis=hit.match_basis,
                    provider_event_group=hit.provider_event_group,
                    article_count=hit.article_count,
                )
            )
            if order[state] > order[highest]:
                highest = state
    inv.screening_state = highest
    # Contact candidates: mark limited evidence (fixture) — never invents a person.
    for cand in inv.candidates:
        if cand.person_evidence_status is None:
            cand.person_evidence_status = PersonEvidenceStatus.LIMITED_EVIDENCE
