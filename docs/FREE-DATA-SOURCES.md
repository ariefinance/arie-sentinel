# Free data-source matrix — Counterparty Intelligence Workbench

Phase policy: **no paid providers.** Broad free evidence collection, narrow defensible
conclusions. Every source below was assessed for current availability, authentication,
free/commercial-use suitability, and authoritative-vs-discovery status. This
environment's network egress is restricted, so live endpoint behaviour was **not**
exercised from here; terms were verified via provider docs / web search where reachable
and are cited. Live verification is part of the controlled-pilot step, not this PR.

| Source | Free for internal business use? | Key required? | Classification | Status in this PR | What it provides |
| --- | --- | --- | --- | --- | --- |
| **GLEIF** (LEI) | Yes (open data, CC0) | No | Authoritative | **Integrated** (`gleif.py`, existing; used in enrichment) | LEI, legal name, legal/HQ address, jurisdiction, entity status, registration authority, parent/child links |
| **RDAP** (domains) | Yes | No | Authoritative (registration metadata) | **Integrated** (`rdap.py`, existing) | Domain existence, registrar, creation/expiry, status, nameservers (privacy-redacted fields respected) |
| **SEC EDGAR** | Yes | No (identifying User-Agent required) | Authoritative (US filers only) | **Adapter shipped + tested** (`sec_edgar.py`); enrichment consumption is the next increment | US SEC entity name/CIK/tickers. Absence is never treated as adverse. |
| **GDELT 2.0 Doc API** | Yes | No | **Discovery only** | **Adapter shipped + tested** (`gdelt.py`); enrichment consumption is the next increment | Public-news leads (publisher, title, date, url). A keyword hit is not confirmed adverse info. |
| **UK Companies House Public Data API** | Yes | **Yes — free key** (register at developer.company-information.service.gov.uk; ~600 req/5 min) | Authoritative (UK) | **Adapter-ready** (documented; one free-key step in §"User action") | UK company record, status, incorporation, address, officers, PSC, filing history |
| **OFAC SDN / Consolidated** | Yes (US Treasury official) | No | Authoritative (sanctions) | **Deferred — feed identified** (SDN XML/CSV); normalizer into `ScreeningResult` is the next increment | US sanctions entities + identifiers (aliases, DOB, nationality, ids) |
| **UN Security Council Consolidated List** | Yes (official) | No | Authoritative (sanctions) | **Deferred — feed identified** (consolidated XML) | UN sanctions entities + identifiers |
| **UK OFSI Consolidated List** | Yes (official) | No | Authoritative (sanctions) | **Deferred — feed identified** (CSV/HTML) | UK sanctions entities + identifiers |
| **EU Consolidated Financial Sanctions** | Yes (official; token-gated public download) | Sometimes (free) | Authoritative (sanctions) | **Deferred — feed identified** (XML) | EU sanctions entities + identifiers |
| **OpenCorporates API** | No (commercial licence for business use) | Yes | — | **Rejected this phase** (paid) | — |
| **OpenSanctions API / bulk** | **No** for our use — free for non-commercial only; businesses must license | Yes | — | **Rejected this phase** (licence-incompatible for internal ARIE use); ingest official primary feeds instead | — |

## Why official sanctions feeds instead of an aggregator

OpenSanctions aggregates OFAC/UN/UK/EU but is free **only for non-commercial** users;
internal ARIE use is commercial and requires a licence. The underlying government
lists are themselves free and authoritative, so Sentinel should ingest those primary
feeds directly and normalize them into the existing `ScreeningResult` model (matching
on aliases, DOB, nationality and identifiers where present — never name-only), with
potential matches routed to analyst review and never an automated "clearance".

## Rejected categories

Abandoned APIs, scraping proxies, unofficial data mirrors, and any source whose licence
is incompatible with internal ARIE use were not integrated.

## User action required (free key)

Only one free credential is needed to activate a fully-built adapter (UK Companies
House). See `docs/DEMO-REMEDIATION.md`-style handoff in the PR body. Never commit the key.

Sources consulted: [Companies House API Catalogue](https://www.api.gov.uk/ch/companies-house/),
[OpenSanctions licensing](https://www.opensanctions.org/licensing/),
[OpenSanctions consolidated dataset](https://www.opensanctions.org/datasets/sanctions/).
