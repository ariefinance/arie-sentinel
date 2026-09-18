"""Idempotently preload the supported non-live management-demo cases.

Company identities, canonical labels and case types come from the canonical
``demo_dataset`` (via ``iter_seed_cases``) — the same source of truth that drives
corporate discovery and case-type classification — so the seeder cannot drift from
the supported-company dataset (B1). Contacts are optional scenario inputs carried as
separate metadata in the canonical dataset.
"""

from sqlalchemy import select

from arie_sentinel.config import Settings
from arie_sentinel.db import SessionLocal
from arie_sentinel.demo_cases import demo_case_context
from arie_sentinel.demo_dataset import PUBLIC_VALIDATION_CASE, SEED_CLAIMS, iter_seed_cases
from arie_sentinel.models.core import Investigation
from arie_sentinel.services.investigations import (
    create_investigation,
    mark_public_validation_screening_not_performed,
)

settings = Settings()
if settings.env.lower() == "demo" and settings.provider_mode == "fixture":
    created = 0
    with SessionLocal() as session:
        for company_label, contact_label, case_type in iter_seed_cases():
            existing = session.scalar(
                select(Investigation).where(
                    Investigation.company_label == company_label,
                    Investigation.contact_label == contact_label,
                )
            )
            if existing is not None:
                context = dict(existing.case_context or {})
                for key, value in demo_case_context(company_label).items():
                    context.setdefault(key, value)
                existing.case_context = context or None
                if case_type == PUBLIC_VALIDATION_CASE:
                    mark_public_validation_screening_not_performed(session, existing)
                continue
            create_investigation(
                session,
                company_label=company_label,
                contact_label=contact_label,
                actor=settings.dev_manager_email,
                claims=SEED_CLAIMS.get(company_label),
            )
            created += 1
        session.commit()
    print(f"Management-demo preload complete; created {created} missing case(s).")
else:
    print("Management-demo preload skipped outside fixture-backed demo mode.")
