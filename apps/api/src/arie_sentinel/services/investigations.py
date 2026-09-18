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
from ..demo_cases import PUBLIC_VALIDATION_CASE, demo_case_context
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
from ..models.ops import AuditEvent, Job
from ..providers import DemoDatasetUnsupported, ProviderUnavailable
from ..providers.base import (
    CandidateEntity,
    ProviderInvalidResponse,
    RegistryCoverageUnavailable,
    ScreeningSubject,
)
from ..providers.factory import Providers, build_providers
from ..providers.normalization import normalize_entity_name
from ..providers.sanctions import OfficialSanctionsProvider
from .contradictions import run_contradiction_checks
from .sanctions_cache import CoverageReport, load_sanctions_matcher

# A material source that could not be reached OR returned malformed data is
# handled the same way: an explicit source-unavailable/limited state, never a
# crash and never fabricated results.
_SOURCE_FAILURE = (ProviderUnavailable, ProviderInvalidResponse)

_THIRD_PARTY_DOMAIN_SUFFIXES = (
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "google.com",
    "bing.com",
    "duckduckgo.com",
)

PUBLIC_VALIDATION_SCREENING_LIMITATION = (
    "Live sanctions/PEP screening was not performed in this management environment. "
    "No live screening conclusion is available."
)


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
    """Retain the supplied contact as one unverified candidate; never invent people."""
    label = investigation.contact_label.strip()
    if label:
        session.add(
            PersonCandidate(
                investigation_id=investigation.investigation_id,
                label_fragment=label,
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
    investigation_context: str | None = None,
    claims: dict[str, Any] | None = None,
    import_batch_id: uuid.UUID | None = None,
    source_row_ref: str | None = None,
) -> Investigation:
    """Create one Investigation, run the intake gate, and enqueue discovery when sufficient."""
    normalized_contact = contact_label or ""
    assessment = assess_intake(company_label, normalized_contact)
    stored_context = dict(case_context or {})
    # Optional analyst context + subject claims are non-evidentiary intake inputs
    # stored alongside case context; they steer emphasis and feed the contradiction
    # engine, never the facts themselves.
    if investigation_context:
        stored_context.setdefault("investigation_context", investigation_context)
    if claims:
        stored_context.setdefault("claims", claims)
    if get_settings().provider_mode == "fixture":
        for key, value in demo_case_context(company_label).items():
            stored_context.setdefault(key, value)

    investigation = Investigation(
        company_label=company_label,
        contact_label=normalized_contact,
        intake_state=assessment.state,
        clarification_reason=assessment.reason,
        investigation_state=InvestigationState.NOT_STARTED,
        case_context=stored_context or None,
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


def _jurisdiction_hint(inv: Investigation) -> str | None:
    """Return the optional analyst-supplied jurisdiction routing hint, if any.

    Sourced from the intake claim / case context (never a discovered fact); it only
    steers which free authoritative registry is consulted.
    """
    for source in (inv.claims, inv.case_context or {}):
        value = source.get("jurisdiction")
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    return None


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

    jurisdiction_hint = _jurisdiction_hint(inv)
    try:
        candidates = providers.registry.discover_candidates(
            inv.company_label, jurisdiction=jurisdiction_hint
        )
    except RegistryCoverageUnavailable as exc:
        # No FREE authoritative registry covers this jurisdiction. This is an explicit
        # coverage limitation, NOT a source outage and NOT a nonexistence finding.
        inv.investigation_state = InvestigationState.COMPLETED
        inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
        inv.company_identity_status = CompanyIdentityStatus.NOT_VERIFIED
        inv.clarification_reason = str(exc)
        record_audit(
            session,
            actor="adapter:free_registry",
            action=AuditAction.STATE_CHANGE,
            object_type="investigation",
            investigation_id=inv.investigation_id,
            rationale=str(exc),
            payload={
                "investigation_state": inv.investigation_state.value,
                "coverage": "free-registry-unavailable",
                "jurisdiction_hint": jurisdiction_hint,
            },
        )
        return
    except DemoDatasetUnsupported as exc:
        inv.investigation_state = InvestigationState.SOURCE_UNAVAILABLE
        inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
        inv.company_identity_status = None
        inv.clarification_reason = str(exc)
        record_audit(
            session,
            actor="adapter:demo_registry",
            action=AuditAction.STATE_CHANGE,
            object_type="investigation",
            investigation_id=inv.investigation_id,
            rationale=str(exc),
            payload={"investigation_state": inv.investigation_state.value},
        )
        return
    except _SOURCE_FAILURE as exc:
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
            payload={
                "investigation_state": inv.investigation_state.value,
                "failure": type(exc).__name__,
            },
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
        is_public_validation = (inv.case_context or {}).get(
            "demo_case_type"
        ) == PUBLIC_VALIDATION_CASE
        fixture_mode = get_settings().provider_mode == "fixture"
        if is_public_validation:
            # Curated citation of a real public registry listing (no live capture).
            registry_captured_by = (
                "fixture:public_registry_citation" if fixture_mode else "adapter:corporate_registry"
            )
            registry_limitations = (
                "Curated citation of an official public listing prepared for the management demo; "
                "not a live registry capture. It confirms the legal name and registration "
                "identifier but does not state current legal or regulatory status. Analyst "
                "resolution is still required."
                if fixture_mode
                else (
                    "Official public listing confirms the legal name and registration identifier; "
                    "it does not state current legal or regulatory status. Analyst resolution is "
                    "still required."
                )
            )
            registry_license = "public-government-source"
            registry_extracted_by = (
                "fixture:public_registry_citation" if fixture_mode else "adapter:corporate_registry"
            )
        elif fixture_mode:
            registry_captured_by = "fixture:corporate_registry"
            registry_limitations = (
                "Fictional fixture registry record prepared for the management demo; not a live "
                "registry capture. Candidate until authoritative analyst resolution."
            )
            registry_license = "fixture-non-live"
            registry_extracted_by = "fixture:corporate_registry"
        else:
            registry_captured_by = "adapter:corporate_registry"
            registry_limitations = "Search result is a candidate until authoritative resolution."
            registry_license = "provider-normalized"
            registry_extracted_by = "adapter:corporate_registry"
        source = Source(
            investigation_id=inv.investigation_id,
            source_class=SourceClass.CORPORATE_REGISTRY,
            title=f"Registry candidate: {candidate.legal_name}",
            origin_ref=candidate.source_ref,
            retrieved_at=retrieved_at,
            captured_by=registry_captured_by,
            limitations=registry_limitations,
            license_class=registry_license,
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
                extracted_by=registry_extracted_by,
                extraction_confidence=ExtractionConfidence.AUTHORITATIVE,
            )
        )

    if len(candidates) == 0:
        inv.company_identity_status = CompanyIdentityStatus.NOT_VERIFIED
        inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
        inv.investigation_state = InvestigationState.COMPLETED
    else:
        inv.company_identity_status = CompanyIdentityStatus.AMBIGUOUS
        inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
        inv.investigation_state = InvestigationState.PARTIAL_RESULTS
        record_audit(
            session,
            actor="adapter:corporate_registry",
            action=AuditAction.STATE_CHANGE,
            object_type="investigation",
            investigation_id=inv.investigation_id,
            rationale="Registry search produced candidates; analyst resolution required.",
            payload={"candidate_count": len(candidates)},
        )


def resolve_entity(
    session: Session,
    investigation: Investigation,
    candidate: EntityCandidate,
    *,
    actor: str,
    rationale: str,
) -> Counterparty:
    if candidate.investigation_id != investigation.investigation_id:
        raise ValueError("Candidate does not belong to this investigation.")
    cp, _created = get_or_create_counterparty(session, candidate)
    investigation.counterparty_id = cp.counterparty_id
    investigation.counterparty = cp
    investigation.company_identity_status = CompanyIdentityStatus.CONFIRMED
    investigation.company_match_basis = f"Analyst selected: {candidate.match_basis or rationale}"
    investigation.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
    investigation.investigation_state = InvestigationState.PARTIAL_RESULTS
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
    existing_job = session.scalar(
        select(Job).where(
            Job.investigation_id == investigation.investigation_id,
            Job.job_type == "enrichment",
        )
    )
    if existing_job is None:
        session.add(
            Job(
                investigation_id=investigation.investigation_id,
                job_type="enrichment",
                status=JobStatus.PENDING,
                payload={
                    "investigation_id": str(investigation.investigation_id),
                    "candidate_id": str(candidate.entity_candidate_id),
                },
            )
        )
    return cp


def run_enrichment(
    session: Session,
    investigation_id: uuid.UUID,
    candidate_id: uuid.UUID,
    providers: Providers | Any | None = None,
) -> None:
    """Run idempotent post-resolution enrichment in the PostgreSQL worker."""
    investigation = session.get(Investigation, investigation_id)
    candidate = session.get(EntityCandidate, candidate_id)
    if (
        investigation is None
        or candidate is None
        or candidate.investigation_id != investigation_id
        or investigation.company_identity_status is not CompanyIdentityStatus.CONFIRMED
    ):
        raise ValueError("Enrichment requires a confirmed entity candidate.")
    completed = session.scalar(
        select(AuditEvent.event_id).where(
            AuditEvent.investigation_id == investigation_id,
            AuditEvent.object_type == "enrichment",
            AuditEvent.target_ref == str(candidate_id),
        )
    )
    if completed is not None:
        return

    investigation.investigation_state = InvestigationState.RUNNING
    active_providers = providers or build_providers(get_settings())
    if _public_validation_uses_fixture_providers(investigation):
        mark_public_validation_screening_not_performed(session, investigation)
    else:
        _run_screening(session, investigation, active_providers, candidate)
    _corroborate_contact(session, investigation, candidate, active_providers)
    gleif = getattr(active_providers, "gleif", None)
    if candidate.lei and gleif is not None:
        try:
            gleif_data = gleif.lookup_lei(candidate.lei)
        except _SOURCE_FAILURE as exc:
            # LEI enrichment is supplementary (a missing LEI is never adverse), so a
            # GLEIF outage is a coverage limitation, not a material-source failure.
            gleif_data = None
            _note_supplementary_limitation(
                session, investigation, actor="adapter:gleif", source="gleif", reason=str(exc)
            )
        if gleif_data is not None:
            existing_identifier = session.scalar(
                select(Identifier.identifier_id).where(
                    Identifier.counterparty_id == investigation.counterparty_id,
                    Identifier.id_type == "lei",
                    Identifier.id_value == candidate.lei,
                )
            )
            if existing_identifier is None:
                session.add(
                    Identifier(
                        counterparty_id=investigation.counterparty_id,
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
            _run_gleif_relationships(session, investigation, gleif, candidate.lei)
    _run_public_intelligence(session, investigation, active_providers)
    _run_supplementary_sources(session, investigation, active_providers)
    run_contradiction_checks(session, investigation, candidate)
    investigation.investigation_state = InvestigationState.COMPLETED
    record_audit(
        session,
        actor="worker:enrichment",
        action=AuditAction.STATE_CHANGE,
        object_type="enrichment",
        investigation_id=investigation_id,
        target_ref=str(candidate_id),
        payload={"status": "completed"},
    )


def _run_gleif_relationships(
    session: Session, investigation: Investigation, gleif: Any, lei: str
) -> None:
    """Persist GLEIF direct parent/child relationships (free) with provenance."""
    lookup_rel = getattr(gleif, "lookup_relationships", None)
    if lookup_rel is None:
        return
    try:
        relationships = lookup_rel(lei)
    except _SOURCE_FAILURE:
        return
    parent_lei = relationships.get("parent_lei") if isinstance(relationships, dict) else None
    child_leis = relationships.get("child_leis") if isinstance(relationships, dict) else None
    child_list = [str(c) for c in child_leis] if isinstance(child_leis, list) else []
    if not parent_lei and not child_list:
        return
    source = Source(
        investigation_id=investigation.investigation_id,
        source_class=SourceClass.CORPORATE_REGISTRY,
        title=f"GLEIF relationships: {lei}",
        origin_ref=f"{gleif.base_url}/lei-records/{lei}/direct-parent",
        retrieved_at=datetime.now(UTC),
        captured_by="adapter:gleif",
        limitations="GLEIF direct parent/child relationships for the supplied LEI.",
        license_class="GLEIF-public",
    )
    session.add(source)
    session.flush()
    session.add(
        Evidence(
            source_id=source.source_id,
            observed_value={
                "kind": "gleif_relationships",
                "parent_lei": parent_lei,
                "child_leis": child_list,
            },
            extracted_by="adapter:gleif",
            extraction_confidence=ExtractionConfidence.AUTHORITATIVE,
        )
    )


def _note_supplementary_limitation(
    session: Session, inv: Investigation, *, actor: str, source: str, reason: str
) -> None:
    """Record a SUPPLEMENTARY-source outage without downgrading the whole case.

    Supplementary sources (news discovery, US SEC corroboration, LEI enrichment) are
    optional: their unavailability is a coverage limitation, never a material-source
    failure. It must not overwrite a genuine MATERIAL_SOURCE_UNAVAILABLE already set.
    """
    if inv.completeness_state is not CompletenessState.MATERIAL_SOURCE_UNAVAILABLE:
        inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
    record_audit(
        session,
        actor=actor,
        action=AuditAction.STATE_CHANGE,
        object_type="supplementary_source",
        investigation_id=inv.investigation_id,
        rationale=reason,
        payload={"source": source, "status": "unavailable", "materiality": "supplementary"},
    )


def _run_supplementary_sources(
    session: Session, inv: Investigation, providers: Providers | Any
) -> None:
    """Free, no-key supplementary sourcing: GDELT discovery, SEC (US), Companies House (GB).

    All are optional and jurisdiction-gated; each fails closed to a source-unavailable
    limitation and never asserts absence as adverse. Discovery leads are not evidence.
    """
    company = inv.counterparty.legal_name if inv.counterparty else inv.company_label
    jurisdiction = ((inv.counterparty.jurisdiction if inv.counterparty else "") or "").upper()

    news = getattr(providers, "news", None)
    if news is not None:
        try:
            leads = news.search(company)
        except _SOURCE_FAILURE as exc:
            # GDELT is discovery-only (supplementary): its outage is a coverage
            # limitation, not a material-source failure for the whole case.
            _note_supplementary_limitation(
                session, inv, actor="adapter:gdelt", source="gdelt", reason=str(exc)
            )
            leads = []
        for lead in leads[:10]:
            session.add(
                Source(
                    investigation_id=inv.investigation_id,
                    source_class=SourceClass.WEB_PUBLIC,
                    title=lead.title,
                    origin_ref=lead.url,
                    retrieved_at=_parse_time(lead.retrieved_at),
                    captured_by="adapter:gdelt:discovery",
                    limitations=(
                        "Public-news discovery lead (GDELT); not evidence and not adverse "
                        "by itself. Analyst review required."
                    ),
                    license_class="linked-public-source",
                )
            )

    sec = getattr(providers, "sec", None)
    if sec is not None and jurisdiction.startswith("US"):
        try:
            records = sec.search_company(company)
        except _SOURCE_FAILURE as exc:
            # SEC EDGAR is US corroboration-only (supplementary); most companies are not
            # SEC filers, so its outage is a coverage limitation, not a material failure.
            _note_supplementary_limitation(
                session, inv, actor="adapter:sec_edgar", source="sec_edgar", reason=str(exc)
            )
            records = []
        if records:
            record = records[0]
            sec_source = Source(
                investigation_id=inv.investigation_id,
                source_class=SourceClass.CORPORATE_REGISTRY,
                title=f"SEC EDGAR: {record.name}",
                origin_ref="https://www.sec.gov/cgi-bin/browse-edgar",
                retrieved_at=datetime.now(UTC),
                captured_by="adapter:sec_edgar",
                limitations=(
                    "US SEC filer record. Absence of an EDGAR record is not adverse — most "
                    "companies are not SEC filers."
                ),
                license_class="public-sec",
            )
            session.add(sec_source)
            session.flush()
            session.add(
                Evidence(
                    source_id=sec_source.source_id,
                    observed_value={
                        "name": record.name,
                        "cik": record.cik,
                        "tickers": list(record.tickers),
                    },
                    extracted_by="adapter:sec_edgar",
                    extraction_confidence=ExtractionConfidence.REPORTED,
                )
            )

    companies_house = getattr(providers, "companies_house", None)
    registry_id = inv.counterparty.registry_id if inv.counterparty else None
    if companies_house is not None and jurisdiction.startswith("GB") and registry_id:
        try:
            profile = companies_house.get_company(registry_id)
        except _SOURCE_FAILURE as exc:
            inv.completeness_state = CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
            record_audit(
                session,
                actor="adapter:companies_house",
                action=AuditAction.STATE_CHANGE,
                object_type="public_intelligence",
                investigation_id=inv.investigation_id,
                rationale=str(exc),
                payload={"source": "companies_house", "status": "unavailable"},
            )
            profile = None
        if profile is not None:
            ch_source = Source(
                investigation_id=inv.investigation_id,
                source_class=SourceClass.CORPORATE_REGISTRY,
                title=f"Companies House: {profile.name}",
                origin_ref=f"https://find-and-update.company-information.service.gov.uk/company/{profile.company_number}",
                retrieved_at=datetime.now(UTC),
                captured_by="adapter:companies_house",
                limitations="UK Companies House public record for the resolved company number.",
                license_class="public-government-source",
            )
            session.add(ch_source)
            session.flush()
            session.add(
                Evidence(
                    source_id=ch_source.source_id,
                    observed_value={
                        "company_number": profile.company_number,
                        "name": profile.name,
                        "status": profile.status,
                        "incorporation_date": profile.incorporation_date,
                        "registered_address": profile.registered_address,
                    },
                    extracted_by="adapter:companies_house",
                    extraction_confidence=ExtractionConfidence.AUTHORITATIVE,
                )
            )


def _public_validation_uses_fixture_providers(investigation: Investigation) -> bool:
    """Return true when a real public case would otherwise use fictional screening."""
    return (
        get_settings().provider_mode == "fixture"
        and investigation.case_type == PUBLIC_VALIDATION_CASE
    )


def mark_public_validation_screening_not_performed(
    session: Session, investigation: Investigation
) -> None:
    """Persist and audit that fixture screening is invalid for a public validation case."""
    investigation.screening_state = None
    if investigation.completeness_state is None:
        investigation.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
    existing = session.scalar(
        select(AuditEvent.event_id).where(
            AuditEvent.investigation_id == investigation.investigation_id,
            AuditEvent.object_type == "screening",
            AuditEvent.target_ref == "live-screening-not-performed",
        )
    )
    if existing is None:
        record_audit(
            session,
            actor="system:demo_boundary",
            action=AuditAction.STATE_CHANGE,
            object_type="screening",
            investigation_id=investigation.investigation_id,
            target_ref="live-screening-not-performed",
            rationale=PUBLIC_VALIDATION_SCREENING_LIMITATION,
            payload={"status": "not_performed", "provider_mode": "fixture"},
        )


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
    if not investigation.candidates:
        return
    registry = providers.registry
    discover_officers = getattr(registry, "discover_officers", None)
    if discover_officers is None or not entity.jurisdiction or not entity.registry_id:
        return
    try:
        officers = discover_officers(
            investigation.contact_label, entity.jurisdiction, entity.registry_id
        )
    except _SOURCE_FAILURE as exc:
        investigation.completeness_state = CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
        record_audit(
            session,
            actor="adapter:corporate_registry",
            action=AuditAction.STATE_CHANGE,
            object_type="person_corroboration",
            investigation_id=investigation.investigation_id,
            rationale=str(exc),
            payload={"status": "unavailable"},
        )
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
        person.match_basis = (
            "The registry verifies that an officer with this normalized name is linked to the "
            "resolved company identifier; it does not conclusively verify the submitted human's "
            "physical identity."
        )
        person.person_evidence_status = PersonEvidenceStatus.LIMITED_EVIDENCE


def _country_from_jurisdiction(jurisdiction: str | None) -> tuple[str, ...]:
    if not jurisdiction:
        return ()
    country = jurisdiction.split("_", 1)[0].strip().upper()
    return (country,) if len(country) == 2 and country.isalpha() else ()


def _company_screening_subject(
    inv: Investigation, entity: EntityCandidate | None
) -> ScreeningSubject:
    company_label = inv.counterparty.legal_name if inv.counterparty else inv.company_label
    identifiers: dict[str, set[str]] = {}

    def add_identifier(key: str, value: str | None) -> None:
        if value and value.strip():
            identifiers.setdefault(key, set()).add(value.strip())

    aliases: tuple[str, ...] = ()
    countries: tuple[str, ...] = ()
    if entity is not None:
        aliases = tuple(
            name for name in (entity.alternative_names or []) if name and name != company_label
        )
        countries = _country_from_jurisdiction(entity.jurisdiction)
        add_identifier("registrationNumber", entity.registry_id)
        add_identifier("leiCode", entity.lei)
    if inv.counterparty is not None:
        identifier_map = {
            "registration_number": "registrationNumber",
            "company_number": "registrationNumber",
            "registry_id": "registrationNumber",
            "lei": "leiCode",
            "tax_number": "taxNumber",
        }
        for identifier in inv.counterparty.identifiers:
            property_name = identifier_map.get(identifier.id_type.lower())
            if property_name:
                add_identifier(property_name, identifier.id_value)
    return ScreeningSubject(
        label=company_label,
        schema="Company",
        aliases=aliases,
        countries=countries,
        identifiers={key: tuple(sorted(values)) for key, values in identifiers.items()},
    )


def _run_screening(
    session: Session,
    inv: Investigation,
    providers: Providers | Any,
    entity: EntityCandidate | None = None,
) -> None:
    """Record screening hits for the counterparty + contact candidates (adjudicated later)."""
    # Official sanctions feeds only: load the matcher from the local cache and capture
    # coverage. "No material match" is only assertable when every required feed is fresh.
    coverage: CoverageReport | None = None
    screener = getattr(providers, "screening", None)
    if isinstance(screener, OfficialSanctionsProvider):
        screener, coverage = load_sanctions_matcher(session, get_settings())
    subjects = [_company_screening_subject(inv, entity)]
    subjects += [ScreeningSubject(label=c.label_fragment) for c in inv.candidates]
    highest = ScreeningState.NO_MATERIAL_MATCH
    order = {
        ScreeningState.NO_MATERIAL_MATCH: 0,
        ScreeningState.POTENTIAL_MATCH: 1,
        ScreeningState.MATCH_REQUIRES_REVIEW: 2,
        ScreeningState.CONFIRMED_MATCH: 3,
    }
    if screener is None:
        screener = providers.screening
    try:
        result_sets = [(subject, screener.screen(subject)) for subject in subjects]
    except _SOURCE_FAILURE as exc:
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
            captured_by="adapter:official_sanctions",
            limitations=(
                "Screened against the cached official government sanctions feeds "
                "(OFAC/UN/UK/EU). Matches require human disposition; never auto-confirmed."
            ),
            license_class="official-government-sanctions-feed",
        )
        session.add(source)
        session.flush()
        session.add(
            Evidence(
                source_id=source.source_id,
                observed_value={
                    "subject": subject.label,
                    "aliases": list(subject.aliases),
                    "countries": list(subject.countries),
                    "birth_dates": list(subject.birth_dates),
                    "identifiers": {
                        key: list(values) for key, values in subject.identifiers.items()
                    },
                    "match_count": len(hits),
                },
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
    # Coverage gate: "no material match" is only assertable when every required official
    # feed is fresh in the cache. With incomplete coverage and no positive hit we must NOT
    # claim a clear screen — record a limitation instead. Real hits still surface.
    if (
        coverage is not None
        and not coverage.is_complete
        and highest is ScreeningState.NO_MATERIAL_MATCH
    ):
        inv.screening_state = None
        if inv.completeness_state is None:
            inv.completeness_state = CompletenessState.COMPLETE_WITH_LIMITATIONS
        record_audit(
            session,
            actor="adapter:official_sanctions",
            action=AuditAction.STATE_CHANGE,
            object_type="screening",
            investigation_id=inv.investigation_id,
            target_ref="sanctions-coverage-incomplete",
            rationale=coverage.limitation_text(),
            payload={
                "required": list(coverage.required),
                "fresh": list(coverage.fresh),
                "stale_or_missing": list(coverage.stale_or_missing),
            },
        )
    else:
        inv.screening_state = highest
    # Contact candidates: mark limited evidence (fixture) — never invents a person.
    for cand in inv.candidates:
        if cand.person_evidence_status is None:
            cand.person_evidence_status = PersonEvidenceStatus.LIMITED_EVIDENCE


def _run_public_intelligence(
    session: Session, inv: Investigation, providers: Providers | Any
) -> None:
    company = inv.counterparty.legal_name if inv.counterparty else inv.company_label
    contact = inv.contact_label.strip()
    queries = [
        f'"{company}"',
        f'"{company}" regulator',
        f'"{company}" lawsuit',
        f'"{company}" fraud',
    ]
    if contact:
        queries.insert(1, f'"{company}" "{contact}"')
    seen: set[str] = set()
    evidence_ids: list[uuid.UUID] = []
    try:
        result_sets = [providers.web.search(query) for query in queries]
    except _SOURCE_FAILURE as exc:
        inv.completeness_state = CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
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
            try:
                page = providers.web.retrieve(result.url)
            except _SOURCE_FAILURE:
                page = None
            captured = page is not None
            # A curated demo summary is NOT a live capture: label its provenance
            # so nobody can infer Sentinel downloaded the page (M1).
            curated = bool(page and page.curated)
            if curated:
                web_captured_by = "fixture:curated_summary"
                if inv.case_type == PUBLIC_VALIDATION_CASE:
                    web_limitations = (
                        "Curated summary of a public page prepared for the management demo; "
                        "not a live page capture."
                    )
                else:
                    web_limitations = (
                        "Fictional fixture source prepared for the management demo; "
                        "no live page was retrieved."
                    )
                web_license = "fixture-non-live"
            elif captured:
                web_captured_by = "adapter:web_retrieval"
                web_limitations = (
                    "Captured public page; discovery terms do not imply adverse content."
                )
                web_license = "linked-public-source"
            else:
                web_captured_by = "adapter:web_search:discovery"
                web_limitations = (
                    "Discovery lead only: underlying page was not captured; "
                    "search snippet is not evidence."
                )
                web_license = "linked-public-source"
            source = Source(
                investigation_id=inv.investigation_id,
                source_class=SourceClass.WEB_PUBLIC,
                title=result.title,
                origin_ref=result.url,
                retrieved_at=_parse_time(page.retrieved_at if page else result.retrieved_at),
                captured_by=web_captured_by,
                content_ref=page.url if page else None,
                content_hash=page.content_hash if page else None,
                limitations=web_limitations,
                license_class=web_license,
            )
            session.add(source)
            session.flush()
            if page is not None:
                evidence = Evidence(
                    source_id=source.source_id,
                    excerpt=page.content,
                    observed_value={
                        "publisher": result.publisher,
                        "published_at": result.published_at,
                        "content_type": page.content_type,
                        "captured_url": page.url,
                        "curated": curated,
                    },
                    extracted_by=(
                        "fixture:curated_summary" if curated else "adapter:web_retrieval"
                    ),
                    extraction_confidence=ExtractionConfidence.REPORTED,
                )
                session.add(evidence)
                session.flush()
                evidence_ids.append(evidence.evidence_id)
    for domain, association_basis in _claimed_company_domains(inv).items():
        try:
            domain_record = providers.domain.lookup(domain)
        except _SOURCE_FAILURE as exc:
            domain_record = None
            inv.completeness_state = CompletenessState.MATERIAL_SOURCE_UNAVAILABLE
            record_audit(
                session,
                actor="adapter:rdap",
                action=AuditAction.STATE_CHANGE,
                object_type="domain_research",
                investigation_id=inv.investigation_id,
                rationale=str(exc),
                payload={"domain": domain, "status": "unavailable"},
            )
        if domain_record is not None:
            domain_source = Source(
                investigation_id=inv.investigation_id,
                source_class=SourceClass.DOMAIN_REGISTRATION,
                title=f"RDAP record: {domain_record.domain}",
                origin_ref=domain_record.source_ref,
                retrieved_at=datetime.now(UTC),
                captured_by="adapter:rdap",
                limitations=(
                    f"Domain association basis: {association_basis}. "
                    "Registration metadata does not prove company ownership."
                ),
                license_class="public-rdap",
            )
            session.add(domain_source)
            session.flush()
            session.add(
                Evidence(
                    source_id=domain_source.source_id,
                    observed_value={
                        "domain": domain_record.domain,
                        "association_basis": association_basis,
                        "ownership_proven": False,
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
    if not inv.candidates:
        return
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


def _claimed_company_domains(inv: Investigation) -> dict[str, str]:
    """Return only explicitly claimed/recorded company domains, never search-result hosts."""
    domains: dict[str, str] = {}

    def add(value: object, basis: str) -> None:
        if not isinstance(value, str) or not value.strip():
            return
        candidate = value.strip()
        parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
        hostname = parsed.hostname.rstrip(".").lower() if parsed.hostname else None
        is_third_party = hostname and any(
            hostname == suffix or hostname.endswith(f".{suffix}")
            for suffix in _THIRD_PARTY_DOMAIN_SUFFIXES
        )
        if hostname and not is_third_party:
            domains[hostname] = basis

    context = inv.case_context or {}
    for key in ("company_domain", "domain", "website"):
        add(context.get(key), f"supplied case context field '{key}'")
    # Subject-supplied claims are the live intake path (Investigate UI stores the
    # website under claims). Consume the same values so a real analyst-entered
    # website drives RDAP/domain enrichment, not only the demo fixtures.
    claims = inv.claims
    for key in ("company_domain", "domain", "website"):
        add(claims.get(key), f"supplied intake claim '{key}'")
    if inv.counterparty is not None:
        for identifier in inv.counterparty.identifiers:
            if identifier.id_type.lower() in {"domain", "website"}:
                add(identifier.id_value, f"stored counterparty identifier '{identifier.id_type}'")
    return domains
