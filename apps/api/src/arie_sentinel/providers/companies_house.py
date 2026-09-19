"""UK Companies House Public Data API adapter — free, requires a free API key.

Applies only to UK entities. A missing key means the source is UNAVAILABLE/not
configured — never "no company exists". Absence of a record is not adverse.
Auth is HTTP Basic with the API key as the username and an empty password.
Register a free key at developer.company-information.service.gov.uk.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from .base import CandidateEntity, ProviderInvalidResponse, ProviderUnavailable
from .http import request_json


@dataclass(frozen=True)
class CompaniesHouseProfile:
    company_number: str
    name: str
    status: str | None
    incorporation_date: str | None
    registered_address: str | None
    officers: tuple[str, ...] = field(default_factory=tuple)


class CompaniesHouseProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.company-information.service.gov.uk",
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        # Companies House uses HTTP Basic auth: API key as username, empty password.
        self.client = httpx.Client(timeout=timeout, follow_redirects=True, auth=(api_key, ""))

    def search_company(self, name: str) -> list[CandidateEntity]:
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/search/companies",
            provider="companies_house",
            params={"q": name},
        )
        items = payload.get("items")
        if items is None:
            return []
        if not isinstance(items, list):
            raise ProviderInvalidResponse("companies_house: items must be a list")
        candidates: list[CandidateEntity] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            number = item.get("company_number")
            if not isinstance(title, str) or not isinstance(number, str):
                continue
            address = item.get("address_snippet")
            candidates.append(
                CandidateEntity(
                    legal_name=title,
                    jurisdiction="GB",
                    registry_class="companies_house",
                    registry_id=number,
                    status=item.get("company_status")
                    if isinstance(item.get("company_status"), str)
                    else None,
                    registered_address=address if isinstance(address, str) else None,
                    match_basis="Companies House name search; analyst resolution required",
                )
            )
        return candidates

    def get_company(self, company_number: str) -> CompaniesHouseProfile | None:
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/company/{company_number}",
            provider="companies_house",
        )
        name = payload.get("company_name")
        if not isinstance(name, str):
            return None
        office = payload.get("registered_office_address")
        address = None
        if isinstance(office, dict):
            parts = [
                office.get(k)
                for k in ("address_line_1", "locality", "postal_code", "country")
                if isinstance(office.get(k), str)
            ]
            address = ", ".join(p for p in parts if p) or None
        return CompaniesHouseProfile(
            company_number=company_number,
            name=name,
            status=payload.get("company_status")
            if isinstance(payload.get("company_status"), str)
            else None,
            incorporation_date=payload.get("date_of_creation")
            if isinstance(payload.get("date_of_creation"), str)
            else None,
            registered_address=address,
        )

    def get_officers(self, company_number: str) -> list[dict[str, str | None]]:
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/company/{company_number}/officers",
            provider="companies_house",
        )
        items = payload.get("items")
        if items is None:
            return []
        if not isinstance(items, list):
            raise ProviderInvalidResponse("companies_house: officers items must be a list")
        officers: list[dict[str, str | None]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str):
                officers.append(
                    {
                        "name": name,
                        "position": item.get("officer_role")
                        if isinstance(item.get("officer_role"), str)
                        else None,
                        "start_date": item.get("appointed_on")
                        if isinstance(item.get("appointed_on"), str)
                        else None,
                        "end_date": item.get("resigned_on")
                        if isinstance(item.get("resigned_on"), str)
                        else None,
                    }
                )
        return officers

    def get_psc(self, company_number: str) -> list[dict[str, str | None | list[str]]]:
        """Return persons with significant control (free PSC endpoint).

        The UK Companies House Public Data API exposes PSC data at
        ``/company/{number}/persons-with-significant-control``. Each entry carries the
        PSC name, kind, and natures of control.
        """
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/company/{company_number}/persons-with-significant-control",
            provider="companies_house",
        )
        items = payload.get("items")
        if items is None:
            return []
        if not isinstance(items, list):
            raise ProviderInvalidResponse("companies_house: psc items must be a list")
        pscs: list[dict[str, str | None | list[str]]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str):
                continue
            natures = item.get("natures_of_control")
            pscs.append(
                {
                    "name": name,
                    "kind": item.get("kind") if isinstance(item.get("kind"), str) else None,
                    "natures_of_control": [str(n) for n in natures]
                    if isinstance(natures, list)
                    else [],
                    "notified_on": item.get("notified_on")
                    if isinstance(item.get("notified_on"), str)
                    else None,
                    "ceased_on": item.get("ceased_on")
                    if isinstance(item.get("ceased_on"), str)
                    else None,
                }
            )
        return pscs


class UnavailableCompaniesHouseProvider:
    """Used when no free API key is configured — fails closed, never 'no company'."""

    def search_company(self, name: str) -> list[CandidateEntity]:
        raise ProviderUnavailable("companies_house: API key is not configured")

    def get_company(self, company_number: str) -> CompaniesHouseProfile | None:
        raise ProviderUnavailable("companies_house: API key is not configured")

    def get_officers(self, company_number: str) -> list[dict[str, str | None]]:
        raise ProviderUnavailable("companies_house: API key is not configured")

    def get_psc(self, company_number: str) -> list[dict[str, str | None | list[str]]]:
        raise ProviderUnavailable("companies_house: API key is not configured")
