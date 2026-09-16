"""Shared defensive HTTP behavior for live provider adapters."""

from __future__ import annotations

from typing import Any

import httpx

from .base import ProviderInvalidResponse, ProviderRateLimited, ProviderUnavailable


def request_json(
    client: httpx.Client, method: str, url: str, *, provider: str, **kwargs: Any
) -> dict[str, Any]:
    try:
        response = client.request(method, url, **kwargs)
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise ProviderUnavailable(f"{provider}: request unavailable") from exc
    if response.status_code == 429:
        raise ProviderRateLimited(f"{provider}: rate limited")
    if response.status_code in {401, 403}:
        raise ProviderUnavailable(f"{provider}: credentials unavailable or rejected")
    if response.status_code >= 500:
        raise ProviderUnavailable(f"{provider}: upstream unavailable ({response.status_code})")
    try:
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderInvalidResponse(f"{provider}: invalid response") from exc
    if not isinstance(payload, dict):
        raise ProviderInvalidResponse(f"{provider}: response must be an object")
    return payload
