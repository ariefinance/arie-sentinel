"""GDELT adapter — free, no API key. Public-news DISCOVERY only, never authoritative.

Returns discovery leads (publisher, title, date, url) for analyst/context review. A
generic negative-keyword hit is NOT confirmed adverse information.
GDELT 2.0 Doc API: https://api.gdeltproject.org/api/v2/doc/doc?query=...&format=json
"""

from __future__ import annotations

import httpx

from .base import ProviderInvalidResponse, WebResult
from .http import request_json

_USER_AGENT = "ARIE Sentinel counterparty-integrity (compliance@ariefinance.com)"


class GdeltNewsProvider:
    def __init__(
        self, base_url: str = "https://api.gdeltproject.org", timeout: float = 15.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            timeout=timeout, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
        )

    def search(self, query: str, *, max_records: int = 25) -> list[WebResult]:
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/api/v2/doc/doc",
            provider="gdelt",
            params={
                "query": query,
                "mode": "artlist",
                "format": "json",
                "maxrecords": str(max_records),
                "sort": "datedesc",
            },
        )
        articles = payload.get("articles")
        if articles is None:
            return []
        if not isinstance(articles, list):
            raise ProviderInvalidResponse("gdelt: articles must be a list")
        results: list[WebResult] = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            url = article.get("url")
            title = article.get("title")
            if not isinstance(url, str) or not isinstance(title, str):
                continue
            seen = article.get("seendate")
            results.append(
                WebResult(
                    title=title,
                    url=url,
                    excerpt="",  # GDELT returns metadata only; snippet is not evidence
                    retrieved_at=seen if isinstance(seen, str) else "",
                    publisher=article.get("domain")
                    if isinstance(article.get("domain"), str)
                    else None,
                )
            )
        return results
