"""Adapter for an approved structured web/news search endpoint."""

from __future__ import annotations

import hashlib
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as ResolverTimeoutError
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from .base import ProviderInvalidResponse, RetrievedPage, WebResult
from .http import request_json

_ALLOWED_CONTENT_TYPES = {"text/html", "text/plain", "application/xhtml+xml"}
_MAX_RESPONSE_BYTES = 1_000_000
_MAX_REDIRECTS = 3
_DNS_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sentinel-dns")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.parts.append(data.strip())


def _validate_public_url(url: str, timeout: float) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Only unauthenticated HTTP(S) URLs are permitted")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Local hosts are not permitted")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        literal_address = ipaddress.ip_address(hostname)
    except ValueError:
        resolution = _DNS_EXECUTOR.submit(socket.getaddrinfo, hostname, port, 0, socket.SOCK_STREAM)
        try:
            address_info = resolution.result(timeout=max(timeout, 0.1))
        except ResolverTimeoutError as exc:
            resolution.cancel()
            raise ValueError("DNS resolution timed out") from exc
        addresses = {item[4][0] for item in address_info}
    else:
        addresses = {str(literal_address)}
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Only publicly routable targets are permitted")


def _extract_text(body: bytes, content_type: str, encoding: str | None) -> str:
    text = body.decode(encoding or "utf-8", errors="replace")
    if content_type == "text/plain":
        return " ".join(text.split())
    parser = _TextExtractor()
    parser.feed(text)
    return " ".join(parser.parts)


class StructuredWebSearchProvider:
    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
            follow_redirects=True,
        )
        self.page_client = httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            headers={
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
                "User-Agent": "ARIE-Sentinel/1.0 public-source-retriever",
            },
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
        """Capture one discovered page with SSRF, redirect, type and size controls."""
        current = url
        try:
            for redirect_count in range(_MAX_REDIRECTS + 1):
                _validate_public_url(current, self.timeout)
                with self.page_client.stream("GET", current) as response:
                    if response.is_redirect:
                        if redirect_count == _MAX_REDIRECTS or not response.headers.get("location"):
                            return None
                        current = urljoin(current, response.headers["location"])
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if content_type not in _ALLOWED_CONTENT_TYPES:
                        return None
                    length = response.headers.get("content-length")
                    if length and int(length) > _MAX_RESPONSE_BYTES:
                        return None
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > _MAX_RESPONSE_BYTES:
                            return None
                content = _extract_text(bytes(body), content_type, response.encoding)
                if not content:
                    return None
                return RetrievedPage(
                    url=current,
                    content=content,
                    content_hash=hashlib.sha256(body).hexdigest(),
                    content_type=content_type,
                    retrieved_at=datetime.now(UTC).isoformat(),
                )
        except (httpx.HTTPError, OSError, ValueError):
            return None
        return None
