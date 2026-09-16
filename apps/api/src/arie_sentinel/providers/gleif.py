"""GLEIF LEI enrichment adapter."""

from __future__ import annotations

import httpx

from .base import ProviderInvalidResponse
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
