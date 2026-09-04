# Architecture

**Status:** Foundational. Framework choices are *proposed with rationale*, not
frozen; data model and boundaries are frozen.

This document describes the smallest professional architecture capable of
building Sentinel Phase 1, and records — in the **Technical Challenge Log**
(§10) — where the brief's technical assumptions were accepted, modified,
deferred, or rejected. Nothing here scaffolds the application; it defines
boundaries so implementation does not force a rewrite.

---

## 1. Architectural principles (accepted from brief)

- **PostgreSQL first.** Single relational store of record.
- **Immutable / versioned evidence.** See `CLAIMS-EVIDENCE-MODEL.md`.
- **Asynchronous investigation jobs.** Investigations are long-running and
  I/O-bound (external lookups); they run as background jobs.
- **Adapter-based vendor integrations.** All external data behind interfaces.
- **Model isolation.** LLM access behind an adapter; output is never evidence.
- **Strict auditability.** Append-only audit log; versioned sources.
- **No graph database.** Relational is sufficient (see §10).
- **No vendor lock-in.** Adapters + open store formats.
- **No privileged autonomous browser.** No headless browser with credentials
  acting autonomously; retrieval is explicit, sandboxed, and logged.
- **AI output is never evidence by itself.**

---

## 2. System shape (logical)

```
                    ┌──────────────────────────────┐
   Analyst  ───────▶│  Web UI (case workspace)     │
                    └──────────────┬───────────────┘
                                   │ HTTP/JSON (authn + RBAC)
                    ┌──────────────▼───────────────┐
                    │  Application API             │
                    │  - investigation orchestration│
                    │  - claims/evidence/findings  │
                    │  - human-review actions       │
                    │  - report assembly            │
                    └───────┬───────────────┬──────┘
                            │ enqueue        │ read/write
                    ┌───────▼──────┐  ┌──────▼───────────────┐
                    │  Job runner  │  │  PostgreSQL          │
                    │ (async workers)│ │  - investigations,       │
                    │              │  │    claims, evidence,   │
                    │              │  │  - audit (append-only)│
                    └───┬───────┬──┘  └──────────────────────┘
                        │       │                 ▲
             ┌──────────▼─┐ ┌───▼──────────┐      │ content_ref
             │ Adapters   │ │ Model adapter│  ┌───┴────────────┐
             │ (registry, │ │ (LLM behind  │  │ Object store    │
             │  screening,│ │  isolation)  │  │ (raw source     │
             │  RDAP, web)│ └──────────────┘  │  payloads,      │
             └────────────┘                   │  immutable)     │
                                              └─────────────────┘
```

Deliberately a **modular monolith**, not microservices (§10). One deployable
application with clear internal module boundaries: `intake`, `identity`,
`enrichment`, `screening`, `evidence`, `findings`, `report`, `audit`, `adapters`.

---

## 3. Data layer

- **PostgreSQL** is the store of record for all structured data
  (`CLAIMS-EVIDENCE-MODEL.md`).
- **Raw source payloads** (HTML snapshots, API responses, registry documents)
  are stored in an **object store** (S3-compatible / filesystem in dev),
  referenced by `content_ref` + `content_hash`. Rationale: keep large,
  immutable blobs out of the transactional DB; hash gives integrity + dedupe.
- **Immutability** is enforced by (a) application never issuing UPDATE on source
  content columns, and (b) a DB-level guard (revoked UPDATE privilege or a
  BEFORE UPDATE trigger) on those columns.
- **Audit log** is append-only (INSERT-only role; no UPDATE/DELETE).

## 4. Asynchronous investigation jobs

- **Bulk list import** (`PHASE-1-SCOPE.md` §2C) is an ingest job that reads an
  uploaded **XLSX/CSV** file and **fans out one Investigation per row**. Each
  resulting Investigation then runs the **same job graph** below — there is no
  separate, gate-skipping path for bulk rows.
  - **Malformed-row isolation:** a row that cannot be parsed/validated is
    recorded as a failed import item and skipped; it never aborts the file or
    corrupts sibling rows.
  - **Idempotency:** each row carries an **import row hash** (over its
    normalised source cells); a re-import of the same row does **not** create a
    duplicate Investigation, and repeated organisations still link to the
    existing shared Counterparty on `identity_key` (never on label similarity).
  - Non-Phase-1 commercial columns are stored as non-evidentiary `case_context`,
    never as sources/claims/evidence.
- An investigation is a **job graph**: **intake quality gate → normalisation →
  candidate discovery → legal entity resolution** → (company enrichment ∥ person
  enrichment ∥ domain ∥ screening) → finding synthesis → completeness
  assessment.
- The **intake quality gate** runs first and is a hard branch: if it returns
  `CLARIFICATION_REQUIRED`, **no downstream step runs** — no normalisation, no
  web/AI discovery, no counterparty creation. The investigation waits for more
  input. This prevents manufacturing a likely entity from a poor label
  (`TBD`, `Unnamed Refinery`). It is distinct from the `AMBIGUOUS` outcome of
  resolution.
- **Candidate discovery** produces candidate counterparties and **0..N
  PersonCandidates** from the raw `contact_label`; it never destructively
  rewrites the raw labels.
- **Legal entity resolution** matches/creates a shared **Counterparty** on
  authoritative `identity_key` (registry identity), never on label similarity,
  so a repeated organisation across management rows links to the existing
  counterparty (`CLAIMS-EVIDENCE-MODEL.md` §2.7).
- Each step is idempotent and records its own sources/evidence.
- A step that cannot complete sets a partial state (`PARTIAL_RESULTS`,
  `SOURCE_UNAVAILABLE`) rather than failing the whole investigation.
- **Queue/runner:** start with a Postgres-backed job queue (e.g.
  `SELECT … FOR UPDATE SKIP LOCKED`) — no extra infrastructure, transactional
  with the data it produces. Introduce Redis/dedicated broker **only if**
  throughput demands it (deferred; see §10). This avoids standing up Redis for
  Phase 1 volumes.

## 5. Adapter architecture

Every external dependency sits behind a narrow, typed interface. Adapters:

- return **normalised evidence + a stored source** (never leak vendor payload
  shapes upward);
- declare their `source_class`, `license_class`, and `limitations`;
- are individually testable with recorded fixtures (deterministic tests);
- are swappable (e.g. `ScreeningProvider` today ComplyAdvantage-style, tomorrow
  LSEG) with no change to callers.

Phase 1 interfaces (define now, implement one real impl each + a fixture/mock):

- `CorporateRegistryProvider`
- `ScreeningProvider` (sanctions / PEP / adverse media)
- `DomainRegistrationProvider` (RDAP-first, WHOIS fallback)
- `WebIntelligenceProvider` (sandboxed public retrieval)
- `ModelProvider` (LLM; isolated; drafting/extraction only)

> We define the interfaces but **do not** implement five providers each. One
> real + one fixture per interface (brief §20 "design for change").

**Provider-aware adverse-media event grouping.** Where the `ScreeningProvider`
(or adverse-media provider) supplies its own **event grouping / clustering**,
the adapter **consumes and preserves it** as normalised evidence — Sentinel does
**not** build its own clustering engine. If a provider supplies none, the
requirement is to **measure duplicate noise first** and only then consider a
**lightweight** dedup layer. This is a **provider-aware requirement**, not a
commitment to build a clustering engine (§10, Revision 4).

**Structured analyst export** (`PHASE-1-SCOPE.md` §3A) is **assembled from
stored claims / evidence / findings** — the same store the report is built from
— not from raw vendor payloads. It is **licensing-aware**: it honours each
source's `license_class` and emits only a reference where raw content or URL may
not be surfaced. No proprietary vendor payload leaves the boundary.

## 6. Model isolation

- LLMs are used for: extracting candidate claims/values from retrieved text,
  drafting assessment prose, and clustering candidate entities during identity
  resolution.
- LLMs are **not** used to: decide policy, decide report gating, assign
  screening matches, or produce facts without a source.
- Every model call is behind `ModelProvider`, logged, and its output is written
  as **evidence only when tied to a real source**; otherwise it is a draft
  `assessment_text` a human edits/approves.
- **Prompt-injection defence:** retrieved external content is treated as data,
  never as instructions. System prompts and policy are fixed in code; model
  output cannot change workflow state or gating. This is an acceptance
  criterion (0 prompt-injection influence over policy/workflow).

## 7. AuthN / AuthZ

- Authenticated internal users only (no public access to case data).
- **RBAC**, two roles for Phase 1: `analyst` and `manager` (management/review).
  Analysts investigate and action findings; managers additionally finalise.
- Every mutating action is authorised server-side and written to the audit log
  with actor identity. RBAC is enforced in the API, not the UI.

## 8. Observability & error handling

- Structured logging with correlation by `investigation_id` and `job_id`.
- Adapter failures are typed and surfaced as investigation states
  (`SOURCE_UNAVAILABLE`), never swallowed.
- No secrets in logs; external payloads referenced by hash, not inlined into
  application logs.

## 9. Technical stack (DECIDED — build-readiness gate)

Framework choice was deferred during specification; it is now **decided** for
implementation. Bias: mature, boring, well-supported, low operational overhead,
easy for humans and Claude to maintain. No microservices, no Kubernetes, no
graph DB, no Redis (PostgreSQL-backed jobs suffice for Phase 1 volumes).

| Concern | Decision | Why (justification) |
|---|---|---|
| **Backend / API** | **Python 3.12 + FastAPI** | Async-first (I/O-bound adapters), Pydantic v2 validation built in, first-class Postgres ecosystem, Python-first model/extraction libraries. Boring and ubiquitous. |
| **DB access / ORM** | **SQLAlchemy 2.0 (typed)** | Mature, explicit, powerful; typed models; no lock-in to a thin wrapper. |
| **Migrations** | **Alembic** | Canonical with SQLAlchemy; autogenerate + reviewable migrations; up/down in CI. |
| **Background jobs** | **PostgreSQL-backed queue** (`SELECT … FOR UPDATE SKIP LOCKED`), via **procrastinate** | Postgres-native (no broker), transactional with the data it produces. `procrastinate` is a maintained Postgres-only task lib; a hand-rolled SKIP LOCKED worker is the trivial fallback. Redis only if throughput ever demands it. |
| **Object storage** | **S3-compatible via `boto3`** behind a small `ObjectStore` interface; **filesystem** impl for dev (or MinIO) | Immutable raw payloads keyed by `content_ref` + `content_hash`; one interface, swappable; no blobs in the transactional DB. |
| **AuthN** | **OIDC against the internal IdP** (`authlib`) + signed secure session cookies; dev stub IdP | Internal users only; no bespoke auth; standard, reviewable. |
| **AuthZ / RBAC** | **Two roles** (`analyst`, `manager`) enforced by a FastAPI dependency on every mutation | Server-side, UI-independent; no external policy engine for two roles. |
| **Validation / schema** | **Pydantic v2** | Ships with FastAPI; one validation model end-to-end. |
| **Frontend** | **React + TypeScript + Vite** (SPA) + **TanStack Query** for server state; accessible primitives (semantic HTML + Radix UI where needed) | Internal auth-gated desktop tool → an SPA is simpler than SSR; no heavy client-state lib. Strong a11y tooling. *(This supersedes the earlier "server-render capability" note — SSR is not required for an internal tool; recorded as a justified simplification.)* |
| **Report generation** | **Jinja2 HTML template → PDF via WeasyPrint** | Report assembled from stored data (not free-form); pure-Python HTML→PDF, **no headless browser** (aligns with the no-privileged-browser rule). |
| **XLSX / CSV** | **openpyxl** (XLSX read/write) + stdlib **csv** | Mature, dependency-light; used for both bulk import and structured export. |
| **Audit log** | **Append-only Postgres table**, INSERT-only role, written in the same transaction as the mutation | No extra infra; integrity by construction. |
| **Testing** | Backend **pytest** (+ httpx test client, dockerised Postgres for integration); Frontend **Vitest** + React Testing Library; **Playwright** for E2E + axe a11y | Deterministic; fixture-driven; covers the acceptance harness (`EXAMPLE-FIXTURES.md`). |
| **Lint / format / types** | Backend **ruff** + **mypy**; Frontend **eslint** + **prettier** + **tsc** | Fast, standard, CI-enforced. |
| **Secrets / config** | **Pydantic Settings** from environment / secret manager; `.env` git-ignored; `.env.example` placeholders | Rotatable without code change; nothing secret in the repo. |

**Frozen regardless of the above:** the data model, adapter boundaries,
async-job semantics, audit/immutability rules, and the interaction/IA design.

**UX freeze distinction (build-readiness gate):**
**INTERACTION / IA: FROZEN.** **VISUAL DESIGN: SUBJECT TO RENDERED REVIEW** once
the first real UI exists (`UI-UX-SPEC.md`, `DESIGN-SYSTEM.md`).

### Provider strategy (build without waiting on vendor contracts)
Define the five interfaces now (`CorporateRegistryProvider`,
`ScreeningProvider`, `DomainRegistrationProvider`, `WebIntelligenceProvider`,
`ModelProvider`) and build against **deterministic fixtures/mocks**, with a real
implementation only where it is free and public:
- `DomainRegistrationProvider` — **real RDAP** (public, structured) + fixtures.
- `CorporateRegistryProvider` — **fixtures/mock** (a public register may be
  wired later); real vendor swaps in behind the interface.
- `ScreeningProvider` — **mock** (deterministic synthetic hits); real vendor later.
- `WebIntelligenceProvider` — sandboxed public retrieval + fixtures.
- `ModelProvider` — real model behind the isolation boundary (§6), or a
  deterministic stub in tests.
Simple, explicit interfaces — **no plugin framework**. Real providers replace
mocks without touching the core.

---

## 10. TECHNICAL CHALLENGE LOG

Classification: **ACCEPT** (sound as proposed) · **MODIFY** (better approach) ·
**DEFER** (premature to decide/build) · **REJECT** (technically inappropriate).

| # | Assumption | Verdict | Reasoning / action |
|---|---|---|---|
| 1 | **PostgreSQL** as primary store | **ACCEPT** | Relational fits claims/evidence/findings with FKs and constraints; gives transactional integrity, JSONB for flexible values, and easy audit. No reason to look further. |
| 2 | **Immutable / versioned evidence** | **ACCEPT (with mechanism)** | Correct and essential for auditability. Added concrete mechanism: object store for raw payloads + `content_hash` + DB-level UPDATE guard, rather than relying on convention alone. |
| 3 | **Asynchronous workers** | **ACCEPT** | Investigations are long, I/O-bound, partially-failing — async is right. |
| 4 | **Redis/dedicated broker for the queue** (implied) | **DEFER** | Not stated but commonly assumed. For Phase 1 volumes a **Postgres-backed queue** (`FOR UPDATE SKIP LOCKED`) removes an entire piece of infrastructure and is transactional with the data. Introduce a broker only on demonstrated throughput need. |
| 5 | **Adapter architecture** | **ACCEPT (narrowed)** | Keep interfaces narrow and normalise at the boundary. Implement **one real + one fixture** per interface — do not build multiple providers speculatively. |
| 6 | **Model isolation** | **ACCEPT (hardened)** | Kept behind `ModelProvider`; added explicit rule that model output is evidence only when tied to a stored source, and cannot mutate workflow/gating (prompt-injection boundary). |
| 7 | **Source storage strategy** | **MODIFY** | Store structured evidence in Postgres, **raw payloads in an object store** keyed by hash — avoids bloating the transactional DB with large immutable blobs while preserving integrity. |
| 8 | **Claims/evidence schema** | **ACCEPT** | Small, additive, enum-extensible; enforces the truth boundary structurally. Phase 2 claim types deliberately absent. |
| 9 | **Audit architecture** | **ACCEPT (append-only)** | Single append-only audit table, INSERT-only role, rationale required for material dismissals. |
| 10 | **Graph database** | **REJECT (Phase 1)** | Relationships are shallow and bounded; relational join tables model them cleanly. A graph DB adds operational cost and lock-in for no Phase 1 benefit. Revisit only if network-style ownership analysis becomes a real requirement (Phase 2+). |
| 11 | **Microservices** | **REJECT (Phase 1)** | Team/scale do not justify distributed complexity. **Modular monolith** with clear module boundaries gives the same separation without the ops burden, and can be split later along existing seams. |
| 12 | **Domain / RDAP integration** | **ACCEPT (RDAP-first)** | Prefer RDAP (structured, rate-friendly) with WHOIS fallback. Behind `DomainRegistrationProvider`. |
| 13 | **Screening integration** | **ACCEPT (interface-first)** | Single `ScreeningProvider` interface; one implementation now, LSEG/others later without caller changes. Screening states never auto-decide; matches route to human review. |
| 14 | **Grok / specific LLM integration** | **MODIFY → DEFER vendor** | Do not hard-wire a named model. Use `ModelProvider`; pick the concrete model at build time. Avoids lock-in and keeps model swappable. |
| 15 | **Authentication / RBAC** | **ACCEPT (scoped)** | Internal-only, two roles (`analyst`, `manager`) for Phase 1. Do not build fine-grained permissioning before it's needed. |
| 16 | **Report generation** | **ACCEPT (assembled, gated)** | Report is assembled from stored claims/evidence/findings (not free-form LLM). Generation gated on `company_identity_status = CONFIRMED`. |
| 17 | **Frontend/backend framework commitment** | **DEFER** | Do not freeze FastAPI/Next.js now. Freeze the *boundaries* (data model, adapters, UI/UX spec) so the framework choice is reversible and non-blocking. Decide in the first build PR. |
| 18 | **Public-repository development model** | **ACCEPT (with guardrails)** | Fine for spec + code, given strict secret hygiene: `.env.example` placeholders only, no real case/KYC/vendor data, fictional samples, secret scanning. See `SECURITY-BOUNDARIES.md`. |
| 19 | **Privileged autonomous browser** | **ACCEPT (as prohibition)** | Correctly prohibited. Public retrieval is sandboxed, explicit, credential-free, and logged. |
| 20 | **Numeric AI confidence scores** (implied by "confidence") | **MODIFY** | Avoid vague numeric AI confidence in the UI. Use provenance classes (`authoritative`/`reported`/`inferred`) tied to source class instead — legible and defensible. |

### Revision 2 — real management-data requirements

Raised after management supplied its real client/counterparty list. These are
spec-only changes (no code exists yet); classified per the challenge protocol.

| # | Assumption / requirement | Verdict | Reasoning / action |
|---|---|---|---|
| 21 | Original **one-Case-one-entity** model (embedded `resolved_entity_id`, `company_name_input`) | **MODIFY** | The real data proves labels ≠ identities and one organisation recurs across rows. Split into **Investigation (management record) + shared Counterparty + Person/PersonCandidate**. Impact: **MEDIUM** — spec-only, no approved product behaviour changed, prevents a later migration. Adopted. |
| 22 | **Contact representation** for initials / first names / several people in one field | **MODIFY (chosen design)** | Options weighed: (a) one raw `contact_label` + derived candidate persons; (b) multiple contact-input records; (c) other. Chose **(a)**: keep the single raw label immutable and derive **0..N PersonCandidates**. (b) forces destructive pre-splitting and loses the original combined label; (a) preserves evidence, supports multiplicity, and needs no future migration. |
| 23 | **Intake Quality Gate** as a distinct pre-discovery stage/state | **ACCEPT** | New requirement. `SUFFICIENT_FOR_DISCOVERY` / `CLARIFICATION_REQUIRED` kept **separate** from `AMBIGUOUS`; a poor label never triggers broad web/AI discovery or a manufactured entity. Enforced as a hard branch in the job graph. |
| 24 | **Management commercial context** in the source data | **ACCEPT (guardrailed)** | Retain as non-evidentiary `case_context` (retained-not-analysed), **not** a typed Phase 2 schema. Structurally excluded from Sources/Claims/Evidence and from finding synthesis; internal tiers never become risk ratings; commercial terms not analysed. Prevents Phase 2 leakage while preserving traceability. |
| 25 | **Counterparty identity / dedup key** | **MODIFY** | Match/create counterparties on authoritative `identity_key = f(jurisdiction, registry_id)`, **never** on label string similarity. A repeated organisation links to the existing counterparty; label-only matches must never silently merge. Prevents both duplication and wrong merges. |

### Revision 4 — bulk intake, adverse-media grouping, analyst export

Raised after Phase 1 scope review of intake and output ergonomics. Spec-only
(no code exists yet); classified per the challenge protocol.

| # | Assumption / requirement | Verdict | Reasoning / action |
|---|---|---|---|
| 26 | **Bulk list import** (XLSX/CSV → one Investigation per row) | **ACCEPT** | Matches how management already keeps counterparties. Use the **simplest professional import** (no ETL/mapping platform). Each row runs the **same gates** (no bypass); **malformed-row isolation** and **idempotency via an import row hash** are required. Fan-out is an async ingest job (§4). |
| 27 | **Own adverse-media clustering engine** | **DEFER (provider-aware first)** | Do **not** build a clustering engine. Where the provider supplies event grouping, **consume and preserve** it; otherwise **measure duplicate noise first**, then consider a lightweight dedup layer only if warranted. Recorded as a provider-aware requirement (§5). |
| 28 | **Structured analyst export** (CSV/XLSX evidence & findings register) | **ACCEPT (secondary)** | Assembled from stored claims/evidence/findings; **secondary** to the management report, which stays primary. **Licensing-aware** — never exports proprietary vendor payloads or source content where licensing prohibits (`SECURITY-BOUNDARIES.md`). |
| 29 | **AI-drafted management summary** | **DEFER** | Not a Phase 1 requirement. The report is already concise/structured; a generated summary adds a factual-control + citation-validation surface. Allowed **later only if** report-writing proves a bottleneck — sentence-level cited draft under **mandatory human approval**. Not built/specified now. |
| 30 | **Consolidated REJECT reaffirmation (Phase 1)** | **REJECT** | Reaffirmed out of scope: composite/global **risk score**, **graph database**, **graph-first UI**, **opaque AI conclusions**, **automatic clearance**, **continuous monitoring**, **autonomous acceptance/decline**, and any path that converts **absence of evidence into an adverse judgment** (`PHASE-1-SCOPE.md` §5). |

### Revision 5 — build-readiness gate (decisions locked)

| # | Prior verdict | Now | Action |
|---|---|---|---|
| 14 | Grok/LLM vendor **DEFER** | **DECIDED** | Concrete model chosen at build behind `ModelProvider` (isolation boundary §6); still swappable, still never evidence-by-itself. Locked in §9. |
| 17 | Framework **DEFER** | **DECIDED** | Full stack locked in §9 (FastAPI + SQLAlchemy/Alembic + Postgres-backed jobs + React/TS/Vite SPA + WeasyPrint + openpyxl + ruff/mypy/eslint). SSR dropped for an internal auth-gated SPA (justified simplification). |

**Net position:** the brief's technical spine (Postgres, immutable evidence,
async, adapters, model isolation, audit, no graph DB, no lock-in) is sound and
**accepted**. Main deviations: Postgres-backed queue over a broker (defer
Redis), raw payloads in an object store (modify storage), modular monolith over
microservices, provenance classes over numeric AI confidence, and deferral of
concrete framework/model vendors so the boundaries — not the vendors — are what
we commit to now.
