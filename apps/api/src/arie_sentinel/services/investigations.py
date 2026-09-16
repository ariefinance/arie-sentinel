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
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import get_settings
from ..intake.gate import assess_intake
from ..models.core import Counterparty, EntityCandidate, Identifier, Investigation, PersonCandidate
from ..models.enums import (
    AuditAction,
    CompanyIdentityStatus,
    CompletenessState,
    ExtractionConfidence,
    FindingType,
    IntakeState,
    InvestigationState,
    JobStatus,
    PersonEvidenceStatus,
    RelationshipState,
    ReviewStatus,
    ScreeningState,
    Severity,
    SourceClass,
)
from ..models.evidence import Evidence, Finding, ScreeningResult, Source
from ..models.ops import Job
from ..providers import ProviderUnavailable
from ..providers.base import CandidateEntity, ScreeningSubject
from ..providers.factory import Providers, build_providers
from ..providers.fixtures import build_fixture_providers
from ..providers.normalization import normalize_entity_name


def get_or_create_counterparty(
    session: Session, candidate: CandidateEntity | EntityCandidate
) -> tuple[Counterparty, bool]:
    """Return (counterparty, created). Dedup on identity_key; repeats link, not duplicate."""
    jurisdiction = candidate.jurisdiction
    registry_id = candidate.registry_id
    if not jurisdiction or not registry_id:
        raise ValueError("An authoritative jurisdiction and registry identifier are required.")
    key = f"{jurisdiction.strip().lower()}:{registry_id.strip().lower()}"
    existing = session.scalar(select(Counterparty).where(Counterparty.identity_key == key))
    if existing is not None:
        return existing, False
    cp = Counterparty(
        legal_name=candidate.legal_name,
        registry_class=candidate.registry_class,
        registry_id=candidate.registry_id,
        jurisdiction=candidate.jurisdiction,
        status=(
            candidate.status if isinstance(candidate, CandidateEntity) else candidate.legal_status
        ),
        identity_key=key,
        first_resolved_at=datetime.now(UTC),
    )
    session.add(cp)
    session.flush()
    return cp, True


def _derive_person_candidates(session: Session, investigation: Investigation) -> None:
    """0..N PersonCandidates from the raw contact_label. Model proposes; never confirms."""
    fragments = build_fixture_providers().model.extract_person_candidates(
        investigation.contact_label
    )
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
    _derive_person_candidates(session, investigation)
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
    providers: Providers | Any | None = None,
) -> None:
    """Discover and persist candidates; name-search cardinality never confirms identity."""
    providers = providers or build_providers(get_settings())
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

    for candidate in candidates:
        retrieved_at = _parse_time(candidate.retrieved_at)
        stored = EntityCandidate(
            investigation_id=inv.investigation_id,
            legal_name=candidate.legal_name,
            jurisdiction=candidate.jurisdiction,
            registry_class=candidate.registry_class,
            registry_id=candidate.registry_id,
            legal_status=candidate.status,
            registered_address=candidate.registered_address,
            incorporation_date=candidate.incorporation_date,
            lei=str(candidate.extra["lei"]) if candidate.extra.get("lei") else None,
            alternative_names=list(candidate.alternative_names),
            provider="corporate_registry",
            source_ref=candidate.source_ref,
            retrieved_at=retrieved_at,
            match_basis=candidate.match_basis,
        )
        session.add(stored)
        source = Source(
            investigation_id=inv.investigation_id,
            source_class=SourceClass.CORPORATE_REGISTRY,
            title=f"Registry candidate: {candidate.legal_name}",
            origin_ref=candidate.source_ref,
            retrieved_at=retrieved_at,
            captured_by="adapter:corporate_registry",
            limitations="Search result is a candidate until authoritative resolution.",
            license_class="provider-normalized",
        )
        session.add(source)
        session.flush()
        session.add(
            Evidence(
                source_id=source.source_id,
                observed_value={
                    "legal_name": candidate.legal_name,
                    "jurisdiction": candidate.jurisdiction,
                    "registry_id": candidate.registry_id,
                    "status": candidate.status,
                    "registered_address": candidate.registered_address,
                    "incorporation_date": candidate.incorporation_date,
                },
                extracted_by="adapter:corporate_registry",
                extraction_confidence=ExtractionConfidence.AUTHORITATIVE,
            )
        )

    if len(candidates) == 0:
        inv.company_identity_status = CompanyIdentityStatus.NOT_VERIFIED
        inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
    else:
        inv.company_identity_status = CompanyIdentityStatus.AMBIGUOUS
        inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
        record_audit(
            session,
            actor="adapter:corporate_registry",
            action=AuditAction.STATE_CHANGE,
            object_type="investigation",
            investigation_id=inv.investigation_id,
            rationale="Registry search produced candidates; analyst resolution required.",
            payload={"candidate_count": len(candidates)},
        )

    inv.investigation_state = InvestigationState.COMPLETED


def resolve_entity(
    session: Session,
    investigation: Investigation,
    candidate: EntityCandidate,
    *,
    actor: str,
    rationale: str,
    providers: Providers | Any | None = None,
) -> Counterparty:
    if candidate.investigation_id != investigation.investigation_id:
        raise ValueError("Candidate does not belong to this investigation.")
    cp, _created = get_or_create_counterparty(session, candidate)
    investigation.counterparty_id = cp.counterparty_id
    investigation.counterparty = cp
    investigation.company_identity_status = CompanyIdentityStatus.CONFIRMED
    investigation.company_match_basis = f"Analyst selected: {candidate.match_basis or rationale}"
    investigation.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
    record_audit(
        session,
        actor=actor,
        action=AuditAction.RESOLVE_IDENTITY,
        object_type="counterparty",
        investigation_id=investigation.investigation_id,
        target_ref=str(cp.counterparty_id),
        rationale=rationale,
        payload={
            "identity_key": cp.identity_key,
            "candidate_id": str(candidate.entity_candidate_id),
        },
    )
    active_providers = providers or build_providers(get_settings())
    _run_screening(session, investigation, active_providers)
    _corroborate_contact(session, investigation, candidate, active_providers)
    gleif = getattr(active_providers, "gleif", None)
    if candidate.lei and gleif is not None:
        try:
            gleif_data = gleif.lookup_lei(candidate.lei)
        except ProviderUnavailable:
            gleif_data = None
        if gleif_data is not None:
            session.add(
                Identifier(
                    counterparty_id=cp.counterparty_id,
                    id_type="lei",
                    id_value=candidate.lei,
                )
            )
            gleif_source = Source(
                investigation_id=investigation.investigation_id,
                source_class=SourceClass.CORPORATE_REGISTRY,
                title=f"GLEIF LEI record: {candidate.lei}",
                origin_ref=f"{gleif.base_url}/lei-records/{candidate.lei}",
                retrieved_at=datetime.now(UTC),
                captured_by="adapter:gleif",
                limitations="GLEIF enrichment applies only to the supplied LEI.",
                license_class="GLEIF-public",
            )
            session.add(gleif_source)
            session.flush()
            session.add(
                Evidence(
                    source_id=gleif_source.source_id,
                    observed_value=gleif_data,
                    extracted_by="adapter:gleif",
                    extraction_confidence=ExtractionConfidence.AUTHORITATIVE,
                )
            )
    _run_public_intelligence(session, investigation, active_providers)
    return cp


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _corroborate_contact(
    session: Session,
    investigation: Investigation,
    entity: EntityCandidate,
    providers: Providers | Any,
) -> None:
    registry = providers.registry
    discover_officers = getattr(registry, "discover_officers", None)
    if discover_officers is None or not entity.jurisdiction or not entity.registry_id:
        return
    try:
        officers = discover_officers(
            investigation.contact_label, entity.jurisdiction, entity.registry_id
        )
    except ProviderUnavailable:
        return
    for person in investigation.candidates:
        person_norm = normalize_entity_name(person.label_fragment)
        matching = [
            officer
            for officer in officers
            if normalize_entity_name(str(officer.get("name", ""))) == person_norm
        ]
        if not matching:
            continue
        officer = matching[0]
        source = Source(
            investigation_id=investigation.investigation_id,
            source_class=SourceClass.CORPORATE_REGISTRY,
            title=f"Registry officer: {officer.get('name', person.label_fragment)}",
            origin_ref=str(officer.get("opencorporates_url"))
            if officer.get("opencorporates_url")
            else None,
            retrieved_at=datetime.now(UTC),
            captured_by="adapter:corporate_registry",
            limitations="Officer record corroborates the registry relationship at retrieval time.",
            license_class="provider-normalized",
        )
        session.add(source)
        session.flush()
        session.add(
            Evidence(
                source_id=source.source_id,
                observed_value={
                    "name": officer.get("name"),
                    "position": officer.get("position"),
                    "start_date": officer.get("start_date"),
                    "end_date": officer.get("end_date"),
                    "registry_id": entity.registry_id,
                },
                extracted_by="adapter:corporate_registry",
                extraction_confidence=ExtractionConfidence.AUTHORITATIVE,
            )
        )
        person.relationship_state = RelationshipState.VERIFIED
        person.person_evidence_status = PersonEvidenceStatus.IDENTITY_EVIDENCE_FOUND
        person.match_basis = "Exact normalized officer name and resolved registry identifier."


def _run_screening(session: Session, inv: Investigation, providers: Providers | Any) -> None:
    """Record screening hits for the counterparty + contact candidates (adjudicated later)."""
    company_label = inv.counterparty.legal_name if inv.counterparty else inv.company_label
    subjects = [ScreeningSubject(label=company_label, schema="Company")]
    subjects += [ScreeningSubject(label=c.label_fragment) for c in inv.candidates]
    highest = ScreeningState.NO_MATERIAL_MATCH
    order = {
        ScreeningState.NO_MATERIAL_MATCH: 0,
        ScreeningState.POTENTIAL_MATCH: 1,
        ScreeningState.MATCH_REQUIRES_REVIEW: 2,
        ScreeningState.CONFIRMED_MATCH: 3,
    }
    try:
        result_sets = [(subject, providers.screening.screen(subject)) for subject in subjects]
    except ProviderUnavailable as exc:
        inv.screening_state = None
        inv.completeness_state = CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
        record_audit(
            session,
            actor="adapter:screening",
            action=AuditAction.STATE_CHANGE,
            object_type="screening",
            investigation_id=inv.investigation_id,
            rationale=str(exc),
        )
        return
    for subject, hits in result_sets:
        source = Source(
            investigation_id=inv.investigation_id,
            source_class=SourceClass.SANCTIONS_PEP_SCREENING,
            title=f"Screening search: {subject.label}",
            origin_ref=None,
            retrieved_at=datetime.now(UTC),
            captured_by="adapter:screening",
            limitations="Matches require human disposition; normalized response retained only.",
            license_class="OpenSanctions-commercial-license-required",
        )
        session.add(source)
        session.flush()
        session.add(
            Evidence(
                source_id=source.source_id,
                observed_value={"subject": subject.label, "match_count": len(hits)},
                extracted_by="adapter:screening",
                extraction_confidence=ExtractionConfidence.REPORTED,
            )
        )
        for hit in hits:
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
                    source_id=source.source_id,
                    matched_profile_id=hit.profile_id,
                    match_score=hit.score,
                    match_explanation=hit.explanation,
                    matched_identifiers=hit.matched_identifiers,
                    datasets=list(hit.datasets),
                )
            )
            if order[state] > order[highest]:
                highest = state
    inv.screening_state = highest
    # Contact candidates: mark limited evidence (fixture) — never invents a person.
    for cand in inv.candidates:
        if cand.person_evidence_status is None:
            cand.person_evidence_status = PersonEvidenceStatus.LIMITED_EVIDENCE


def _run_public_intelligence(
    session: Session, inv: Investigation, providers: Providers | Any
) -> None:
    company = inv.counterparty.legal_name if inv.counterparty else inv.company_label
    contact = inv.contact_label
    queries = [
        f'"{company}"',
        f'"{company}" "{contact}"',
        f'"{company}" regulator',
        f'"{company}" lawsuit',
        f'"{company}" fraud',
    ]
    seen: set[str] = set()
    checked_domains: set[str] = set()
    evidence_ids: list[uuid.UUID] = []
    try:
        result_sets = [providers.web.search(query) for query in queries]
    except ProviderUnavailable as exc:
        record_audit(
            session,
            actor="adapter:web_search",
            action=AuditAction.STATE_CHANGE,
            object_type="web_research",
            investigation_id=inv.investigation_id,
            rationale=str(exc),
        )
        result_sets = []
    for results in result_sets:
        for result in results:
            if result.url in seen:
                continue
            seen.add(result.url)
            source = Source(
                investigation_id=inv.investigation_id,
                source_class=SourceClass.WEB_PUBLIC,
                title=result.title,
                origin_ref=result.url,
                retrieved_at=_parse_time(result.retrieved_at),
                captured_by="adapter:web_search",
                content_hash=result.content_hash,
                limitations="Public web content; discovery terms do not imply adverse content.",
                license_class="linked-public-source",
            )
            session.add(source)
            session.flush()
            if result.excerpt:
                evidence = Evidence(
                    source_id=source.source_id,
                    excerpt=result.excerpt,
                    observed_value={
                        "publisher": result.publisher,
                        "published_at": result.published_at,
                    },
                    extracted_by="adapter:web_search",
                    extraction_confidence=ExtractionConfidence.REPORTED,
                )
                session.add(evidence)
                session.flush()
                evidence_ids.append(evidence.evidence_id)
            domain = urlparse(result.url).hostname
            if domain and domain not in checked_domains:
                checked_domains.add(domain)
                try:
                    domain_record = providers.domain.lookup(domain)
                except ProviderUnavailable:
                    domain_record = None
                if domain_record is not None:
                    domain_source = Source(
                        investigation_id=inv.investigation_id,
                        source_class=SourceClass.DOMAIN_REGISTRATION,
                        title=f"RDAP record: {domain_record.domain}",
                        origin_ref=domain_record.source_ref,
                        retrieved_at=datetime.now(UTC),
                        captured_by="adapter:rdap",
                        limitations="Domain registration does not prove company ownership.",
                        license_class="public-rdap",
                    )
                    session.add(domain_source)
                    session.flush()
                    session.add(
                        Evidence(
                            source_id=domain_source.source_id,
                            observed_value={
                                "domain": domain_record.domain,
                                "registrar": domain_record.registrar,
                                "registered_on": domain_record.registered_on,
                                "updated_on": domain_record.updated_on,
                                "expires_on": domain_record.expires_on,
                                "nameservers": list(domain_record.nameservers),
                                "statuses": list(domain_record.statuses),
                            },
                            extracted_by="adapter:rdap",
                            extraction_confidence=ExtractionConfidence.REPORTED,
                        )
                    )
    for candidate in inv.candidates:
        if candidate.relationship_state is not RelationshipState.VERIFIED:
            candidate.relationship_state = RelationshipState.UNVERIFIED
            candidate.match_basis = "No authoritative company-person link was established."
    if any(c.relationship_state is RelationshipState.VERIFIED for c in inv.candidates):
        return
    session.add(
        Finding(
            investigation_id=inv.investigation_id,
            finding_type=FindingType.INSUFFICIENT_EVIDENCE,
            severity=Severity.MEDIUM,
            title="Named contact relationship not established",
            claim_text=f"{contact} is connected to {company}.",
            evidence_text=(
                "No authoritative officer or company-controlled corroboration was retained."
            ),
            assessment_text=(
                "The supplied contact could not be independently connected to the resolved "
                "legal entity."
            ),
            action_text=(
                "Obtain registry officer evidence or independent corroboration before reliance."
            ),
            related_evidence_ids=evidence_ids or None,
            review_status=ReviewStatus.OPEN,
            created_by="system",
        )
    )
