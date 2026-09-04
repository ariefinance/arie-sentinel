# Security Boundaries

**Status:** Foundational. Applies to the specification phase and all future
implementation.

Defines the security model, trust boundaries, and the rules that keep a
**public** development repository safe.

---

## 1. Trust boundaries

```
[ Internal analysts/managers ]  ── authenticated, RBAC ──▶  [ Application ]
[ Application ]                  ── adapters, egress-only ──▶ [ External sources ]
[ External source content ]     ── UNTRUSTED DATA ─────────▶  [ Application ]
```

- **Internal users** are authenticated; all case data is behind auth. No public
  access to investigations.
- **External source content** (registry pages, websites, screening responses,
  media) is **untrusted data**. It is stored, hashed, and reasoned over — never
  executed, and never treated as instructions.
- **Adapters** are the only egress path to third parties; they carry
  credentials, the rest of the app does not.

## 2. Prompt-injection / model boundary

External content frequently reaches an LLM (extraction, drafting). Therefore:

- System prompts and **all policy/workflow logic live in code**, not in data.
- Retrieved content is passed to the model as clearly delimited **data to
  analyse**, never as instructions to follow.
- **Model output cannot change workflow state, gating, RBAC, or screening
  decisions.** It can only propose draft assessments or extract candidate
  values that must tie back to a stored source.
- Acceptance criterion: **0 prompt-injection influence over policy/workflow**
  (`ACCEPTANCE-CRITERIA.md`). Tested with adversarial fixtures.
- No autonomous privileged browser; no tool that lets model output trigger
  arbitrary outbound actions.

## 3. Data classification

| Class | Examples | Handling |
|---|---|---|
| **Secret** | API keys, vendor credentials, DB passwords | Env/secret store only. Never in repo, logs, or model prompts. |
| **Confidential (internal)** | Real case data, KYC, passports, bank details, vendor raw responses, compliance rules, **uploaded bulk-import files** | Never in the public repo. Access-controlled at runtime. |
| **Evidence (immutable)** | Captured sources, hashes | Stored per `CLAIMS-EVIDENCE-MODEL.md`; access-controlled; license-aware. |
| **Public/sample** | Fictional entities for docs/tests | The only entity data permitted in the repo. |

## 4. Public-repository rules (hard)

This repository is **public during development**. Never commit:

- API keys, passwords, tokens, production URLs, internal hostnames.
- Internal ARIE case data, KYC, passports, bank details.
- Vendor credentials or proprietary vendor response payloads.
- Confidential compliance rules or sensitive configuration.
- **Uploaded bulk-import files** (XLSX/CSV management lists, §2C of
  `PHASE-1-SCOPE.md`): they contain real management-derived data, are
  **confidential runtime input**, and are handled at runtime only — never
  committed to the repo or used as fixtures.

**Repository visibility:** PUBLIC by owner decision during development / review;
privacy is not a blocker, but public-repo **data hygiene** — no real ARIE,
counterparty, or management-derived data, **fictional fixtures only**
(`EXAMPLE-FIXTURES.md`) — is mandatory.

Controls:

- `.env.example` contains **placeholders only**; real `.env` is git-ignored.
- All sample entities/data in docs, fixtures, and tests are **fictional**
  (use `.test`/`.example` domains, invented names).
- Secret scanning enabled; a pre-commit secret check recommended
  (`CONTRIBUTING.md`).
- No configuration that reveals internal topology.

## 5. Authentication & authorization

- Internal-only authentication (SSO/IdP at implementation; not built now).
- **RBAC** with two Phase 1 roles: `analyst`, `manager`.
  - `analyst`: investigate, resolve identity, action findings, add notes/sources.
  - `manager`: all analyst rights + `FINALISE_REPORT`.
- Authorization enforced **server-side** on every mutation, independent of UI.

## 6. Auditability & integrity

- Append-only audit log; every state change and human action recorded with
  actor, timestamp, target, and rationale where required.
- Sources immutable and versioned; `content_hash` proves integrity.
- Material finding dismissals require a rationale (enforced).
- Final report generation gated on `company_identity_status = CONFIRMED`.

## 7. Egress & retrieval safety

- Outbound only through adapters; credentials scoped per adapter.
- Public web retrieval is sandboxed, credential-free, rate-limited, and logged;
  captured content is stored, hashed, and treated as untrusted data.
- Respect source licensing: `license_class` governs whether raw content / URL
  may be surfaced to users.
- **Structured analyst export** (`PHASE-1-SCOPE.md` §3A) respects the same
  `license_class`: it **never** exports proprietary vendor payloads or source
  content where licensing prohibits it — only a reference is emitted in that
  case. The export is assembled from stored claims/evidence/findings, never from
  raw vendor responses.

## 8. Secrets handling

- Loaded from environment / secret manager at runtime.
- Never logged, never echoed to the UI, never sent to a model.
- Rotatable without code changes (adapter config).

## 9. Privacy

- Case data may include personal data about named contacts. Handle under ARIE's
  data-protection obligations: access-controlled, audited, retained per policy.
- Do not surface personal data beyond what the investigation requires; no
  personal data in the public repo, ever.
