# Free data-source matrix — Counterparty Intelligence Workbench

Phase policy: **no paid providers on the live path.** Broad free evidence collection,
narrow defensible conclusions. Every source below was assessed for current availability,
authentication, free/commercial-use suitability, and authoritative-vs-discovery status.
This environment's network egress is restricted, so live endpoint behaviour was **not**
exercised end-to-end from here; provider schemas were verified via docs/web search and the
adapters + parsers are unit-tested against representative samples. Live end-to-end
validation against the production endpoints is a controlled-pilot step, not this PR.

## What the live path actually uses (no paid defaults)

Company discovery is routed by `FreeRegistryRouter` (`providers/free_registry.py`) to
**free authoritative sources only**:

- **GB** → UK Companies House (free key) as the PRIMARY authoritative registry.
- **any jurisdiction** → GLEIF legal-name search (`gleif.py: search_by_name`) for
  LEI-registered entities. An empty result is "no LEI located" (an absence), never a
  nonexistence finding and never fabricated.
- **US** → SEC EDGAR is corroboration-only (consumed in enrichment), NOT a discovery
  registry.
- **other jurisdictions with no GLEIF hit** → an explicit `RegistryCoverageUnavailable`
  coverage limitation. The router **never** silently falls back to a paid provider and
  **never** fabricates a confirmation from web search.

When no free authoritative registry coverage or candidate exists, legal identity stays
**NOT_VERIFIED** and **no Counterparty is created**, but the investigation does **not** stop:
the safe checks that do not require a resolved legal entity still run against the supplied
label + intake claims — website/RDAP, public-web discovery, GDELT news discovery, sanctions
name screening (with an explicit unresolved-identity caveat), and the contradictions that do
not need authoritative registry facts. This keeps Sentinel useful for SMEs outside GB and
outside the LEI population (e.g. Mauritius/Africa/UAE) without ever confirming identity or
inventing a jurisdiction, and without treating website data as registry evidence.

Screening uses `OfficialSanctionsProvider` backed by a local cache of the official
government feeds — **no paid OpenSanctions/OpenCorporates default anywhere on the live
path**.

| Source | Free for internal business use? | Key required? | Classification | Status in this PR | What it provides |
| --- | --- | --- | --- | --- | --- |
| **GLEIF** (LEI) | Yes (open data, CC0) | No | Authoritative | **Integrated** (`gleif.py`): free legal-name **discovery** (`search_by_name`, any jurisdiction) AND LEI enrichment; direct parent/child relationships retrieved (`lookup_relationships`) and shown as PARENT_OF edges | LEI, legal name/address, jurisdiction, status, direct parent/child LEIs |
| **UK Companies House Public Data API** | Yes | **Yes — free key** (`ARIE_COMPANIES_HOUSE_API_KEY`) | Authoritative (UK) | **Integrated + tested** (`companies_house.py`): primary GB discovery; enrichment consumes profile + status + incorporation + address + **officers** + **PSC** (`get_psc`). No key ⇒ source unavailable (never "no company") | UK company record, status, incorporation, address, officers, persons with significant control |
| **RDAP** (domains) | Yes | No | Authoritative (registration metadata) | **Integrated** (`rdap.py`), driven by the analyst-entered website (intake claim). A claimed website is CLAIMED, never CORROBORATED without an independent RDAP registration | Domain existence, registrar, creation/expiry, status, nameservers |
| **SEC EDGAR** | Yes | No (identifying User-Agent required) | Authoritative (US filers only) | **Integrated** (`sec_edgar.py`): US-jurisdiction corroboration only; a failure is a SUPPLEMENTARY limitation, not a material-source failure; absence never adverse | US SEC entity name/CIK/tickers |
| **GDELT 2.0 Doc API** | Yes | No | **Discovery only** | **Integrated** (`gdelt.py`): discovery leads (never authoritative, never auto-adverse); a failure is a SUPPLEMENTARY limitation, not a material-source failure | Public-news leads (publisher, title, seen date, url) |
| **OFAC / UN / UK / EU** (official free sanctions feeds) | Yes (official government) | No | Authoritative (sanctions) | **Ingested end-to-end** (`sanctions.py`, `sanctions_feeds.py`, `services/sanctions_cache.py`): per-feed XML parsers, PostgreSQL cache (`SanctionsRecord` + `SanctionsFeedState`, migration `0004`), scheduled refresh (`python -m arie_sentinel.jobs.refresh_sanctions`), coverage-gated screening. Parsers unit-tested against representative samples; live download validation is a pilot step | Sanctions entities + identifiers (aliases, DOB, nationality, ids) |
| **OpenCorporates API** | No (commercial licence for business use) | Yes | — | **Rejected + removed from the live path** (paid). The adapter remains only for parity/tests; `build_providers` never selects it | — |
| **OpenSanctions API / bulk** | **No** for our use — free for non-commercial only | Yes | — | **Rejected** (licence-incompatible for internal ARIE use); official primary feeds are ingested instead | — |

## Official sanctions feeds — formats and cache semantics

| Feed | Endpoint (default) | Format | Required by default? |
| --- | --- | --- | --- |
| OFAC | Treasury Sanctions List Service `SDN.XML` | XML (`sdnEntry`) | Yes |
| UN | UN Security Council consolidated list | XML (`INDIVIDUAL`/`ENTITY`) | Yes |
| UK | **UK Sanctions List (FCDO)** — `https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml` (`Designation` records) | XML | Yes |
| EU | EU Financial Sanctions Files (FSF) `sanctionEntity` | XML | No — optional (the FSF download typically needs a token; parser implemented, URL left unset by default) |

**The UK OFSI Consolidated List has closed**; the **UK Sanctions List** published by the
FCDO at `https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml` is now the sole UK
designation source. The retired OFSI `ConsolidatedList` element layout is still accepted by
the parser for continuity, and a config test guards against regressing the URL to the
retired `assets.publishing.service.gov.uk/.../uk_sanctions_list.xml` asset path.

**Cache & refresh (`services/sanctions_cache.py`):** `refresh_feeds` downloads, parses, and
atomically replaces each feed's cached records, recording per-feed state
(`ok`/`failed`/`never_refreshed`, last success, entity count). A failed refresh **retains**
the previously cached records (never empties the cache). No Redis / Celery / external cache —
just PostgreSQL and a plain runnable process.

**Fail closed on empty parse:** for a *required* feed (OFAC/UN/UK), a download that
succeeds but parses to **zero** usable entities (a schema change or truncated/placeholder
file) is treated as a **failed** refresh — the previous cache is retained, the feed is
marked failed, coverage stays incomplete, and `NO_MATERIAL_MATCH` cannot be asserted. A
non-empty result is the sanity condition (no list sizes are hardcoded).

**Coverage semantics:** screening only reports **NO_MATERIAL_MATCH** when every *required*
feed is present and fresh (within `ARIE_SANCTIONS_CACHE_MAX_AGE_HOURS`, default 168h). With
incomplete coverage, a clearance is **not** asserted — a limitation is recorded instead —
while any positive hit still surfaces as a **POTENTIAL_MATCH** for analyst review. Matches
are **never** auto-confirmed.

## Materiality: material vs supplementary sources

A **supplementary** source outage (GDELT discovery, SEC US corroboration, GLEIF LEI
enrichment, Companies House officer/PSC sub-calls) records a `COMPLETE_WITH_LIMITATIONS`
coverage limitation and never downgrades the whole case to `MATERIAL_SOURCE_UNAVAILABLE`.
Genuinely material outages (registry discovery, the resolved GB registry profile, screening)
remain material.

## Evidence coverage (board)

The Evidence-coverage row distinguishes four states: assessment in progress
(`NOT_ASSESSED`), completed with no evidence retained (`UNVERIFIED`), completed with
evidence (`REPORTED`), and material source unavailable (`SOURCE_UNAVAILABLE`). Zero
collection errors is **not** reported as confirmed coverage.

## Reusable OSS components

### rigour
Status: **INTEGRATED**
Purpose: name/identifier normalization and fuzzy matching support (used in
`providers/normalization.py` and the sanctions matcher — legal-form-aware name keys,
ASCII/transliteration folding, LEI validation/normalization, Levenshtein similarity).
Licence: MIT. Data dependency: none. (It is the same normalization library used by yente.)
Fuzzy name similarity can only ever produce a POTENTIAL_MATCH — never a CONFIRMED_MATCH —
and a conflicting date of birth suppresses obvious false positives.

### yente
Status: **REFERENCE / FUTURE BENCHMARK**
Purpose: mature entity-matching API.
Why not deployed now: it requires OpenSearch/Elasticsearch infrastructure, OpenSanctions
data licensing is separate/commercial, and it is unnecessary operational complexity for the
current free-only, operationally-simple phase.

### ArchiveBox
Status: **NEXT-PHASE OPTIONAL INTEGRATION**
Purpose: preserve public webpages used as investigation evidence.

### Aleph
Status: **REFERENCE ONLY**
Reason: a full investigative platform is excessive; the Sentinel core remains appropriate.

(ArchiveBox / Aleph / yente are **not** integrated in this PR.)

## Rejected categories

Abandoned APIs, scraping proxies, unofficial data mirrors, and any source whose licence
is incompatible with internal ARIE use were not integrated.

## User action required (free key)

The only genuine external action is a **free UK Companies House API key**
(`ARIE_COMPANIES_HOUSE_API_KEY`; register at developer.company-information.service.gov.uk),
because Companies House requires a free account. Sanctions feeds need no key (EU FSF is
optional and left unconfigured by default). Never commit any key.

Sanctions-cache refresh remains available via the operational entrypoint
`python -m arie_sentinel.jobs.refresh_sanctions`. In the Railway demo, the existing
PostgreSQL worker also refreshes the official feeds automatically at most once every
24 hours when `ARIE_SANCTIONS_WORKER_AUTO_REFRESH=true`, avoiding the need for a separate cron
service. No manual scheduling step is required of the operator. Screening treats a
stale/missing/empty required feed as a coverage limitation, not a clearance.

Sources consulted: [Companies House API Catalogue](https://www.api.gov.uk/ch/companies-house/),
[OpenSanctions licensing](https://www.opensanctions.org/licensing/),
UK Sanctions List (GOV.UK), OFAC Sanctions List Service, UN Security Council consolidated
list, EU Financial Sanctions Files.
