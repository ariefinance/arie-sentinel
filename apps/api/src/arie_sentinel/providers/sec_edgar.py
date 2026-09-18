"""SEC EDGAR adapter — free, no API key (identifying User-Agent required).

Applies only to US SEC-registered entities. Absence of an EDGAR record is NEVER
evidence that a company is not genuine — most companies are simply not SEC filers.
Full-text search endpoint: https://efts.sec.gov/LATEST/search-index?q=...
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .base import ProviderInvalidResponse
from .http import request_json

_USER_AGENT = "ARIE Sentinel counterparty-integrity (compliance@ariefinance.com)"


@dataclass(frozen=True)
class EdgarRecord:
    name: str
    cik: str | None
    tickers: tuple[str, ...] = ()


class SecEdgarProvider:
    def __init__(self, base_url: str = "https://efts.sec.gov", timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            timeout=timeout, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
        )

    def search_company(self, name: str) -> list[EdgarRecord]:
        """Return EDGAR entities matching a name (discovery/corroboration, US only)."""
        payload = request_json(
            self.client,
            "GET",
            f"{self.base_url}/LATEST/search-index",
            provider="sec_edgar",
            params={"q": name},
        )
        hits = payload.get("hits")
        if hits is None:
            return []
        if not isinstance(hits, dict):
            raise ProviderInvalidResponse("sec_edgar: hits must be an object")
        inner = hits.get("hits")
        if not isinstance(inner, list):
            raise ProviderInvalidResponse("sec_edgar: hits.hits must be a list")
        records: list[EdgarRecord] = []
        for hit in inner:
            source = hit.get("_source") if isinstance(hit, dict) else None
            if not isinstance(source, dict):
                continue
            display = source.get("display_names")
            names = display if isinstance(display, list) and display else [source.get("name")]
            first = names[0] if names else None
            if not isinstance(first, str):
                continue
            cik = source.get("cik")
            tickers = source.get("tickers")
            records.append(
                EdgarRecord(
                    name=first,
                    cik=str(cik) if cik is not None else None,
                    tickers=tuple(str(t) for t in tickers) if isinstance(tickers, list) else (),
                )
            )
        return records
