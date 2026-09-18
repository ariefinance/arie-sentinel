"""GLEIF LEI enrichment adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from .base import CandidateEntity, ProviderInvalidResponse, ProviderUnavailable
from .http import request_json


class GleifProvider:
    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    def search_by_name(
        self, company_label: str, jurisdiction: str | None = None
    ) -> list[CandidateEntity]:
        """Free GLEIF legal-name search (any jurisdiction).

        Returns 0..N LEI-registered candidates. An empty result means "no LEI located"
        — an absence, never a nonexistence finding and never fabricated. Optionally
        filtered by the analyst-supplied jurisdiction hint.
        """
        params: dict[str, str] = {
            "filter[entity.legalName]": company_label,
            "page[size]": "10",
        }
        juris = (jurisdiction or "").strip().upper()
        if len(juris) == 2 and juris.isalpha():
            params["filter[entity.jurisdiction]"] = juris
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/lei-records",
            provider="gleif",
            params=params,
        )
        records = payload.get("data")
        if records is None:
            return []
        if not isinstance(records, list):
            raise ProviderInvalidResponse("gleif: data must be a list")
        retrieved = datetime.now(UTC).isoformat()
        candidates: list[CandidateEntity] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            lei = record.get("id")
            attributes = record.get("attributes")
            if not isinstance(attributes, dict) or not isinstance(lei, str):
                continue
            entity = attributes.get("entity")
            if not isinstance(entity, dict):
                continue
            legal_name_obj = entity.get("legalName")
            legal_name = (
                legal_name_obj.get("name") if isinstance(legal_name_obj, dict) else None
            )
            if not isinstance(legal_name, str) or not legal_name.strip():
                continue
            status_obj = entity.get("status")
            address_obj = entity.get("legalAddress")
            address_text = None
            if isinstance(address_obj, dict):
                parts = [
                    address_obj.get(k)
                    for k in ("addressLines", "city", "region", "postalCode", "country")
                ]
                flat: list[str] = []
                for part in parts:
                    if isinstance(part, list):
                        flat += [str(p) for p in part if p]
                    elif isinstance(part, str) and part:
                        flat.append(part)
                address_text = ", ".join(flat) or None
            other_names = entity.get("otherNames")
            aliases: tuple[str, ...] = ()
            if isinstance(other_names, list):
                aliases = tuple(
                    str(item.get("name"))
                    for item in other_names
                    if isinstance(item, dict) and isinstance(item.get("name"), str)
                )
            candidates.append(
                CandidateEntity(
                    legal_name=legal_name,
                    jurisdiction=entity.get("jurisdiction")
                    if isinstance(entity.get("jurisdiction"), str)
                    else None,
                    registry_class="gleif",
                    registry_id=lei,
                    status=status_obj if isinstance(status_obj, str) else None,
                    registered_address=address_text,
                    alternative_names=aliases,
                    source_ref=f"{self.base_url}/lei-records/{lei}",
                    retrieved_at=retrieved,
                    match_basis=(
                        "GLEIF legal-name search (LEI issuers, any jurisdiction); "
                        "candidate until authoritative analyst resolution"
                    ),
                    extra={"lei": lei},
                )
            )
        return candidates

    def lookup_lei(self, lei: str) -> dict[str, object] | None:
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/lei-records/{lei}",
            provider="gleif",
        )
        data = payload.get("data")
        if data is None:
            return None
        if not isinstance(data, dict):
            raise ProviderInvalidResponse("gleif: data must be an object")
        attributes = data.get("attributes")
        if not isinstance(attributes, dict):
            raise ProviderInvalidResponse("gleif: attributes missing")
        return attributes

    def _lei_from_record(self, payload: dict[str, object]) -> str | None:
        data = payload.get("data")
        if isinstance(data, dict):
            attributes = data.get("attributes")
            if isinstance(attributes, dict):
                lei = attributes.get("lei")
                return lei if isinstance(lei, str) else None
        return None

    def lookup_relationships(self, lei: str) -> dict[str, object]:
        """Return the direct parent LEI and direct child LEIs (both free GLEIF endpoints).

        GLEIF returns 404 when no parent/children exist — that is a normal absence,
        not an error, and yields an empty result rather than a failure.
        """

        def fetch(path: str) -> dict[str, object] | None:
            try:
                response = self.client.get(f"{self.base_url}/lei-records/{lei}/{path}")
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                raise ProviderUnavailable("gleif: request unavailable") from exc
            if response.status_code == 404:
                return None  # no such relationship — a normal absence
            if response.status_code == 429:
                raise ProviderUnavailable("gleif: rate limited")
            if response.status_code >= 500:
                raise ProviderUnavailable(f"gleif: upstream unavailable ({response.status_code})")
            try:
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise ProviderInvalidResponse("gleif: invalid relationship response") from exc
            return payload if isinstance(payload, dict) else None

        parent_payload = fetch("direct-parent")
        parent_lei = self._lei_from_record(parent_payload) if parent_payload else None

        children_payload = fetch("direct-children")
        child_leis: list[str] = []
        if children_payload is not None:
            data = children_payload.get("data")
            if isinstance(data, list):
                for record in data:
                    if isinstance(record, dict):
                        attributes = record.get("attributes")
                        if isinstance(attributes, dict) and isinstance(attributes.get("lei"), str):
                            child_leis.append(str(attributes["lei"]))
        return {"parent_lei": parent_lei, "child_leis": child_leis}
