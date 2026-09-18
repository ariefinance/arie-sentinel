"""GLEIF LEI enrichment adapter."""

from __future__ import annotations

import httpx

from .base import ProviderInvalidResponse, ProviderUnavailable
from .http import request_json


class GleifProvider:
    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

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
