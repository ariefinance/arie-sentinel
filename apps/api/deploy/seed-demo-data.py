"""Idempotently preload the supported non-live management-demo cases."""

from sqlalchemy import select

from arie_sentinel.config import Settings
from arie_sentinel.db import SessionLocal
from arie_sentinel.demo_cases import demo_case_context
from arie_sentinel.models.core import Investigation
from arie_sentinel.services.investigations import create_investigation

settings = Settings()
if settings.env.lower() == "demo" and settings.provider_mode == "fixture":
    cases = (
        ("Orion Petro Trading", "Karim Mansour"),
        ("Pacific Energy Procurement Ltd", "Daniel Kim"),
        ("Atlas Global Fuels", "Michael Grant"),
        ("Northstar Petroleum Trading", "Victor Lane"),
        ("Meridian Energy Supplies Ltd", "Amira Hassan"),
        ("ARIE Finance", ""),
    )
    created = 0
    with SessionLocal() as session:
        for company_label, contact_label in cases:
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
                continue
            create_investigation(
                session,
                company_label=company_label,
                contact_label=contact_label,
                actor=settings.dev_manager_email,
            )
            created += 1
        session.commit()
    print(f"Management-demo preload complete; created {created} missing case(s).")
else:
    print("Management-demo preload skipped outside fixture-backed demo mode.")
