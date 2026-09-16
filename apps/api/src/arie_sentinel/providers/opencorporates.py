"""OpenCorporates company discovery adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from .base import CandidateEntity, ProviderInvalidResponse
from .http import request_json
from .normalization import normalize_entity_name


class OpenCorporatesProvider:
    def __init__(self, base_url: str, api_key: str | None, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    def discover_candidates(self, company_label: str) -> list[CandidateEntity]:
        params = {"q": company_label, "order": "score"}
        if self.api_key:
            params["api_token"] = self.api_key
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/companies/search",
            provider="opencorporates",
            params=params,
        )
        companies = payload.get("results", {}).get("companies")
        if not isinstance(companies, list):
            raise ProviderInvalidResponse("opencorporates: results.companies missing")
        retrieved = datetime.now(UTC).isoformat()
        query_norm = normalize_entity_name(company_label)
        output: list[CandidateEntity] = []
        for wrapper in companies:
            company: Any = wrapper.get("company") if isinstance(wrapper, dict) else None
            if not isinstance(company, dict) or not company.get("name"):
                continue
            address = company.get("registered_address")
            address_text = None
            if isinstance(address, dict):
                address_text = ", ".join(str(v) for v in address.values() if v)
            legal_name = str(company["name"])
            previous_names = company.get("previous_names", [])
            names = tuple(
                str(item["company_name"])
                for item in previous_names
                if isinstance(item, dict) and item.get("company_name")
            )
            output.append(
                CandidateEntity(
                    legal_name=legal_name,
                    jurisdiction=company.get("jurisdiction_code"),
                    registry_class="opencorporates",
                    registry_id=company.get("company_number"),
                    status=company.get("current_status"),
                    incorporation_date=company.get("incorporation_date"),
                    registered_address=address_text,
                    alternative_names=names,
                    source_ref=company.get("opencorporates_url"),
                    retrieved_at=retrieved,
                    match_basis=(
                        "exact normalized legal name"
                        if normalize_entity_name(legal_name) == query_norm
                        else "provider-ranked name search"
                    ),
                    extra={"company_type": company.get("company_type"), "lei": company.get("lei")},
                )
            )
        return output

    def discover_officers(
        self, contact_label: str, jurisdiction: str, registry_id: str
    ) -> list[dict[str, Any]]:
        params = {"q": contact_label, "jurisdiction_code": jurisdiction, "order": "score"}
        if self.api_key:
            params["api_token"] = self.api_key
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/officers/search",
            provider="opencorporates",
            params=params,
        )
        rows = payload.get("results", {}).get("officers")
        if not isinstance(rows, list):
            raise ProviderInvalidResponse("opencorporates: results.officers missing")
        matches: list[dict[str, Any]] = []
        for wrapper in rows:
            officer = wrapper.get("officer") if isinstance(wrapper, dict) else None
            company = officer.get("company") if isinstance(officer, dict) else None
            if not isinstance(company, dict) or not isinstance(officer, dict):
                continue
            if str(company.get("company_number", "")).casefold() != registry_id.casefold():
                continue
            matches.append(officer)
        return matches
