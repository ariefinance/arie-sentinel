# Build Plan — Phase 1

**Status:** Sequenced implementation plan. Begins **after this specification is
approved**. This is a plan, not code — it defines order, dependencies, the
acceptance criteria each milestone satisfies, and how each is verified.

It inherits scope, terminology, and boundaries verbatim from `PHASE-1-SCOPE.md`,
`ARCHITECTURE.md`, `CLAIMS-EVIDENCE-MODEL.md`, `SCREEN-STATES.md`,
`INFORMATION-ARCHITECTURE.md`, `ACCEPTANCE-CRITERIA.md`, and
`SECURITY-BOUNDARIES.md`. Where a state or type is named here it uses the
**canonical enum** from `SCREEN-STATES.md` — no synonyms.

The team values execution speed and least manual intervention. The plan
therefore front-loads automation (CI, migrations, deterministic tests, secret
scanning) so every later milestone verifies itself.

---

## 1. Guiding sequencing principles

1. **Spec approved first.** No code before the frozen specs are signed off.
   Frozen artefacts (data model, adapter boundaries, state model, async-job
   semantics, audit/immutability rules, IA/UX) are the contract; framework and
   vendor picks are deferred (§Milestone 0) and must not force a rewrite.
2. **Boundaries before vendors.** Define the typed interface, its fixture, and
   its tests before wiring any real vendor. One real implementation plus one
   fixture per interface — never speculative multiples (`ARCHITECTURE.md` §5,
   challenge-log #5; acceptance S2).
3. **Data model before UI.** The PostgreSQL schema, constraints, immutability
   and audit guards land before any API or screen. The truth boundary and the
   report gate are enforced in the data layer, not in the UI.
4. **One real adapter + fixture per interface.** Each of `CorporateRegistry
   Provider`, `ScreeningProvider`, `DomainRegistrationProvider`,
   `WebIntelligenceProvider`, `ModelProvider` ships exactly one real impl and a
   recorded fixture that makes its tests deterministic.
5. **Each milestone ends with its acceptance criteria + deterministic tests.**
   A milestone is not done until the ACCEPTANCE-CRITERIA IDs it claims are
   covered by an automated test (or a defined manual procedure where a test is
   impossible), all tests are deterministic, and CI is green.
6. **Additive, enum-extensible, no Phase 2 leakage.** Every milestone respects
   the exclusions in `PHASE-1-SCOPE.md` §5 and `CLAIMS-EVIDENCE-MODEL.md` §4.
   Absence of Phase 2 concepts is verified, not assumed (acceptance S1).

---

## Milestone 0 — Decisions to lock at build start

These are the challenge-log **DEFERRED** items. They must be resolved in the
first build PR, recorded in an ADR, and are frozen for the rest of Phase 1. None
may weaken a frozen boundary; each must satisfy the constraints below.

| Decision | Challenge-log ref | Constraints it must satisfy |
|---|---|---|
| **Backend framework** | #17 | Mature, typed, first-class PostgreSQL, native async/background jobs, high testability. Python+FastAPI **or** typed-Node both qualify. Must not leak vendor/ORM shapes across module seams (`intake`, `identity`, `enrichment`, `screening`, `evidence`, `findings`, `report`, `audit`, `adapters`). |
| **Frontend framework** | #17 | Mainstream component framework with strong accessibility tooling and server-render capability. **No** heavy client state library until state complexity justifies it. Must be able to meet WCAG 2.2 AA (A1–A4) and the greyscale/text-label rule (U6/A3). |
| **Concrete LLM behind `ModelProvider`** | #14 | A specific model chosen at build time, never hard-wired into callers — reachable only through `ModelProvider`. Used for extraction/drafting/clustering only; output cannot mutate state, gating, RBAC, or screening (C5, SEC-injection boundary). Swappable without caller changes. |
| **Object store** | #7 | S3-compatible in prod, filesystem in dev, one interface either way. Stores raw payloads keyed by `content_ref` + `content_hash` (SHA-256). Immutable — no overwrite path. Keeps large blobs out of the transactional DB (SEC3). |
| **IdP / auth** | #15 | Internal-only SSO/IdP. Two roles only: `analyst`, `manager`. Authorization enforced **server-side** on every mutation, independent of UI (SEC2). Fine-grained permissioning is out of scope. |

**Frozen regardless of the above:** data model, adapter boundaries, async-job
semantics, audit/immutability rules, IA and state model.

> **Note (no new deferred decision required).** The **intake-gate sufficiency
> heuristic** (M5) that separates `SUFFICIENT_FOR_DISCOVERY` from
> `CLARIFICATION_REQUIRED` must be **explicit and testable** — deterministic,
> inspectable rules, **not** an opaque LLM verdict — so criteria I1/I2 and cases
> T1/T2 can be verified. The `ModelProvider` may assist drafting, but the gate
> decision itself is code, not model output.

**Definition of done (M0):** ADR merged recording each pick + rationale; the
choices contradict no frozen boundary; `.env.example` placeholders exist for
every secret the picks introduce (SEC1).

---

## 2. Ordered milestones

Dependencies are cumulative — each milestone assumes all prior ones are done.

### M1 — Foundations (tooling, CI, secret hygiene, DB scaffolding)
- **Goal:** a self-verifying skeleton so every later milestone lands behind a
  green, deterministic pipeline.
- **Deliverables:**
  - Repo tooling: formatter, linter, type-checker, test runner — all run in CI.
  - CI pipeline: lint + type + test + migration-check on every PR; fails closed.
  - **Secret scanning** in CI + recommended pre-commit hook; `.env.example`
    placeholders only; real `.env` git-ignored (`SECURITY-BOUNDARIES.md` §4).
  - Migration framework wired; empty baseline migration; `migrate up/down`
    verified in CI against an ephemeral Postgres.
  - Structured logging with `investigation_id` / `job_id` correlation; no-secrets-in-logs
    lint/guard.
  - Fixtures policy: fictional entities only (`.test` / `.example`).
- **Dependencies:** M0.
- **Satisfies:** SEC1 (repo hygiene, secret scanning). Establishes the
  deterministic-test harness every other criterion relies on.
- **Verification:** CI green on a trivial PR; a planted fake secret is blocked;
  migrate up→down→up is idempotent; logging guard test rejects a secret string.

### M2 — Data model: record/entity split + claims/evidence/source + immutability + audit guards
- **Goal:** the frozen data model exists in Postgres with structural
  enforcement of the record≠entity split, the truth boundary, immutability, the
  raw-label and counterparty-dedup guards, the report gate, and audit.
- **Deliverables:**
  - Tables per `CLAIMS-EVIDENCE-MODEL.md`: `source`, `evidence`, `claim`,
    claim↔evidence `link`, `finding`, `audit_event`, and the **record/entity
    split** (challenge-log #21/#22): **`investigation`** (management record —
    raw `company_label` / `contact_label`, `intake_state`,
    `company_identity_status`, `case_context`, FK `counterparty_id`), shared
    **`counterparty`** (resolved legal entity, deduped on `identity_key`),
    **`person`**, and **`person_candidate`** (0..N per `contact_label`).
  - Enums exactly as in `SCREEN-STATES.md` and the data model: `source_class`,
    `claim_type`, `intake_state`, `investigation_state`,
    `company_identity_status` (CONFIRMED/AMBIGUOUS/NOT_VERIFIED),
    `person_evidence_status`, `relationship_state`, `completeness_state`,
    `screening_state`, `finding_type`, `review_status`, `severity`, etc.
  - **Immutability guard:** INSERT-only on source content columns via revoked
    UPDATE privilege or BEFORE UPDATE trigger (`ARCHITECTURE.md` §3).
  - **Raw-label immutability guard:** `company_label` / `contact_label` on
    `investigation` are **never overwritten** by resolution — enforced by
    trigger/permission, not convention (I3).
  - **Counterparty dedup:** `counterparty.identity_key = f(jurisdiction,
    registry_id)` is **unique**; a counterparty is matched/created on this
    authoritative key, never on label string similarity — the schema-level
    uniqueness underpins the M6 link-not-duplicate behaviour (challenge-log #25).
  - **Audit append-only:** INSERT-only role; no UPDATE/DELETE.
  - **Report-gate invariant** at the data layer: a Final Report cannot be
    produced unless `company_identity_status = CONFIRMED`; `counterparty_id`
    non-null only when `CONFIRMED`.
  - **Intake-gate invariant** at the data layer: no `counterparty_id` may be set
    while `intake_state = CLARIFICATION_REQUIRED` (no manufactured entity).
  - `case_context` stored as an opaque, non-evidentiary structure, structurally
    unjoinable into Sources/Claims/Evidence (see the M-CTX cross-cutting section).
  - Constraint: a claim is a "material fact" only if linked to evidence **or**
    explicitly marked unresolved.
  - `content_hash` (SHA-256) required on every source; object-store `content_ref`
    integration.
- **Dependencies:** M0, M1.
- **Satisfies:** C3 (material claims linked or unresolved — constraint), SEC3
  (immutable/versioned/hash-verified sources), partial C1/U4 (AMBIGUOUS cannot
  be silently resolved — enforced at data layer), **I3** (raw-label immutability
  guard), foundation for C2, L4, I2/I4/I6.
- **Verification:** migration tests; a test asserting UPDATE on a source content
  column is rejected; UPDATE/DELETE on `audit_event` rejected; **UPDATE of
  `company_label` / `contact_label` rejected** and raw labels remain recoverable
  after resolution (I3); **duplicate `identity_key` insert rejected** (dedup);
  a `counterparty_id` set while `intake_state = CLARIFICATION_REQUIRED` rejected;
  insert of a material claim with no evidence and no unresolved marker rejected;
  re-capture produces a new `version` with `supersedes_id` set and a distinct
  hash.

### M3 — Adapter interfaces + fixtures + first real implementations
- **Goal:** every external dependency sits behind a narrow typed interface, each
  with one real impl and one deterministic fixture.
- **Deliverables (one real + one fixture each):**
  - `CorporateRegistryProvider` (registry lookup → normalised evidence + stored
    source, `source_class = corporate_registry`).
  - `DomainRegistrationProvider` — **RDAP-first, WHOIS fallback**
    (`source_class = domain_registration`).
  - `ScreeningProvider` — sanctions/PEP/adverse; returns proposed
    `screening_state`, **never auto-decides** (`MATCH_REQUIRES_REVIEW` routes to
    human).
  - `WebIntelligenceProvider` — **sandboxed, credential-free, rate-limited,
    logged** public retrieval; content stored + hashed + treated as untrusted.
  - `ModelProvider` — LLM behind isolation; extraction/drafting/clustering only;
    system prompt + policy fixed in code; retrieved content passed as delimited
    **data**, never instructions.
  - Each adapter declares `source_class`, `license_class`, `limitations`;
    normalises at the boundary; typed failure → `SOURCE_UNAVAILABLE`.
- **Dependencies:** M2 (evidence/source schema).
- **Satisfies:** S2 (interfaces exist, ≤1 real impl each), S3 (RDAP not a graph
  DB, no autonomous privileged browser — verified by the sandboxed retrieval
  design), SEC3 (adapter-captured sources hashed), start of L4/U7 provenance via
  `source_class`/`extraction_confidence`.
- **Verification:** each adapter tested against its recorded fixture
  (deterministic, no network); a `SOURCE_UNAVAILABLE` path test; a fixture
  proving `ScreeningProvider` never emits `CONFIRMED_MATCH` on its own; a test
  that `WebIntelligenceProvider` carries no credentials and is rate-limited.

### M4 — Async job runner (Postgres-backed queue) + investigation job graph
- **Goal:** investigations run as an idempotent, partially-failing job graph on
  a Postgres-backed queue (no Redis).
- **Deliverables:**
  - Queue on `SELECT … FOR UPDATE SKIP LOCKED`, transactional with the data it
    produces (`ARCHITECTURE.md` §4, challenge-log #4). No broker.
  - Job graph (canonical order, `ARCHITECTURE.md` §4): intake quality gate →
    normalisation → candidate discovery → legal entity resolution → (company
    enrichment ∥ person enrichment ∥ domain ∥ screening) → finding synthesis →
    completeness assessment. The intake gate is a **hard branch**: a
    `CLARIFICATION_REQUIRED` intake runs **no** downstream step. (Gate,
    normalisation and discovery land in M5; resolution/dedup in M6; per-candidate
    person assessment in M7.)
  - Each step idempotent, records its own sources/evidence, and sets partial
    states (`PARTIAL_RESULTS`, `SOURCE_UNAVAILABLE`) rather than failing the
    whole case.
  - Investigation lifecycle states driven exactly per `SCREEN-STATES.md` §1;
    every transition writes a `STATE_CHANGE` audit event.
- **Dependencies:** M2, M3.
- **Satisfies:** foundation for C4 (runs the controlled test set), U5/completeness
  states, SEC2 (state changes audited). Deterministic-runner tests underpin all
  later behavioural criteria.
- **Verification:** step-idempotency tests (re-run yields no duplicate
  evidence); a fixture where one adapter is unavailable yields
  `PARTIAL_RESULTS` + `SOURCE_UNAVAILABLE`, not `FAILED`; concurrent-worker test
  proves no double-claim of a job (SKIP LOCKED); all transitions appear in audit.

### M5 — Intake quality gate + normalisation + candidate discovery
- **Goal:** decide whether an intake is good enough to investigate and, only
  when it is, normalise the raw labels and discover candidates — **before** any
  legal entity resolution runs (`ARCHITECTURE.md` §4 job graph).
- **Deliverables:**
  - **Intake Quality Gate** sets `intake_state` = `SUFFICIENT_FOR_DISCOVERY` /
    `CLARIFICATION_REQUIRED` on the raw `company_label` + `contact_label`, using
    an **explicit, testable sufficiency heuristic** (deterministic rules — not an
    opaque LLM verdict; see M0 note).
  - **Hard branch:** a `CLARIFICATION_REQUIRED` intake **blocks all discovery** —
    no normalisation, **no web/AI retrieval, no counterparty created, no
    manufactured entity**; the investigation waits and requests the minimum
    useful discriminator. `CLARIFICATION_REQUIRED` ≠ `AMBIGUOUS` — separate
    states, never merged (`SCREEN-STATES.md` §0).
  - **Normalisation** of the raw labels — non-destructive; `company_label` /
    `contact_label` are never overwritten (I3).
  - **Candidate discovery** produces candidate counterparties **and 0..N
    `person_candidate` records** derived from the raw `contact_label` (e.g.
    `NOVEXA - Amara - via Delta Trading`), without destructive parsing — foundation
    for M6 resolution and M7 per-candidate assessment.
- **Dependencies:** M4 (job runner/graph), M3 (adapters), M2 (schema).
- **Satisfies:** **I1** (CLARIFICATION_REQUIRED ≠ AMBIGUOUS), **I2** (no
  discovery / no counterparty on CLARIFICATION_REQUIRED), **U1** (discriminator
  requested only when required), foundation for I5.
- **Verification:** **T1** (`company_label = "TBD"` + first-name-only contact →
  `CLARIFICATION_REQUIRED`; no invented entity; no discovery launched); **T2**
  (`company_label = "Unnamed Refinery"` → `CLARIFICATION_REQUIRED`; asks for minimum
  discriminator); **T6** (initial-only contact `"JR"` → one `person_candidate`,
  never invents a person); a test asserting `CLARIFICATION_REQUIRED` fires **no**
  `WebIntelligenceProvider`/`ModelProvider` call and creates **no** counterparty;
  a test asserting the sufficiency heuristic is deterministic and inspectable
  (I1/I2); raw labels intact after normalisation (I3).

### M6 — Identity resolution & counterparty dedup
- **Goal:** ambiguity is a hard gate — no silent resolution anywhere — and a
  repeated organisation **links to** the existing counterparty rather than
  duplicating it.
- **Deliverables:**
  - Resolution sets `company_identity_status` to `CONFIRMED` / `AMBIGUOUS` /
    `NOT_VERIFIED` against authoritative source(s); meaningful only once
    `intake_state = SUFFICIENT_FOR_DISCOVERY`.
  - **Counterparty match/create on authoritative `identity_key`** (registry
    identity), **never** on label similarity: two investigations resolving to the
    same registry identity **link to the same `counterparty_id`**; a repeated
    organisation across management rows creates **no duplicate**, and a
    label-only match **never silently merges** distinct entities (challenge-log
    #25).
  - `AMBIGUOUS` pauses the investigation and requests the **minimum
    discriminator** needed (`PHASE-1-SCOPE.md` §4); no default selection.
  - `RESOLVE_IDENTITY` and `LINK_COUNTERPARTY` are explicit, audited actions;
    only `RESOLVE_IDENTITY` can move `AMBIGUOUS` → `CONFIRMED`.
  - No code path resolves `AMBIGUOUS` without that action (enforced + tested).
- **Dependencies:** M4, M5.
- **Satisfies:** **C1** (0 silently resolved ambiguous entities), **U4**
  (ambiguous identity cannot be accidentally bypassed), **C4** (controlled test
  set — 0 critical identity misses), **I4** (dedup: one counterparty per
  identity, no silent merge), SEC2.
- **Verification:** controlled counterparty test set runs with 0 critical miss;
  **T3** (`company_label = "Vantar - Castellan"` → discovery/resolution runs;
  raw label preserved verbatim even if the resolved counterparty differs); **T4**
  (same counterparty in a second management record **links** to the existing
  `counterparty_id` — no duplicate, no silent merge of distinct entities); test
  asserts no path mutates `AMBIGUOUS`→`CONFIRMED` except `RESOLVE_IDENTITY`; test
  asserts no default candidate is pre-selected; audit records the action + actor.

### M7 — Person resolution & per-candidate assessment
- **Goal:** each `person_candidate` from a `contact_label` is assessed
  **independently**; partial/multiple contacts are first-class and never
  collapsed into a single person verdict.
- **Deliverables:**
  - Per-candidate `person_evidence_status` (`IDENTITY_EVIDENCE_FOUND` /
    `LIMITED_EVIDENCE` / `IDENTITY_AMBIGUOUS` / `NO_RELIABLE_EVIDENCE_LOCATED`)
    and `relationship_state` (company↔person) set **per candidate**
    (`SCREEN-STATES.md` §3/§4), never one rolled-up verdict.
  - A `person_candidate` links to a shared `person` only when resolved
    (`person_id` set); an unresolved candidate never invents a person.
  - Raw `contact_label` remains intact; candidates carry only a `label_fragment`.
- **Dependencies:** M5 (candidates), M6.
- **Satisfies:** **I5** (0..N PersonCandidates, independent evidence +
  relationship state), reinforces I3, foundation for C6.
- **Verification:** **T5** (`"NOVEXA - Amara - via Delta Trading"` → ≥1
  `person_candidate` per person, each assessed independently, raw label intact);
  **T6** (initial-only `"JR"` → one candidate, likely
  `LIMITED_EVIDENCE`/`IDENTITY_AMBIGUOUS`, never an invented person); test that
  per-candidate states are stored and rendered separately, never collapsed.

### M8 — Findings synthesis + completeness
- **Goal:** findings emerge structurally from claim/evidence divergence, each
  carrying the four-part structure; completeness is assessed and stated.
- **Deliverables:**
  - Finding synthesis producing `finding_type` from `SCREEN-STATES.md` §6, with
    `severity` and the **CLAIM / EVIDENCE / ASSESSMENT / ACTION** four blocks
    never collapsed into a single label.
  - `asserted_by` + `source_class` drive provenance; model-drafted
    `assessment_text` is a draft a human edits/approves, never evidence on its
    own.
  - `completeness_state` set (`COMPLETE` / `COMPLETE_WITH_LIMITATIONS` /
    `MATERIAL_SOURCE_UNAVAILABLE`); limitations captured.
  - Screening states rolled onto the investigation; per-candidate
    person/relationship states (from M7) surfaced per candidate, never collapsed.
  - `case_context` is **structurally excluded** from finding synthesis: it is
    never read as a Claim/Evidence/Source input (M-CTX cross-cutting section).
- **Dependencies:** M4, M6, M7.
- **Satisfies:** C3 (findings reference claims/evidence), **L1/L2/L3**
  (evidence-based language, no character labels), **L4** (provenance classes not
  numeric AI confidence), U7 (truth-boundary distinctions), **I6** (case_context
  never an input to findings), foundation for C6.
- **Verification:** worked-example test (`CLAIMS-EVIDENCE-MODEL.md` §5) produces
  an `INCONSISTENCY` with all four blocks and never the string "suspicious";
  banned-phrase lint over generated text (L1/L2); test asserting a
  model-only-derived value with no source cannot become evidence; completeness
  state test with an unavailable material source; a test asserting a
  `case_context` value (including `internal_tier`) present on the investigation
  produces **no** finding and is never read by synthesis (I6).

### M9 — Application API + RBAC (`analyst` / `manager`)
- **Goal:** a typed HTTP/JSON API with server-side RBAC and full audit on every
  mutation.
- **Deliverables:**
  - Endpoints for intake, case read, identity resolution, finding actions
    (`CONFIRM_FINDING`, `DISMISS_FINDING`, `REQUEST_INFORMATION`, `ADD_NOTE`),
    analyst-supplied sources, and `FINALISE_REPORT`.
  - **RBAC enforced in the API, not the UI:** `analyst` vs `manager`;
    `FINALISE_REPORT` is `manager`-only.
  - Every mutating action authorised server-side and written to `audit_event`
    with actor identity; **material (high-severity) dismissal requires a
    rationale** (rejected without one).
- **Dependencies:** M2, M6, M8, M0 (auth pick).
- **Satisfies:** **SEC2** (mutations authorized + audited), **SEC4** (material
  dismissals require rationale), C1 (resolution via authorised action).
- **Verification:** authz tests — `analyst` calling `FINALISE_REPORT` is
  rejected; every mutation writes exactly one audit event with actor; a
  high-severity `DISMISS_FINDING` without rationale is rejected; RBAC test does
  not rely on any UI.

### M10 — UI build (case workspace per IA + state model)
- **Goal:** the analyst workspace implementing the frozen IA and every screen
  state, meeting the UX acceptance criteria.
- **Deliverables:**
  - Global nav: **Investigate · Cases · (account/role)** — no dashboards/metric
    tiles (`INFORMATION-ARCHITECTURE.md`).
  - Persistent case header + tabs in exact order:
    **SUMMARY · FINDINGS · COMPANY · PERSON · SCREENING** (five tabs; Evidence is
    an in-context **drawer**, not a tab — `COMPETITIVE-UX-PATTERN-AUDIT.md` §7).
  - Evidence drawer opens from any fact/finding and closes back to context
    (≤2 interactions, no page round-trip); a secondary "All sources" browse
    lists everything captured. Inline provenance chips on every fact/finding;
    `match_basis` ("why matched") on identity candidates, screening matches, and
    PersonCandidates; bounded Related-parties list (no graph).
  - Investigate screen = **2 fields** (raw `company_label`, `contact_label`);
    discriminators requested only at the intake gate or identity resolution.
  - Summary shows high-severity findings above the fold; every line links to
    context; evidence reachable in **≤2 interactions** from any finding.
  - Final report sections map 1:1 to the eight management questions incl.
    **Named Person(s)** and **Screening**, with completeness as a
    **checked-vs-not-established** checklist (audit §8, criteria X7–X10).
  - Universal component states (Loading / Empty / Partial / Error / Disabled /
    Source unavailable) per `SCREEN-STATES.md` §8; **Final Report** action
    present but **disabled with reason** until `company_identity_status =
    CONFIRMED`.
  - Truth-boundary treatment on every relevant surface (source fact vs
    counterparty claim vs system assessment); **every state has a text label +
    icon**, colour secondary only.
- **Dependencies:** M9, M0 (frontend pick).
- **Satisfies:** **U1** (2-field intake), **U2** (findings above fold), **U3**
  (evidence ≤2 interactions), **U4** (no default selection at the gate), **U5**
  (limitations visible), **U6/A3** (colour never sole conveyor), **U7** (truth
  boundary), **L4** (provenance not numeric confidence in UI).
- **Verification:** click-path test from any finding to its source ≤2
  interactions; greyscale render audit passes (no state distinguishable by
  colour alone); intake renders exactly 2 fields; disabled Final Report shows
  the reason string; component-state snapshot tests.

### M11 — Report assembler (gated on `company_identity_status = CONFIRMED`)
- **Goal:** the Counterparty Integrity Report assembled from stored
  claims/evidence/findings — not free-form LLM — and hard-gated.
- **Deliverables:**
  - Assembler reads stored data; every material fact links to evidence **or** is
    marked unresolved; no unsupported material facts emitted.
  - Generation **refused unless `company_identity_status = CONFIRMED`** (blocked
    by a `CLARIFICATION_REQUIRED` intake or `AMBIGUOUS` / `NOT_VERIFIED` identity
    at the data layer, not just UI).
  - `case_context` never appears as a report conclusion; internal tier never
    rendered as a rating; imported commercial fields never analysed (M-CTX).
  - Report sections mirror `PHASE-1-SCOPE.md` §3; limitations + required actions
    included; understandable in ~2 minutes.
  - No excluded Phase 2 section appears.
- **Dependencies:** M8, M9.
- **Satisfies:** **C2** (0 unsupported material facts), **C3** (100% linked or
  unresolved), **C8** (~2-minute comprehension), **U5** (limitations shown),
  **S1** (no Phase 2 sections), **I7** (Phase 2 commercial fields not analysed /
  absent from conclusions), reinforces the M2 gate invariant.
- **Verification:** assembler test rejects generation when
  `company_identity_status ≠ CONFIRMED`; validation test fails if any material
  fact lacks evidence and lacks an unresolved marker; section-allowlist test
  rejects any Phase 2 section; **T8** (imported commercial fields — product,
  quantity, Incoterm, port — retained as `case_context`, ignored by analysis,
  absent from findings/report conclusions, I7); timed comprehension test with
  analysts/management (C8, defined manual procedure).

### M12 — Human-review actions + audit completeness
- **Goal:** the review workflow is complete, auditable, and gate-safe.
- **Deliverables:**
  - Finding review lifecycle: `OPEN` → `CONFIRMED` / `DISMISSED` /
    `INFO_REQUESTED`, each an audited action.
  - `FINALISE_REPORT`: `manager` role, requires `CONFIRMED` entity, requires an
    explicit non-accidental confirmation step.
  - Screening adjudication: `MATCH_REQUIRES_REVIEW` → analyst →
    `CONFIRMED_MATCH`; never auto-decided.
  - Before/after payloads captured in audit where relevant.
- **Dependencies:** M9, M11.
- **Satisfies:** **SEC2**, **SEC4** (rationale on material dismissal),
  reinforces C1/U4 (no silent resolution), screening-never-auto-decides.
- **Verification:** each action writes the correct `action` audit event;
  finalise blocked without confirmed entity and without the confirmation step;
  screening cannot reach `CONFIRMED_MATCH` without an analyst action; audit is
  append-only end-to-end.

### M13 — Hardening (prompt-injection, accessibility, performance)
- **Goal:** prove the security and accessibility guarantees under adversarial
  and real conditions.
- **Deliverables:**
  - **Prompt-injection test suite:** adversarial fixtures embedded in retrieved
    content; assert **0** influence over policy/workflow/gating/RBAC/screening.
  - **Accessibility audit:** WCAG 2.2 AA contrast; full keyboard operability
    with visible focus; form fields with programmatic labels + associated error
    messaging; automated a11y checks in CI + a manual audit.
  - Greyscale/colour-vision audit across all states (U6/A3).
  - Performance pass against Phase 1 volumes (queue throughput, Summary render);
    confirms the Postgres-backed queue suffices — Redis stays deferred unless a
    demonstrated need appears.
- **Dependencies:** all prior milestones.
- **Satisfies:** **C5** (0 prompt-injection influence), **A1** (contrast),
  **A2** (keyboard + focus), **A3** (colour not sole conveyor), **A4** (labels +
  errors); confirms challenge-log #4 (no broker needed).
- **Verification:** adversarial fixture suite passes with 0 policy/workflow
  influence; automated a11y suite green in CI; manual keyboard + screen-reader
  pass documented; performance run within target at Phase 1 volumes.

### M14 — Bulk import (spreadsheet intake → per-row investigations)
- **Goal:** management can import a spreadsheet of many client/counterparty rows
  and each row becomes its own investigation that flows through the **same**
  canonical intake and job graph as a single intake — with malformed rows
  isolated and re-imports idempotent.
- **Deliverables:**
  - **`ImportBatch`** record (one per uploaded file) and a per-row parse that
    creates **one `investigation` per row**, mapping each row's raw
    `company_label` / `contact_label` and its non-evidentiary `case_context`
    (e.g. `management_reference`, `internal_tier`, `product`, `incoterm`, `port`)
    exactly as M2/M-CTX define — no new typed Phase 2 schema.
  - **Per-row intake-gate pass:** every row runs the M5 **Intake Quality Gate**
    unchanged — bulk applies no weaker or bypassed intake path; a `TBD` /
    `Unnamed Refinery` row yields `CLARIFICATION_REQUIRED` just as single intake.
  - **Malformed-row isolation:** a row that fails to parse or lacks a required
    field is recorded as its own failed / `CLARIFICATION_REQUIRED` outcome and
    **does not** corrupt, block, or alter any other row in the batch.
  - **No bulk auto-resolution:** `AMBIGUOUS` identity and ambiguous intake stay
    ambiguous — bulk performs no default counterparty selection (reuses the M6
    hard gate; no new resolution path).
  - **Dedup across rows:** rows resolving to the same authoritative
    `identity_key` link to the shared `counterparty_id` (reuses M6 dedup); no
    duplicate counterparty, no silent label-based merge.
  - **Raw-label immutability** across import — imported labels are never
    overwritten by resolution (reuses the M2 guard).
  - **Idempotency:** each row carries an `import_row_hash`; re-importing the same
    file creates **no** duplicate investigation for an unchanged row.
- **Dependencies:** M5 (intake gate), M6 (resolution/dedup), M4 (job runner),
  M2 (schema/guards).
- **Satisfies:** **B1** (malformed-row isolation), **B2** (per-row intake gate),
  **B3** (no bulk auto-resolution), **B4** (cross-row dedup on `identity_key`),
  **B5** (raw-label immutability), **B6** (idempotent on `import_row_hash`);
  reinforces C1, U4, I3, I4.
- **Verification:** a batch with one malformed row yields other rows'
  investigations intact + the malformed row isolated (B1); each row carries an
  `intake_state` from the M5 gate and a bulk `TBD`/`Unnamed Refinery` row →
  `CLARIFICATION_REQUIRED` (B2); an `AMBIGUOUS`-resolving row stays `AMBIGUOUS`
  with no default selection (B3); two rows resolving to the same registry
  identity (`Castellan Trading FZE` twice) link to one `counterparty_id` (B4);
  imported `Vantar - Castellan` label preserved verbatim after resolution (B5);
  re-importing the same file creates no duplicate for an unchanged row (B6).

### M15 — Analyst worklist (derived views over canonical states)
- **Goal:** an analyst can see which cases require action without opening every
  investigation — as a derived read-only view, not a dashboard.
- **Deliverables:**
  - A **worklist** view that projects existing investigations, keyed off
    **canonical workflow states** (`intake_state`, `investigation_state`,
    `screening_state`, `review_status`), surfacing rows that need analyst action
    (e.g. `CLARIFICATION_REQUIRED`, `AMBIGUOUS`, `MATCH_REQUIRES_REVIEW`, findings
    `OPEN`).
  - Worklist actionability is **derived** from those canonical states — no
    duplicated UI-only status logic and no separate stored status field.
  - **Not a dashboard:** no charts, no aggregate/vanity metric tiles, no risk
    score; a list respecting the IA nav (`Investigate · Cases`) and U6/A3
    (text label + icon, colour secondary).
- **Dependencies:** M4/M6/M8 (canonical states populated), M10 (UI shell).
- **Satisfies:** **W1** (identify cases needing action without opening each),
  **W2** (derived from canonical states, not a dashboard); reinforces S1, U6.
- **Verification:** seeded states produce a worklist listing exactly the cases
  needing action without opening them (W1); a test asserts each row's
  actionability maps 1:1 to a canonical state and a review/test asserts no chart,
  metric tile, or risk score is present (W2).

### M16 — Provider-aware adverse-media grouping
- **Goal:** duplicate adverse-media articles are not shown as multiple
  independent adverse events **where the provider already groups them** — by
  consuming provider-supplied grouping, not by building a clustering engine.
- **Deliverables:**
  - The adverse-media path (via `ScreeningProvider`) **consumes provider-supplied
    grouping** so grouped duplicate articles surface as **one** adverse event.
  - **Measure first:** before adding any lightweight dedup of our own, measure
    residual duplication on recorded fixtures; only if measurement shows a
    material gap is a bounded, deterministic lightweight dedup considered —
    **no clustering engine, no graph, no ML clustering** is built in Phase 1.
  - Where no provider grouping is available, duplicates remain separate (stated
    as a limitation), never fabricated into a single event.
- **Dependencies:** M3 (`ScreeningProvider` + fixture), M8 (findings/screening
  roll-up).
- **Satisfies:** **AM1** (provider-aware grouping; no clustering engine);
  reinforces S3 (no graph), L3.
- **Verification:** a `ScreeningProvider` fixture with provider-grouped duplicates
  yields one adverse event, not several (AM1); a test asserts grouping consumes
  only provider-supplied grouping and that no clustering engine exists; a
  no-grouping fixture leaves duplicates separate; residual-duplication
  measurement recorded before any lightweight dedup is added.

### M17 — Structured export (projection over stored data + licensing guard)
- **Goal:** a structured export of a case is a **projection over stored
  claims/evidence/findings** — traceable like the report and licence-safe — and
  is explicitly **secondary** to the management report (M11).
- **Deliverables:**
  - An export that reads **stored data only** (no free-form LLM); every material
    fact carries its provenance/evidence reference **or** an explicit unresolved
    marker, mirroring the M11 assembler.
  - A **licensing guard**: any source whose adapter-declared `license_class`
    prohibits redistribution is withheld from the export payload, while its
    traceable reference remains; the guard is enforced in code, not convention.
  - No excluded Phase 2 concept appears in the export; export is offered
    alongside, not in place of, the Counterparty Integrity Report.
- **Dependencies:** M8 (findings), M11 (assembler/traceability), M3 (adapter
  `license_class`).
- **Satisfies:** **E1** (exported facts traceable), **E2** (restricted
  vendor/source content not exported where licensing prohibits); reinforces C2,
  C3, X10, S1.
- **Verification:** exported material facts each carry an evidence reference or
  unresolved marker (E1); a case with a redistribution-prohibited source withholds
  that content from the export while keeping its reference (E2); section/concept
  allowlist test rejects any Phase 2 concept in the export.

> **DEFERRED (explicitly NOT a Phase 1 milestone): AI-drafted management
> summary.** An AI-generated executive/management summary is **out of Phase 1
> scope** and is not a milestone here. It would conflict with X10/C2 (no generic
> AI executive summary; every material statement click-through traceable). The
> structured export (M17) and the assembled report (M11) are projections over
> stored, evidence-linked data — not model-authored prose.

### M-CTX — `case_context` (retained-not-analysed) — cross-cutting
- **Goal:** imported commercial/management context is retained for traceability
  but **structurally excluded** from evidence and finding synthesis across every
  milestone that touches it (`CLAIMS-EVIDENCE-MODEL.md` §2.10, challenge-log #24).
- **Deliverables (spanning M2 / M5 / M8 / M11):**
  - `case_context` stored as an opaque, non-evidentiary structure (**not** a
    typed Phase 2 schema — no product/vessel/payment tables) and never joinable
    into Sources/Claims/Evidence (M2).
  - Discovery and resolution never read `case_context` as a discriminator (M5/M6).
  - Finding synthesis never takes `case_context` as an input (M8).
  - `internal_tier` (T1/T2/…) is **never** surfaced or interpreted as a Sentinel
    integrity/risk rating; imported commercial terms (product, quantity,
    Incoterm, port, price) are **not analysed** and never appear as report
    conclusions (M11).
- **Satisfies:** **I6** (case_context never Source/Claim/Evidence, never
  influences findings, tier never a rating), **I7** (Phase 2 commercial fields
  not analysed), reinforces S1.
- **Verification:** **T7** (internal tier present → retained in `case_context`,
  never used as evidence, never shown as a Sentinel rating); **T8** (imported
  commercial fields ignored by analysis, absent from findings/report); a
  static/structural test that no synthesis code path reads `case_context`.

---

## 3. Definition of done — per milestone (cross-cutting)

A milestone is done only when **all** of the following hold:

- **Tests deterministic.** No network, no wall-clock/random flakiness; adapters
  run against recorded fixtures. CI green.
- **No secrets.** Secret scanning passes; `.env.example` placeholders only; no
  real case/KYC/vendor payloads; sample data fictional (`.test`/`.example`).
- **Audit written.** Every state change and mutating action appends an
  `audit_event` with actor; material (high-severity) dismissals carry a
  rationale.
- **Canonical enums.** All states/types use the exact names from
  `SCREEN-STATES.md` / `CLAIMS-EVIDENCE-MODEL.md` — no synonyms.
- **No Phase 2 leakage.** No excluded concept (transactions, mandates, vessels,
  payments, capacity scoring, forgery claims, continuous monitoring) appears in
  schema, navigation, report sections, or UI copy (S1).
- **Claimed acceptance IDs covered.** Each ACCEPTANCE-CRITERIA ID the milestone
  lists maps to a passing automated test or a defined manual procedure.

---

## 4. Acceptance-criteria coverage map

| Milestone | Criteria satisfied |
|---|---|
| M1 Foundations | SEC1 |
| M2 Data model + guards | C3, SEC3, I3, (foundation: C1/U4, C2, L4, I2, I4, I6) |
| M3 Adapters | S2, S3 |
| M4 Job runner | (foundation: C4, U5, SEC2) |
| M5 Intake gate + discovery | I1, I2, U1, T1, T2, T6, (foundation: I5) |
| M6 Identity resolution + dedup | C1, C4, U4, I4, SEC2, T3, T4 |
| M7 Person + per-candidate | I5, T5, T6 |
| M8 Findings + completeness | C3, L1, L2, L3, L4, U7, I6, (foundation: C6) |
| M9 API + RBAC | SEC2, SEC4, C1 |
| M10 UI | U1, U2, U3, U4, U5, U6, U7, A3, L4 |
| M11 Report assembler | C2, C3, C8, U5, S1, I7, T8 |
| M12 Review + audit | SEC2, SEC4, C1, U4 |
| M13 Hardening | C5, A1, A2, A3, A4 |
| M14 Bulk import | B1, B2, B3, B4, B5, B6 |
| M15 Analyst worklist | W1, W2 |
| M16 Adverse-media grouping | AM1 |
| M17 Structured export | E1, E2 |
| M-CTX case_context | I6, I7, T7, T8 |

**Intake/identity/context criteria (revision 2)** map as: **I1/I2** → M5;
**I3** → M2 (guard); **I4** → M6; **I5** → M7; **I6** → M2/M8/M-CTX; **I7** →
M11/M-CTX. **Test cases:** T1/T2 → M5; T3/T4 → M6; T5 → M7; T6 → M5+M7; T7 →
M-CTX; T8 → M11/M-CTX.

**Bulk/worklist/adverse-media/export criteria (revision 4)** map as:
**B1–B6** → M14; **W1/W2** → M15; **AM1** → M16; **E1/E2** → M17. The
**AI-drafted management summary is DEFERRED** — explicitly not a Phase 1
milestone (see the note after M17).

Criteria requiring live analyst measurement — **C6** (≥80% relevance), **C7**
(≥30% time improvement), **C8** (~2-minute comprehension) — are validated by
defined manual procedures once M11 is available (baseline captured before build
start so C7 has a comparison point).

---

## 5. Risk / mitigation

| Risk | Mitigation |
|---|---|
| Framework/vendor pick (M0) later proves wrong | Only boundaries are frozen; adapters, data model, and job semantics are framework-agnostic, so a pick is reversible without a rewrite. |
| Redis assumed necessary, adds infra prematurely | Postgres-backed queue (SKIP LOCKED) ships first; broker deferred until M13 performance run shows a demonstrated throughput need (challenge-log #4). |
| Scope creep pulls in Phase 2 concepts | Exclusion list enforced by S1 review + section/claim-type allowlist tests in CI; absence verified, not assumed. |
| Poor intake manufactures a likely entity | Intake quality gate (M5) hard-branches on `CLARIFICATION_REQUIRED`: no discovery, no counterparty; heuristic is explicit/testable, not an opaque LLM verdict (I1, I2). |
| Same organisation duplicated / distinct entities silently merged | Counterparty match/create on authoritative `identity_key` only, never label similarity; schema-unique key (M2) + M6 link-not-duplicate tests (I4). |
| Commercial context or ARIE tier leaks into integrity conclusions | `case_context` retained-not-analysed, structurally excluded from Sources/Claims/Evidence and synthesis (M-CTX); tier never a rating (I6, I7). |
| Silent identity resolution slips in | Data-layer invariant + M6 tests: only `RESOLVE_IDENTITY` moves `AMBIGUOUS`→`CONFIRMED`; no default selection (C1, U4). |
| Prompt injection alters workflow | Policy/prompts fixed in code; retrieved content passed as delimited data; model output cannot mutate state/gating/RBAC; adversarial suite in M13 (C5). |
| Secret / real data leaks into public repo | Secret scanning + pre-commit hook in M1; fictional-data policy; `.env.example` placeholders only (SEC1). |
| Model output treated as fact | Evidence requires a stored source; model-only values cannot become evidence (enforced M8, tested). |
| Report generated on an unconfirmed entity | Hard gate at the data layer (M2) and assembler (M11): generation refused unless `company_identity_status = CONFIRMED`. |
| Colour-only state slips into UI | Every state carries text label + icon; greyscale audit in M10 and M13 (U6/A3). |
| Non-deterministic tests erode CI trust | Fixtures-only for adapters; no network/clock/random in tests; determinism part of every milestone's definition of done. |
