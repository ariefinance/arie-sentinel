"""OpenSanctions query-by-example matching adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from .base import ProviderInvalidResponse, ScreeningHit, ScreeningSubject
from .http import request_json


class OpenSanctionsProvider:
    def __init__(
        self, base_url: str, api_key: str, dataset: str = "default", timeout: float = 15.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.dataset = dataset
        self.client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"ApiKey {api_key}"},
            follow_redirects=True,
        )

    def screen(self, subject: ScreeningSubject | str) -> list[ScreeningHit]:
        if isinstance(subject, str):
            subject = ScreeningSubject(label=subject)
        properties: dict[str, list[str]] = {"name": [subject.label, *subject.aliases]}
        if subject.countries:
            properties["country"] = list(subject.countries)
        if subject.birth_dates:
            properties["birthDate"] = list(subject.birth_dates)
        properties.update({key: list(values) for key, values in subject.identifiers.items()})
        payload = request_json(
            self.client,
            "POST",
            f"{self.base_url}/match/{self.dataset}",
            provider="opensanctions",
            params={"algorithm": "best", "limit": "5"},
            json={"queries": {"subject": {"schema": subject.schema, "properties": properties}}},
        )
        response = payload.get("responses", {}).get("subject")
        if not isinstance(response, dict) or not isinstance(response.get("results"), list):
            raise ProviderInvalidResponse("opensanctions: responses.subject.results missing")
        retrieved = datetime.now(UTC).isoformat()
        hits: list[ScreeningHit] = []
        for result in response["results"]:
            if not isinstance(result, dict) or not result.get("id"):
                continue
            raw_props = result.get("properties")
            props: dict[str, object] = raw_props if isinstance(raw_props, dict) else {}
            topics_raw = props.get("topics", [])
            programs_raw = props.get("programId", [])
            topics = [str(v) for v in topics_raw] if isinstance(topics_raw, list) else []
            programs = [str(v) for v in programs_raw] if isinstance(programs_raw, list) else []
            identifiers = {
                key: [str(v) for v in values]
                for key, values in props.items()
                if key
                in {"idNumber", "registrationNumber", "leiCode", "taxNumber", "passportNumber"}
                and isinstance(values, list)
            }
            profile_id = str(result["id"])
            hits.append(
                ScreeningHit(
                    subject_label=subject.label,
                    list_or_source=", ".join(topics or programs or ["OpenSanctions default"]),
                    state="POTENTIAL_MATCH",
                    match_basis=str(result.get("caption") or "provider match"),
                    profile_id=profile_id,
                    score=float(result["score"]) if result.get("score") is not None else None,
                    explanation=(
                        result.get("explanations", {})
                        if isinstance(result.get("explanations"), dict)
                        else {}
                    ),
                    matched_identifiers=identifiers,
                    datasets=tuple(str(v) for v in result.get("datasets", [])),
                    source_ref=f"https://www.opensanctions.org/entities/{profile_id}/",
                    retrieved_at=retrieved,
                )
            )
        return hits
