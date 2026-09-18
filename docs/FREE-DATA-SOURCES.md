# Free data-source matrix — Counterparty Intelligence Workbench

Phase policy: **no paid providers.** Broad free evidence collection, narrow defensible
conclusions. Every source below was assessed for current availability, authentication,
free/commercial-use suitability, and authoritative-vs-discovery status. This
environment's network egress is restricted, so live endpoint behaviour was **not**
exercised from here; terms were verified via provider docs / web search where reachable
and are cited. Live verification is part of the controlled-pilot step, not this PR.

| Source | Free for internal business use? | Key required? | Classification | Status in this PR | What it provides |
| --- | --- | --- | --- | --- | --- |
| **GLEIF** (LEI) | Yes (open data, CC0) | No | Authoritative | **Integrated** (`gleif.py`): LEI record used in enrichment; **direct parent/child relationships now retrieved** (`lookup_relationships`) and shown as PARENT_OF edges | LEI, legal name/address, jurisdiction, status, registration authority, direct parent/child LEIs |
| **RDAP** (domains) | Yes | No | Authoritative (registration metadata) | **Integrated** (`rdap.py`), now also driven by the analyst-entered website (intake claim) | Domain existence, registrar, creation/expiry, status, nameservers (privacy-redacted fields respected) |
| **SEC EDGAR** | Yes | No (identifying User-Agent required) | Authoritative (US filers only) | **Integrated** (`sec_edgar.py`): consumed by enrichment for US-jurisdiction entities; absence never treated as adverse | US SEC entity name/CIK/tickers |
| **GDELT 2.0 Doc API** | Yes | No | **Discovery only** | **Integrated** (`gdelt.py`): consumed by enrichment as discovery leads (never authoritative, never auto-adverse); retrieval time is Sentinel's fetch time, seen-date is provenance | Public-news leads (publisher, title, seen date, url) |
| **UK Companies House Public Data API** | Yes | **Yes — free key** (register at developer.company-information.service.gov.uk; ~600 req/5 min) | Authoritative (UK) | **Adapter built + tested** (`companies_house.py`), consumed by enrichment for GB entities when a key is configured; no key ⇒ source unavailable (never "no company") | UK company record, status, incorporation, address, officers, PSC |
| **OFAC / UN / UK OFSI / EU** (official free feeds) | Yes (official government) | No | Authoritative (sanctions) | **Matching engine shipped + tested** (`sanctions.py`): normalized model + identifier-aware matcher + fail-closed provider. **Live per-feed download + PostgreSQL cache + scheduled refresh is the remaining wiring** (formats: OFAC SDN XML/CSV, UN consolidated XML, UK OFSI CSV, EU XML) | Sanctions entities + identifiers (aliases, DOB, nationality, ids) |
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
