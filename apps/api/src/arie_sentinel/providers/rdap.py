"""RDAP-first domain registration adapter."""

from __future__ import annotations

import httpx

from .base import DomainRecord
from .http import request_json


class RdapDomainProvider:
    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    def lookup(self, domain: str) -> DomainRecord | None:
        norm = domain.strip().lower().rstrip(".")
        payload = request_json(
            self.client, "GET", f"{self.base_url}/domain/{norm}", provider="rdap"
        )
        events = {
            str(item.get("eventAction")): str(item.get("eventDate"))
            for item in payload.get("events", [])
            if isinstance(item, dict) and item.get("eventAction") and item.get("eventDate")
        }
        nameservers = tuple(
            str(item["ldhName"]).lower()
            for item in payload.get("nameservers", [])
            if isinstance(item, dict) and item.get("ldhName")
        )
        registrar = None
        for entity in payload.get("entities", []):
            if isinstance(entity, dict) and "registrar" in entity.get("roles", []):
                registrar = str(entity.get("handle") or "registrar")
                break
        return DomainRecord(
            domain=str(payload.get("ldhName") or norm).lower(),
            registered_on=events.get("registration"),
            updated_on=events.get("last changed"),
            expires_on=events.get("expiration"),
            registrar=registrar,
            nameservers=nameservers,
            statuses=tuple(str(v) for v in payload.get("status", [])),
            source_ref=str(payload.get("links", [{}])[0].get("href"))
            if payload.get("links")
            else f"{self.base_url}/domain/{norm}",
        )
