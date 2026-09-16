# Phase 1 deployment and controlled-pilot reference

**Status: Implementation complete — awaiting production provider configuration and controlled pilot.**

Sentinel is an internal analyst-assistance tool. It is not production-ready and
is not a regulatory screening system of record. Use public or synthetic subjects
until ARIE has approved the providers, identity configuration, deployment, and
pilot controls below.

## Management-demo deployment

The temporary management demo uses `ARIE_ENV=demo`, fixture providers, development
role headers, and an explicit frontend build setting of
`VITE_AUTH_MODE=development`. Its public frontend ingress is protected with HTTP
Basic Authentication; the API, worker, and PostgreSQL remain private. Credentials
and the generated `BASIC_AUTH_HTPASSWD` value belong in the deployment platform's
secret store and must never be committed.

After management approval, reuse the deployed service layout and convert it in
place: make the repository private, configure approved live-provider credentials,
connect the production OIDC client and API validation settings, set
`ARIE_ENV=production`, `ARIE_PROVIDER_MODE=live`, and `VITE_AUTH_MODE=production`,
then pass the production safety gate below before any controlled live case.

## Production configuration

All values are runtime environment variables. Store secrets in the deployment
platform's secret manager, never in Git or a container image. The authoritative
placeholder set is [`.env.example`](../.env.example).

### Application

| Variable | Required | Purpose |
|---|---:|---|
| `ARIE_ENV=production` | Yes | Enables production safety validation and disables development identity handling. |
| `ARIE_DATABASE_URL` | Yes | Non-development PostgreSQL connection using the `postgresql+psycopg://` driver. |
| `ARIE_CORS_ORIGINS` | Yes | Comma-separated HTTPS origins allowed to call the API. Wildcards, credentials, paths, queries, and fragments are rejected. |
| `ARIE_LOG_LEVEL` | No | Runtime log level; defaults to `info`. |
| `ARIE_PROVIDER_MODE=live` | Yes | Selects live adapters. Fixture mode is rejected in production. |
| `ARIE_PROVIDER_TIMEOUT_SECONDS` | No | External-provider timeout; defaults to 15 seconds. |

### Authentication

| Variable | Required | Purpose |
|---|---:|---|
| `ARIE_DEV_AUTH=false` | Yes | Development headers are rejected in production. |
| `ARIE_OIDC_ISSUER` | Yes | Exact trusted token issuer. |
| `ARIE_OIDC_AUDIENCE` | Yes | Expected Sentinel API audience. |
| `ARIE_OIDC_JWKS_URL` | Yes | HTTPS JWKS endpoint used for signature validation. |
| `ARIE_OIDC_ROLES_CLAIM` | No | Claim holding Sentinel roles; defaults to `roles`. |
| `ARIE_OIDC_ANALYST_ROLE` | No | Analyst role value; defaults to `sentinel-analyst`. |
| `ARIE_OIDC_MANAGER_ROLE` | No | Manager role value; defaults to `sentinel-manager`. |

The frontend has a token-provider interface but deliberately contains no invented
identity SDK. ARIE must supply the approved IdP client integration that calls
`configureTokenProvider`; the provider must keep tokens in memory and return the
analyst or manager role. Production API requests fail before network access when
no bearer token is available.

All configured OIDC and external-provider endpoints must be valid HTTPS URLs in
production. Plain HTTP configuration fails application startup.

### Corporate intelligence

| Variable | Required | Purpose |
|---|---:|---|
| `ARIE_OPENCORPORATES_BASE_URL` | Yes | OpenCorporates API root. |
| `ARIE_OPENCORPORATES_API_KEY` | Provider-dependent | API credential when issued/required for ARIE's approved access. |
| `ARIE_GLEIF_BASE_URL` | Yes | GLEIF API root used only for LEI enrichment. |

### Screening

| Variable | Required | Purpose |
|---|---:|---|
| `ARIE_OPENSANCTIONS_BASE_URL` | Yes | OpenSanctions API root. |
| `ARIE_OPENSANCTIONS_API_KEY` | Yes for screening | Matching API credential; absence is recorded as source unavailable. |
| `ARIE_OPENSANCTIONS_DATASET` | No | Dataset selector; defaults to `default`. |

### Web/news

| Variable | Required | Purpose |
|---|---:|---|
| `ARIE_WEB_SEARCH_PROVIDER` | No | Adapter label; currently `structured`. |
| `ARIE_WEB_SEARCH_BASE_URL` | Yes for web discovery | Approved endpoint returning structured search results. |
| `ARIE_WEB_SEARCH_API_KEY` | Provider-dependent | Credential for the approved search endpoint. |

Search results are discovery leads only. Live underlying-page retrieval remains
disabled until deployment provides connection-pinned egress that closes DNS
rebinding/TOCTOU risk. Search snippets never become authoritative evidence.

### RDAP and GLEIF

| Variable | Required | Purpose |
|---|---:|---|
| `ARIE_RDAP_BASE_URL` | Yes | RDAP bootstrap/proxy endpoint for claimed company domains only. |
| `ARIE_GLEIF_BASE_URL` | Yes | GLEIF endpoint; no application credential is currently consumed. |

## Provider readiness

| Provider | Purpose | Credentials required | Licence/approval required | Current code status |
|---|---|---|---|---|
| OpenCorporates | Company candidates and registry attributes | API key when required by approved access | **ARIE ACTION REQUIRED** — confirm access, permitted use, and retention terms | Live adapter implemented and tested |
| OpenSanctions | Sanctions/PEP matching | API key required | **ARIE ACTION REQUIRED** — approve the appropriate business licence and datasets | Matching adapter implemented; missing key fails safely |
| GLEIF | LEI identity enrichment | None consumed by current adapter | **ARIE ACTION REQUIRED** — confirm intended use and retention against current terms | Live enrichment adapter implemented and tested |
| RDAP | Registration metadata for claimed company domains | None consumed by current adapter | **ARIE ACTION REQUIRED** — approve selected endpoint and acceptable-use limits | Live adapter implemented and restricted to claimed domains |
| Structured web/news search | Discovery of public sources | Endpoint and provider credential as applicable | **ARIE ACTION REQUIRED** — select/approve provider and its use/retention terms | Vendor-neutral adapter implemented; page retrieval remains fail-closed |

## Deployment layout and commands

The smallest supported layout is four services on one private network:

- `frontend`: static Vite build served by an unprivileged Nginx container;
- `api`: one FastAPI process, reachable from the frontend as `/api`;
- `worker`: the same backend image running the PostgreSQL-backed job worker;
- `postgres`: PostgreSQL 16 with durable storage (prefer an ARIE-managed database).

TLS terminates at the approved ingress. Only the frontend is internet/user
reachable; PostgreSQL and the worker remain private. The API may remain private
behind the frontend proxy. The API and worker must use the same environment and
database. No Redis or separate broker is required.

```bash
# Build the exact application images
docker build -t arie-sentinel-api:phase1 apps/api
docker build -t arie-sentinel-web:phase1 apps/web

# Apply schema before API/worker rollout
docker run --rm --env-file .env arie-sentinel-api:phase1 \
  uv run --no-sync alembic upgrade head

# API (image default)
docker run --env-file .env arie-sentinel-api:phase1

# Worker (same image and configuration)
docker run --env-file .env arie-sentinel-api:phase1 \
  uv run --no-sync python -m arie_sentinel.jobs.worker
```

For a single-host controlled environment, `compose.pilot.yml` expresses the
same topology and a persistent PostgreSQL volume. The frontend binds to
`127.0.0.1:8080` by default. Set `POSTGRES_PASSWORD` and all `.env` values
outside Git, set `ARIE_DATABASE_URL` to the private database address, validate
with `docker compose -f compose.pilot.yml config`, then start with
`docker compose -f compose.pilot.yml up -d --build`. Exposing Sentinel beyond
the host requires an approved TLS ingress/reverse proxy; override
`SENTINEL_BIND_ADDRESS` only for that controlled ingress configuration. API,
worker, and PostgreSQL ports are never published by this Compose definition.

The API health check is `GET /health`; it verifies database connectivity. The
frontend build has no runtime configuration other than the same-origin `/api`
proxy. ARIE's approved frontend auth integration must be bundled before building
the production image.

Persistent requirements are the PostgreSQL data volume/backups and the external
secret configuration. Provider raw responses are not persisted by Phase 1.

## Production safety gate

Before any real ARIE case, verify all items and retain the deployment record:

- [ ] Repository has been made private.
- [ ] `ARIE_ENV=production`, `ARIE_DEV_AUTH=false`, and `ARIE_PROVIDER_MODE=live`.
- [ ] OIDC issuer, audience, JWKS URL, role claim, and role mappings are approved and tested.
- [ ] Frontend uses the approved in-memory token provider; no token is committed or hard-coded.
- [ ] `ARIE_DATABASE_URL` targets the backed-up non-development PostgreSQL service.
- [ ] Provider endpoints, credentials, licences, and retention constraints are approved.
- [ ] No fixture fallback, real case data, production URL, or secret exists in Git.
- [ ] Logs contain no bearer tokens, API keys, database credentials, or provider payloads.
- [ ] Live page retrieval is disabled and web snippets remain discovery-only.
- [ ] Migration, health check, worker processing, final report, backup, and restore are exercised.

Production startup rejects development authentication, fixture provider mode,
the default development database, incomplete OIDC configuration, HTTP external
endpoints, and unsafe CORS origins. CI also starts the packaged PostgreSQL,
migration, API, worker, and frontend stack and verifies both direct API health
and `/api/health` routing through the frontend proxy before removing containers
and volumes.

## Controlled-pilot matrix

Use only the repository's fictional fixtures or a compliance-approved public
test identity. Do not commit pilot outputs or captured provider data.

| Case | Test subject | Expected focus | Required verification |
|---|---|---|---|
| 1. Clear company + clean screening | Fictional single-candidate company with a contact that produces no match | Confirmed legal identity and completed zero-match screening | Entity resolution, source/retrieval dates, `NO_MATERIAL_MATCH`, relationship state, limitations, findings, audit, PDF |
| 2. Ambiguous company | Fictional `Vantar Energy Trading` fixture | Analyst must choose among jurisdictions; no auto-confirmation | Candidate distinctions, provenance, blocked report before selection, audit, final PDF after resolution |
| 3. Known sanctions/PEP | Compliance-approved public provider test identity selected at pilot time | Potential match only; no automatic confirmation | Matched identifiers/datasets, provenance, human disposition and rationale, audit, PDF |
| 4. Officer/contact relationship | Public or fictional registry record with same normalized officer name and company identifier | Registry verifies the recorded relationship, not physical identity | Relationship basis and cautious wording, provenance, limitations, findings, audit, PDF |
| 5. Relationship not established | Fictional resolved company plus unmatched contact | Explicitly unverified relationship | No invented identity, limitation/follow-up finding, provenance, audit, PDF |
| 6. Provider unavailable | Deterministic unavailable-provider fixture | Investigation remains usable with a recorded limitation | `SOURCE_UNAVAILABLE`, partial evidence, findings, audit history, PDF wording |
| 7. Zero screening matches | Deterministic clean-screening fixture | Completed screening is not confused with outage | `NO_MATERIAL_MATCH`, source status, limitations, audit, PDF wording |
| 8. Potential screening match | Fictional `Amara` fixture or approved provider test identity | Analyst review required | Potential-match basis, identifiers, disposition controls, rationale, audit, PDF |

For every case, capture pass/fail and reviewer initials outside this public
repository. A failed safety, provenance, audit, or report check blocks real-case
use until remediated.

## Management demo runbook (5–10 minutes)

1. Sign in as an analyst and enter a fictional Company + Contact.
2. Show candidate legal entities and explain why a name alone is not confirmed.
3. Select the correct fictional candidate and record a rationale.
4. Show the investigation returning immediately while the worker enriches it.
5. Open Company and show value, source, retrieval date, and match basis.
6. Open Person and explain the limited meaning of registry-name corroboration.
7. Open Screening and contrast zero matches, unavailable screening, and a potential match.
8. Open the evidence drawer to demonstrate provenance and source limitations.
9. Review Findings and the explicit unknowns/follow-up items.
10. Switch to manager context, deliberately confirm finalisation, and open the PDF report.

End by stating that analyst judgement remains required, external-provider access
is not yet approved in this repository, and Sentinel is not the regulatory
screening system of record.
