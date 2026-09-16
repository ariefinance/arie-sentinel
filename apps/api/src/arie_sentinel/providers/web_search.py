"""Adapter for an approved structured web/news search endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from .base import ProviderInvalidResponse, RetrievedPage, WebResult
from .http import request_json


class StructuredWebSearchProvider:
    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0) -> None:
        self.base_url = base_url
        self.client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
            follow_redirects=True,
        )

    def search(self, query: str) -> list[WebResult]:
        payload = request_json(
            self.client,
            "GET",
            self.base_url,
            provider="web_search",
            params={"q": query},
        )
        rows = payload.get("results")
        if not isinstance(rows, list):
            raise ProviderInvalidResponse("web_search: results missing")
        retrieved = datetime.now(UTC).isoformat()
        output: list[WebResult] = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("url") or not row.get("title"):
                continue
            url = str(row["url"])
            output.append(
                WebResult(
                    title=str(row["title"]),
                    url=url,
                    excerpt=str(row.get("content") or row.get("snippet") or ""),
                    retrieved_at=retrieved,
                    publisher=str(row.get("publisher") or urlparse(url).netloc),
                    published_at=str(row["published_at"]) if row.get("published_at") else None,
                )
            )
        return output

    def retrieve(self, url: str) -> RetrievedPage | None:
        """Keep live results discovery-only until a connection-pinned egress service exists.

        Validating DNS and then letting the HTTP client resolve again is vulnerable to
        rebinding. Returning no capture is the fail-closed Phase 1 boundary.
        """
        return None
