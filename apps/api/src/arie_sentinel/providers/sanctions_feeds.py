"""Official sanctions feed download + parsing (free government feeds only).

Each parser transforms one official feed's published XML into the normalized
``SanctionedEntity`` model. Parsers are namespace-agnostic (matched on element
local-names) and defensive: a missing optional field is skipped, never guessed.

Feed field mappings target each provider's published schema:
  - OFAC  : Treasury Sanctions List Service SDN.XML (``sdnEntry`` records).
  - UN    : UN Security Council consolidated list (``INDIVIDUAL`` / ``ENTITY``).
  - UK    : UK Sanctions List XML on GOV.UK (``Designation`` records; the retired
            OFSI ``ConsolidatedList`` layout is also accepted for continuity).
  - EU    : EU Financial Sanctions Files (FSF) ``sanctionEntity`` records.

Live end-to-end validation against the production endpoints is a controlled-pilot
step (this environment's egress is restricted); the parsers are unit-tested against
representative samples of each schema.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator

import httpx

from .base import ProviderInvalidResponse, ProviderUnavailable
from .sanctions import SanctionedEntity


def _local(tag: str) -> str:
    """Return an element tag's local name (namespace stripped)."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _iter_local(elem: ET.Element, name: str) -> Iterator[ET.Element]:
    """Yield descendants whose local-name equals ``name`` (namespace-agnostic)."""
    for child in elem.iter():
        if _local(child.tag) == name:
            yield child


def _first_text(elem: ET.Element, *names: str) -> str | None:
    for child in elem.iter():
        if _local(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return None


def _all_text(elem: ET.Element, *names: str) -> list[str]:
    out: list[str] = []
    for child in elem.iter():
        if _local(child.tag) in names and child.text and child.text.strip():
            out.append(child.text.strip())
    return out


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for value in values:
        if value and value not in seen:
            seen[value] = None
    return tuple(seen)


def _parse_xml(payload: bytes, provider: str) -> ET.Element:
    # ElementTree does not resolve external entities, so external-entity injection is
    # not possible here; the download size is capped upstream to bound entity-expansion.
    try:
        return ET.fromstring(payload)
    except ET.ParseError as exc:  # pragma: no cover - exercised via callers
        raise ProviderInvalidResponse(f"{provider}: malformed XML feed") from exc


def parse_ofac_sdn(payload: bytes) -> list[SanctionedEntity]:
    root = _parse_xml(payload, "OFAC")
    entities: list[SanctionedEntity] = []
    for entry in _iter_local(root, "sdnEntry"):
        first = _first_text(entry, "firstName")
        last = _first_text(entry, "lastName")
        name = " ".join(p for p in (first, last) if p).strip()
        if not name:
            continue
        sdn_type = (_first_text(entry, "sdnType") or "").lower()
        entity_type = "person" if sdn_type == "individual" else "entity"
        aliases: list[str] = []
        for aka in _iter_local(entry, "aka"):
            aka_name = " ".join(
                p for p in (_first_text(aka, "firstName"), _first_text(aka, "lastName")) if p
            ).strip()
            if aka_name:
                aliases.append(aka_name)
        dobs = _all_text(entry, "dateOfBirth")
        countries = _all_text(entry, "country")
        ids = _all_text(entry, "idNumber")
        entities.append(
            SanctionedEntity(
                name=name,
                source_list="OFAC",
                entity_type=entity_type,
                aliases=_dedupe(aliases),
                birth_dates=_dedupe(dobs),
                countries=_dedupe(countries),
                identifiers=_dedupe(ids),
                profile_id=_first_text(entry, "uid"),
            )
        )
    return entities


def _un_records(root: ET.Element, container: str, entity_type: str) -> list[SanctionedEntity]:
    out: list[SanctionedEntity] = []
    tag = "INDIVIDUAL" if container == "INDIVIDUALS" else "ENTITY"
    for record in _iter_local(root, tag):
        name = " ".join(
            p
            for p in (
                _first_text(record, "FIRST_NAME"),
                _first_text(record, "SECOND_NAME"),
                _first_text(record, "THIRD_NAME"),
                _first_text(record, "FOURTH_NAME"),
            )
            if p
        ).strip()
        if not name:
            continue
        aliases = _all_text(record, "ALIAS_NAME")
        dobs = _all_text(record, "DATE", "YEAR")
        countries = _all_text(record, "NATIONALITY", "VALUE")
        ids = _all_text(record, "NUMBER")
        out.append(
            SanctionedEntity(
                name=name,
                source_list="UN",
                entity_type=entity_type,
                aliases=_dedupe(aliases),
                birth_dates=_dedupe(dobs),
                countries=_dedupe(countries),
                identifiers=_dedupe(ids),
                profile_id=_first_text(record, "DATAID", "REFERENCE_NUMBER"),
            )
        )
    return out


def parse_un_consolidated(payload: bytes) -> list[SanctionedEntity]:
    root = _parse_xml(payload, "UN")
    return _un_records(root, "INDIVIDUALS", "person") + _un_records(root, "ENTITIES", "entity")


def parse_uk_sanctions(payload: bytes) -> list[SanctionedEntity]:
    root = _parse_xml(payload, "UK")
    entities: list[SanctionedEntity] = []
    # UK Sanctions List (GOV.UK) uses <Designation> records; the retired OFSI
    # consolidated list used the same element name, so both are handled here.
    for designation in _iter_local(root, "Designation"):
        # Prefer a whole-name field (Name6), else assemble the ordered name parts.
        name = _first_text(designation, "Name6")
        if not name:
            parts = []
            for part_tag in ("Name1", "Name2", "Name3", "Name4", "Name5"):
                part = _first_text(designation, part_tag)
                if part:
                    parts.append(part)
            name = " ".join(parts).strip() or _first_text(designation, "Name", "LastName")
        if not name:
            continue
        group_type = (_first_text(designation, "GroupTypeDescription", "GroupType") or "").lower()
        entity_type = "person" if "individual" in group_type else "entity"
        aliases = _all_text(designation, "Alias", "AliasName")
        dobs = _all_text(designation, "DateOfBirth", "DOB")
        countries = _all_text(designation, "Nationality", "Country")
        ids = _all_text(designation, "PassportNumber", "NationalIdNumber", "IdNumber")
        entities.append(
            SanctionedEntity(
                name=name,
                source_list="UK",
                entity_type=entity_type,
                aliases=_dedupe(aliases),
                birth_dates=_dedupe(dobs),
                countries=_dedupe(countries),
                identifiers=_dedupe(ids),
                profile_id=_first_text(designation, "GroupID", "UniqueID", "ReferenceNumber"),
            )
        )
    return entities


def parse_eu_fsf(payload: bytes) -> list[SanctionedEntity]:
    root = _parse_xml(payload, "EU")
    entities: list[SanctionedEntity] = []
    for record in _iter_local(root, "sanctionEntity"):
        subject_type = ""
        for st in _iter_local(record, "subjectType"):
            subject_type = (st.get("code") or st.get("classificationCode") or "").lower()
            break
        entity_type = "person" if "person" in subject_type else "entity"
        names = [n.get("wholeName") for n in _iter_local(record, "nameAlias") if n.get("wholeName")]
        # Assemble a whole name from parts when wholeName is absent.
        if not names:
            for n in _iter_local(record, "nameAlias"):
                assembled = " ".join(
                    p for p in (n.get("firstName"), n.get("lastName")) if p
                ).strip()
                if assembled:
                    names.append(assembled)
        names = [n for n in names if n]
        if not names:
            continue
        primary = names[0]
        aliases = names[1:]
        dobs = [b.get("birthdate") for b in _iter_local(record, "birthdate") if b.get("birthdate")]
        countries = [
            c.get("countryDescription") or c.get("countryIso2Code") or ""
            for c in _iter_local(record, "citizenship")
        ]
        ids = [d.get("number") for d in _iter_local(record, "identification") if d.get("number")]
        entities.append(
            SanctionedEntity(
                name=str(primary),
                source_list="EU",
                entity_type=entity_type,
                aliases=_dedupe([str(a) for a in aliases]),
                birth_dates=_dedupe([str(b) for b in dobs if b]),
                countries=_dedupe([c for c in countries if c]),
                identifiers=_dedupe([str(i) for i in ids if i]),
                profile_id=record.get("euReferenceNumber") or record.get("logicalId"),
            )
        )
    return entities


PARSERS = {
    "OFAC": parse_ofac_sdn,
    "UN": parse_un_consolidated,
    "UK": parse_uk_sanctions,
    "EU": parse_eu_fsf,
}


def download_feed(client: httpx.Client, url: str, max_bytes: int) -> bytes:
    """Stream a feed with a hard byte cap; raise ProviderUnavailable on any outage."""
    try:
        with client.stream("GET", url) as response:
            if response.status_code == 429:
                raise ProviderUnavailable(f"sanctions feed rate limited: {url}")
            if response.status_code >= 400:
                raise ProviderUnavailable(
                    f"sanctions feed unavailable ({response.status_code}): {url}"
                )
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise ProviderInvalidResponse(f"sanctions feed exceeds size cap: {url}")
                chunks.append(chunk)
            return b"".join(chunks)
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise ProviderUnavailable(f"sanctions feed unreachable: {url}") from exc


def parse_feed(name: str, payload: bytes) -> list[SanctionedEntity]:
    parser = PARSERS.get(name)
    if parser is None:
        raise ProviderInvalidResponse(f"unknown sanctions feed: {name}")
    return parser(payload)
