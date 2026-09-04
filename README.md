# ARIE Sentinel — Phase 1: Counterparty Integrity Engine

Given a **company name** and a **contact person**, Sentinel establishes who the
counterparty legally is, whether the named person is credibly connected to it,
what public and screening intelligence exists, and where claims and evidence
disagree — then produces a single, auditable **Counterparty Integrity Report**
that an analyst can understand in about two minutes.

Repository: `ariefinance/arie-sentinel`

---

> ## STATUS: Specification frozen · Build Stage 1 in progress
>
> The Phase 1 specification (in [`docs/`](docs/)) is the **frozen baseline**.
> Implementation is proceeding in controlled stages (see
> [`docs/BUILD-PLAN.md`](docs/BUILD-PLAN.md)). **Build Stage 1** establishes the
> application foundation and the Counterparty Integrity data spine in
> [`apps/api`](apps/api) (and the frontend shell in `apps/web`).
> **Interaction / IA is frozen; visual design is subject to rendered review.**
> The repository is **public by owner decision** during development — public-repo
> data hygiene (fictional fixtures only) is mandatory.

---

## What Sentinel is

Sentinel is a **case-investigation workspace** for counterparty due diligence.
It surfaces evidence and contradictions so a human analyst can decide; it is
**not** an analytics dashboard and **not** a decision engine. It reports what
authoritative sources show, what the counterparty claims, where the two diverge,
and what to do next — always in **evidence-based language**, never as a
subjective character judgment about a company or person.

For each case Sentinel is designed to establish: the exact legal entity and its
registration status; directors/ownership where obtainable; evidence about the
named person; the company↔person and company↔domain relationships;
sanctions/PEP/adverse-intelligence results; material public intelligence;
claims-vs-evidence contradictions; research limitations; required verification
actions; and the assembled, auditable Counterparty Integrity Report. Identity
resolution is a **gate**: if a company name resolves to more than one plausible
legal entity, the investigation pauses for analyst disambiguation and final
report generation is blocked.

## What Phase 1 explicitly excludes

The following are **out of scope for Phase 1** and must not appear in code,
schema, navigation, report sections, or UI copy:

- Transaction-chain analysis
- Oil/gas (or any) mandate verification
- Vessels / cargo / logistics
- Payment-release decisions
- Transaction-authority determinations
- Financial-capacity or credit scoring
- Document-forgery claims / authenticity adjudication
- Continuous / ongoing monitoring
- Any other Phase 2 functionality

See [`docs/PHASE-1-SCOPE.md`](docs/PHASE-1-SCOPE.md) for the authoritative scope
and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how these boundaries are
kept clean through adapter and claim-type extensibility **without** building any
of the above now.

## Architecture in one paragraph

Sentinel is a **modular monolith** (not microservices) with **PostgreSQL** as
the single relational store of record for cases, claims, evidence, findings, and
an append-only audit log. Evidence is **immutable and versioned**: raw source
payloads live in an **object store** referenced by content hash, while
structured evidence is held in Postgres, with immutability enforced at the
database level. Investigations run as **asynchronous jobs** on a Postgres-backed
queue (no Redis/broker in Phase 1). All external dependencies — corporate
registry, screening, domain/RDAP, sandboxed web retrieval, and the LLM — sit
behind narrow, swappable **adapters**, and the **model is isolated**: LLM output
is never evidence by itself and can never change workflow state, gating, or
screening decisions. There is **no graph database** and **no vendor lock-in**;
framework and vendor choices are deliberately deferred to the first build PR.

## Documentation index

All specification lives in [`docs/`](docs/).

| Document | Description |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System shape, data layer, adapters, model isolation, and the Technical Challenge Log of accepted/modified/deferred/rejected decisions. |
| [`docs/PHASE-1-SCOPE.md`](docs/PHASE-1-SCOPE.md) | Frozen scope: the one-sentence definition, inputs, deliverables, exclusions, and language-safety rules. Source of truth for all other specs. |
| [`docs/CLAIMS-EVIDENCE-MODEL.md`](docs/CLAIMS-EVIDENCE-MODEL.md) | The claims/evidence/findings data model and the structurally enforced truth boundary (source fact vs claim vs assessment). |
| [`docs/SECURITY-BOUNDARIES.md`](docs/SECURITY-BOUNDARIES.md) | Trust boundaries, prompt-injection/model boundary, data classification, and public-repository secret-hygiene rules. |
| [`docs/ACCEPTANCE-CRITERIA.md`](docs/ACCEPTANCE-CRITERIA.md) | Testable acceptance criteria for Phase 1, including identity-resolution gating and prompt-injection resistance. |
| [`docs/BUILD-PLAN.md`](docs/BUILD-PLAN.md) | Sequenced implementation plan; gates the transition from specification to code. |
| [`docs/UI-UX-SPEC.md`](docs/UI-UX-SPEC.md) | End-to-end UI/UX specification for the case workspace. |
| [`docs/INFORMATION-ARCHITECTURE.md`](docs/INFORMATION-ARCHITECTURE.md) | Navigation, case structure, and how deliverables map to screens and report sections. |
| [`docs/USER-FLOWS.md`](docs/USER-FLOWS.md) | Analyst and manager task flows, including the identity-resolution gate and report finalisation. |
| [`docs/DESIGN-SYSTEM.md`](docs/DESIGN-SYSTEM.md) | Visual and interaction design system, provenance styling, and evidence-based language patterns. |
| [`docs/SCREEN-STATES.md`](docs/SCREEN-STATES.md) | Canonical screen and case-state enums; the authoritative terminology every other document must match. |
| [`docs/COMPONENT-INVENTORY.md`](docs/COMPONENT-INVENTORY.md) | Inventory of UI components and their states, mapped to the design system. |
| [`docs/COMPETITIVE-UX-PATTERN-AUDIT.md`](docs/COMPETITIVE-UX-PATTERN-AUDIT.md) | Audit of mature financial-crime/KYC investigation products; proven patterns adopted/rejected and the bounded UX corrections applied to the spec. |
| [`docs/EXAMPLE-FIXTURES.md`](docs/EXAMPLE-FIXTURES.md) | The single canonical set of fictional example data used across all docs. No real ARIE/counterparty/management-derived data may appear anywhere in this repo. |

## Public repository safety

This repository is **public during development**. Treat everything committed as
world-readable and permanent.

- **Never commit secrets** — API keys, passwords, tokens, vendor credentials,
  production URLs, or internal hostnames. Secrets load from the environment or a
  secret manager at runtime only.
- **Never commit real or confidential data** — internal ARIE case data, KYC,
  passports, bank details, confidential compliance rules, or proprietary vendor
  response payloads.
- **`.env.example` contains placeholders only.** The real `.env` is
  git-ignored and must never be committed.
- **All sample data is fictional** — use `.test`/`.example` domains and invented
  names in every doc, fixture, and test. Fictional entities are the only entity
  data permitted in this repository.
- Enable **GitHub secret scanning** and run a **pre-commit secret check** (see
  `CONTRIBUTING.md`).

See [`docs/SECURITY-BOUNDARIES.md`](docs/SECURITY-BOUNDARIES.md) for the full
security model.

## Technical stack (decided)

Backend: Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 · Alembic ·
PostgreSQL · PostgreSQL-backed jobs. Frontend: React · TypeScript · Vite ·
TanStack Query. Report: Jinja2 → WeasyPrint. Full rationale in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §9 (Technical Challenge Log).

## Development (Build Stage 1)

Prerequisites: Python 3.12 (with [`uv`](https://docs.astral.sh/uv/)), Node 22
(with `pnpm`), and a local PostgreSQL 16.

```bash
# 1) Postgres (dev role + database)
createuser arie --createdb 2>/dev/null || true    # password: arie (dev only)
createdb -O arie arie_sentinel

# 2) Backend (locked dependencies)
cd apps/api
uv sync --frozen --extra dev                      # installs from uv.lock into .venv
cp .env.example .env                              # placeholders only; never commit .env
export ARIE_DATABASE_URL="postgresql+psycopg://arie:arie@localhost:5432/arie_sentinel"
uv run alembic upgrade head                        # create schema + integrity guards
uv run uvicorn arie_sentinel.main:app --reload     # http://localhost:8000  (/health, /docs)

# 2b) Background worker (processes discovery jobs; run in a separate shell)
uv run python -m arie_sentinel.jobs.worker

# 3) Backend quality gates
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest

# 4) Frontend
cd ../web
pnpm install
pnpm dev                                          # http://localhost:5173 (proxies /api -> :8000)
pnpm lint && pnpm exec tsc --noEmit && pnpm test && pnpm build
```

The app uses a clearly-isolated **development identity** (send `X-Dev-Role:
analyst|manager`); the production **OIDC** boundary is explicit but not wired in
Stage 1. All example data is fictional (`docs/EXAMPLE-FIXTURES.md`).
