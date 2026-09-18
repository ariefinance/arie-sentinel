"""Contradiction engine: compare subject claims against discovered evidence.

Rules are pure functions over a :class:`ContradictionContext`, kept out of UI and
persistence so they stay extensible and unit-testable. A discrepancy is reported as
a discrepancy requiring review — never as "fraud" — and missing/unavailable data
never manufactures a contradiction.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..models.core import EntityCandidate, Investigation
from ..models.enums import AuditAction, FindingType, ReviewStatus, Severity, SourceClass
from ..models.evidence import Evidence, Finding, Source


@dataclass(frozen=True)
class DomainFact:
    domain: str
    registered_on: str | None
    evidence_id: uuid.UUID | None = None


@dataclass(frozen=True)
class ContradictionContext:
    """Everything a rule needs, decoupled from the database for testability."""

    claims: dict[str, object]
    contact_label: str = ""
    registry_legal_name: str | None = None
    registry_jurisdiction: str | None = None
    registry_id: str | None = None
    registry_incorporation_date: str | None = None
    registry_evidence_id: uuid.UUID | None = None
    officer_names: tuple[str, ...] = ()
    officer_evidence_ids: tuple[uuid.UUID, ...] = ()
    domains: tuple[DomainFact, ...] = ()
    has_authoritative_regulator_source: bool = False


@dataclass(frozen=True)
class ContradictionResult:
    key: str  # stable rule identity, used for idempotent persistence
    finding_type: FindingType
    severity: Severity
    title: str
    claim_text: str
    evidence_text: str
    assessment_text: str
    action_text: str
    evidence_ids: tuple[uuid.UUID, ...] = ()


Rule = Callable[[ContradictionContext], ContradictionResult | None]


def _claim_str(claims: dict[str, object], key: str) -> str | None:
    value = claims.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _year(value: str | None) -> int | None:
    if not value:
        return None
    digits = ""
    for char in value:
        if char.isdigit():
            digits += char
            if len(digits) == 4:
                break
        elif digits:
            break
    return int(digits) if len(digits) == 4 else None


def _norm(value: str | None) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def _domain_of(email_or_url: str | None) -> str | None:
    if not email_or_url:
        return None
    text = email_or_url.strip().lower()
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    text = text.split("//", 1)[-1]
    text = text.split("/", 1)[0]
    text = text.split(":", 1)[0]
    return text.removeprefix("www.") or None


# --- Rules ---------------------------------------------------------------------------


def _operating_since_before_incorporation(ctx: ContradictionContext) -> ContradictionResult | None:
    claimed = _year(_claim_str(ctx.claims, "operating_since_year")) or _year(
        _claim_str(ctx.claims, "incorporation_year")
    )
    registry = _year(ctx.registry_incorporation_date)
    if claimed is None or registry is None:
        return None  # no false contradiction when either side is unknown
    if claimed < registry - 1:
        return ContradictionResult(
            key="operating_since_before_incorporation",
            finding_type=FindingType.CONTRADICTION,
            severity=Severity.HIGH,
            title="Claimed operating history predates registry incorporation",
            claim_text=f"Subject claims operating since {claimed}.",
            evidence_text=f"Registry incorporation year is {registry}.",
            assessment_text=(
                "The claimed operating history materially predates the registered "
                "incorporation date. This is a discrepancy requiring analyst review."
            ),
            action_text=(
                "Confirm whether a predecessor entity or rebrand explains the gap, or "
                "treat the operating-history claim as unsubstantiated."
            ),
            evidence_ids=tuple(e for e in (ctx.registry_evidence_id,) if e is not None),
        )
    return None


def _jurisdiction_mismatch(ctx: ContradictionContext) -> ContradictionResult | None:
    claimed = _claim_str(ctx.claims, "jurisdiction")
    if not claimed or not ctx.registry_jurisdiction:
        return None
    if (
        _norm(claimed)
        and _norm(claimed) not in _norm(ctx.registry_jurisdiction)
        and _norm(ctx.registry_jurisdiction) not in _norm(claimed)
    ):
        return ContradictionResult(
            key="jurisdiction_mismatch",
            finding_type=FindingType.CONTRADICTION,
            severity=Severity.HIGH,
            title="Claimed jurisdiction conflicts with registry identity",
            claim_text=f"Subject states jurisdiction '{claimed}'.",
            evidence_text=f"Resolved registry jurisdiction is '{ctx.registry_jurisdiction}'.",
            assessment_text=(
                "The stated jurisdiction does not match the resolved legal entity's "
                "registry jurisdiction. Discrepancy requiring review."
            ),
            action_text="Confirm which jurisdiction the counterparty actually operates under.",
            evidence_ids=tuple(e for e in (ctx.registry_evidence_id,) if e is not None),
        )
    return None


def _registration_number_mismatch(ctx: ContradictionContext) -> ContradictionResult | None:
    claimed = _claim_str(ctx.claims, "registration_number")
    if not claimed or not ctx.registry_id:
        return None
    if _norm(claimed) != _norm(ctx.registry_id):
        return ContradictionResult(
            key="registration_number_mismatch",
            finding_type=FindingType.CONTRADICTION,
            severity=Severity.HIGH,
            title="Supplied registration number does not match resolved entity",
            claim_text=f"Supplied registration number '{claimed}'.",
            evidence_text=f"Resolved registry identifier is '{ctx.registry_id}'.",
            assessment_text=(
                "The supplied registration number differs from the resolved legal "
                "entity's registry identifier. Discrepancy requiring review."
            ),
            action_text="Confirm the correct registration number and re-resolve if necessary.",
            evidence_ids=tuple(e for e in (ctx.registry_evidence_id,) if e is not None),
        )
    return None


def _claimed_director_not_found(ctx: ContradictionContext) -> ContradictionResult | None:
    raw = ctx.claims.get("directors")
    claimed_directors = (
        [str(d).strip() for d in raw if str(d).strip()] if isinstance(raw, list) else []
    )
    if not claimed_directors or not ctx.officer_names:
        # No officer data discovered -> cannot assert a contradiction (source-limited).
        return None
    known = {_norm(name) for name in ctx.officer_names}
    missing = [d for d in claimed_directors if _norm(d) not in known]
    if missing:
        return ContradictionResult(
            key="claimed_director_not_found",
            finding_type=FindingType.INCONSISTENCY,
            severity=Severity.MEDIUM,
            title="Claimed director not found among registry officers",
            claim_text=f"Subject names director(s): {', '.join(claimed_directors)}.",
            evidence_text=f"Registry officers discovered: {', '.join(ctx.officer_names)}.",
            assessment_text=(
                "One or more claimed directors were not found among the discovered "
                "registry officers: " + ", ".join(missing) + ". Discrepancy requiring review."
            ),
            action_text="Obtain evidence for the claimed director(s) or treat as unverified.",
            evidence_ids=ctx.officer_evidence_ids,
        )
    return None


def _licence_not_independently_established(ctx: ContradictionContext) -> ContradictionResult | None:
    claimed = _claim_str(ctx.claims, "licence") or _claim_str(ctx.claims, "regulator")
    if not claimed or ctx.has_authoritative_regulator_source:
        return None
    return ContradictionResult(
        key="licence_not_independently_established",
        finding_type=FindingType.UNVERIFIED_CLAIM,
        severity=Severity.MEDIUM,
        title="Regulatory/licence claim not independently established",
        claim_text=f"Subject claims regulatory status/licence: {claimed}.",
        evidence_text="No authoritative regulator source establishing this was retained.",
        assessment_text=(
            "The regulatory/licence claim is not corroborated by an authoritative "
            "regulator source. It remains a company-controlled claim, not established fact."
        ),
        action_text="Verify the licence against the relevant regulator's public register.",
    )


def _contact_email_domain_mismatch(ctx: ContradictionContext) -> ContradictionResult | None:
    email_domain = _domain_of(_claim_str(ctx.claims, "contact_email"))
    company_domain = _domain_of(
        _claim_str(ctx.claims, "website") or _claim_str(ctx.claims, "company_domain")
    )
    if not email_domain or not company_domain:
        return None
    if email_domain != company_domain:
        return ContradictionResult(
            key="contact_email_domain_mismatch",
            finding_type=FindingType.INCONSISTENCY,
            severity=Severity.LOW,
            title="Contact email domain differs from the company domain",
            claim_text=f"Contact email uses domain '{email_domain}'.",
            evidence_text=f"Stated company domain is '{company_domain}'.",
            assessment_text=(
                "The contact's email domain is materially unrelated to the stated "
                "company domain. Discrepancy requiring review, not itself adverse."
            ),
            action_text="Confirm the contact operates under the company's own domain.",
        )
    return None


def _domain_age_vs_operating_history(ctx: ContradictionContext) -> ContradictionResult | None:
    claimed = _year(_claim_str(ctx.claims, "operating_since_year"))
    if claimed is None or not ctx.domains:
        return None
    company_domain = _domain_of(
        _claim_str(ctx.claims, "website") or _claim_str(ctx.claims, "company_domain")
    )
    for domain in ctx.domains:
        if company_domain and _norm(domain.domain) != _norm(company_domain):
            continue
        registered = _year(domain.registered_on)
        if registered is not None and registered > claimed + 2:
            return ContradictionResult(
                key="domain_age_vs_operating_history",
                finding_type=FindingType.ANOMALY,
                severity=Severity.LOW,
                title="Domain registered materially later than claimed operating history",
                claim_text=f"Subject claims operating since {claimed}.",
                evidence_text=f"Domain '{domain.domain}' was registered in {registered}.",
                assessment_text=(
                    "The company's domain was registered materially later than its "
                    "claimed operating history. Potential inconsistency for review; a "
                    "recent domain alone is not evidence of wrongdoing."
                ),
                action_text="Confirm the domain history or the operating-since claim.",
                evidence_ids=tuple(e for e in (domain.evidence_id,) if e is not None),
            )
    return None


# Ordered, extensible registry. Add a rule here — never inside a UI component.
RULES: tuple[Rule, ...] = (
    _operating_since_before_incorporation,
    _jurisdiction_mismatch,
    _registration_number_mismatch,
    _claimed_director_not_found,
    _licence_not_independently_established,
    _contact_email_domain_mismatch,
    _domain_age_vs_operating_history,
)


def evaluate(ctx: ContradictionContext) -> list[ContradictionResult]:
    """Run every rule; a rule returning None simply contributes nothing."""
    results: list[ContradictionResult] = []
    for rule in RULES:
        result = rule(ctx)
        if result is not None:
            results.append(result)
    return results


# --- DB integration ------------------------------------------------------------------

_AUTHORITATIVE_LICENCES = {"public-government-source"}


def build_context(
    session: Session, investigation: Investigation, resolved: EntityCandidate | None
) -> ContradictionContext:
    """Assemble a ContradictionContext from persisted evidence + the resolved entity."""
    rows = list(
        session.execute(
            select(Evidence, Source)
            .join(Source, Evidence.source_id == Source.source_id)
            .where(Source.investigation_id == investigation.investigation_id)
        )
    )
    officer_names: list[str] = []
    officer_ids: list[uuid.UUID] = []
    domains: list[DomainFact] = []
    has_regulator = False
    for evidence, source in rows:
        observed = evidence.observed_value or {}
        if source.source_class is SourceClass.DOMAIN_REGISTRATION:
            domain = observed.get("domain")
            if isinstance(domain, str):
                registered = observed.get("registered_on")
                domains.append(
                    DomainFact(
                        domain=domain,
                        registered_on=registered if isinstance(registered, str) else None,
                        evidence_id=evidence.evidence_id,
                    )
                )
        if source.source_class is SourceClass.CORPORATE_REGISTRY and observed.get("position"):
            name = observed.get("name")
            if isinstance(name, str):
                officer_names.append(name)
                officer_ids.append(evidence.evidence_id)
        if source.license_class in _AUTHORITATIVE_LICENCES:
            has_regulator = True

    registry_evidence_id: uuid.UUID | None = None
    if resolved is not None:
        for evidence, source in rows:
            observed = evidence.observed_value or {}
            if (
                source.source_class is SourceClass.CORPORATE_REGISTRY
                and _norm(str(observed.get("registry_id"))) == _norm(resolved.registry_id)
                and observed.get("position") is None
            ):
                registry_evidence_id = evidence.evidence_id
                break

    return ContradictionContext(
        claims=investigation.claims,
        contact_label=investigation.contact_label,
        registry_legal_name=resolved.legal_name if resolved else None,
        registry_jurisdiction=resolved.jurisdiction if resolved else None,
        registry_id=resolved.registry_id if resolved else None,
        registry_incorporation_date=resolved.incorporation_date if resolved else None,
        registry_evidence_id=registry_evidence_id,
        officer_names=tuple(officer_names),
        officer_evidence_ids=tuple(officer_ids),
        domains=tuple(domains),
        has_authoritative_regulator_source=has_regulator,
    )


def run_contradiction_checks(
    session: Session, investigation: Investigation, resolved: EntityCandidate | None
) -> list[Finding]:
    """Evaluate rules and persist new contradictions as Findings (idempotent by key)."""
    context = build_context(session, investigation, resolved)
    results = evaluate(context)
    if not results:
        return []
    existing_titles = set(
        session.scalars(
            select(Finding.title).where(Finding.investigation_id == investigation.investigation_id)
        )
    )
    created: list[Finding] = []
    for result in results:
        if result.title in existing_titles:
            continue
        finding = Finding(
            investigation_id=investigation.investigation_id,
            finding_type=result.finding_type,
            severity=result.severity,
            title=result.title,
            claim_text=result.claim_text,
            evidence_text=result.evidence_text,
            assessment_text=result.assessment_text,
            action_text=result.action_text,
            related_evidence_ids=list(result.evidence_ids) or None,
            review_status=ReviewStatus.OPEN,
            created_by="system:contradiction_engine",
        )
        session.add(finding)
        created.append(finding)
        record_audit(
            session,
            actor="system:contradiction_engine",
            action=AuditAction.STATE_CHANGE,
            object_type="contradiction",
            investigation_id=investigation.investigation_id,
            rationale=result.assessment_text,
            payload={"rule": result.key, "finding_type": result.finding_type.value},
        )
    return created
