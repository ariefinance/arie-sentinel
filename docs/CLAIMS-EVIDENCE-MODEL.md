# Claims / Evidence Model

**Status:** Frozen for Phase 1. Additive extension allowed (new claim types);
breaking changes require sign-off.

This is the conceptual data model at the heart of Sentinel. It is
implementation-neutral (no ORM, no vendor) but precise enough to build a
PostgreSQL schema against. It exists so that **every material statement in a
report traces to dated, stored evidence**, and so the truth boundary from
`PHASE-1-SCOPE.md` §7 is enforced by structure rather than by prompt.

---

## 1. Core principle

Three node kinds, connected by explicit links:

```
CLAIM  ──asserted_by──▶  (counterparty | source | system)
  │
  │ supported_by / contradicted_by
  ▼
EVIDENCE  ──derived_from──▶  SOURCE (immutable, versioned)
  │
  ▼
FINDING  (emerges where CLAIM and EVIDENCE diverge or are missing)
```

- A **Claim** is a discrete assertion ("operating since 2011", "Jordan Rivera is
  Managing Director", "we are headquartered in Dubai").
- **Evidence** is a specific, dated observation drawn from a **Source** that
  supports or contradicts a claim.
- A **Source** is an immutable, versioned capture of external material (a
  registry record, a webpage snapshot, a screening API response).
- A **Finding** is a system- or analyst-recognised issue arising from the
  claim/evidence relationship.

No claim becomes a "material fact" in a report unless it is linked to at least
one piece of evidence **or** is explicitly recorded as unresolved.

---

## 1A. Raw record ≠ resolved entity (added revision)

Management supplies **labels**, not identities. Real intake looks like
`NORDIC-HALCYON`, `Vantar - Castellan`, `NOVEXA - Amara - via Delta Trading`,
`?? Halcyon Oil`, `Unnamed Refinery`, `TBD`. The model therefore separates three
distinct things that the original single "Case" wrongly fused:

```
INVESTIGATION            COUNTERPARTY                 PERSON
(management record)       (resolved legal entity)      (resolved individual)
─ company_label (raw)     ─ shared, deduplicated        ─ resolved from a
─ contact_label (raw)  ─▶   across investigations   ◀─    contact_label via
─ case_context            ─ one per real legal person     0..N PersonCandidates
  (non-evidentiary)
```

- The **Investigation** is one management row. It owns the **raw labels**
  exactly as supplied and never overwrites them.
- The **Counterparty** is the resolved legal entity. It is created once and
  **reused** when later investigations resolve to the same entity — a new
  management row referencing the same organisation must not spawn a duplicate
  counterparty.
- A **Person** is a resolved individual. A `contact_label` may contain
  initials, a first name, an informal name, or **several people at once**, so
  it resolves through **0..N PersonCandidate** records rather than being assumed
  to be one clean legal name.

### Intake pipeline & the quality gate

```
company_label + contact_label
        ▼
INTAKE QUALITY GATE ── CLARIFICATION_REQUIRED ─▶ stop; ask for the minimum
        │                                        useful discriminator.
        │ SUFFICIENT_FOR_DISCOVERY               (NO broad web/AI investigation,
        ▼                                         NO manufactured entity.)
NORMALISATION ─▶ CANDIDATE DISCOVERY ─▶ LEGAL ENTITY RESOLUTION
                                          (CONFIRMED / AMBIGUOUS / NOT_VERIFIED)
```

`CLARIFICATION_REQUIRED` (insufficient input to *begin* reliable discovery) and
`AMBIGUOUS` (discovery ran but several plausible identities remain) are
**different states with different causes** and must never be merged. See
`SCREEN-STATES.md`.

### Two non-evidentiary inputs

Raw labels and imported commercial context are **routing/context only**. They
are **never** Claims, Evidence, or Sources, and are **never** inputs to finding
synthesis:

- **Raw labels** (`company_label`, `contact_label`) are what management typed;
  they carry no evidentiary weight and cannot support or contradict anything.
- **`case_context`** retains imported commercial context (buyer/seller,
  management reference, internal tier, product, quantity, Incoterm, port,
  comments) for traceability only. It must not influence company/person
  integrity conclusions unless the same fact is *independently* established as
  Evidence, and ARIE internal tiers (T1/T2/…) must never become Sentinel
  integrity/risk ratings.

---

## 2. Entities (conceptual)

### 2.1 Source (immutable, versioned)

The atomic, tamper-evident unit. Once written, never mutated; re-capture
produces a new version.

| Field | Type | Notes |
|---|---|---|
| `source_id` | uuid | PK |
| `source_class` | enum | See §3. |
| `title` | text | Human label of the source. |
| `origin_ref` | text | URL, registry id, API endpoint — where permitted to store. |
| `retrieved_at` | timestamptz | When captured. |
| `captured_by` | enum | `adapter:<name>` \| `analyst` \| `system`. |
| `content_ref` | text | Pointer to stored raw payload (object store / blob). |
| `content_hash` | text | SHA-256 of raw payload — integrity + dedupe. |
| `version` | int | Increments on re-capture of the same logical source. |
| `supersedes_id` | uuid null | Previous version, if any. |
| `limitations` | text | Known caveats (staleness, partial access, jurisdiction). |
| `license_class` | enum | Governs whether raw content / URL may be surfaced. |

**Immutability rule:** application code may INSERT sources but never UPDATE the
content fields. Enforced by convention + DB trigger/permission in
implementation (see `ARCHITECTURE.md`).

### 2.2 Evidence

A dated observation extracted from exactly one source version.

| Field | Type | Notes |
|---|---|---|
| `evidence_id` | uuid | PK |
| `source_id` | uuid | FK → Source (specific version). |
| `observed_value` | jsonb | The extracted datum (e.g. `{ "incorporation_date": "2025-02-14" }`). |
| `excerpt` | text | Relevant excerpt / data for analyst review. |
| `extracted_by` | enum | `adapter:<name>` \| `model:<name>` \| `analyst`. |
| `extraction_confidence` | enum | `authoritative` \| `reported` \| `inferred`. **Not** a numeric AI score in UI. |
| `created_at` | timestamptz | |

If `extracted_by = model:*`, the evidence still points at a real source; the
model only *located/extracted* it. Model output alone (no source) cannot be
Evidence.

### 2.3 Claim

A discrete assertion, attributed to who/what made it.

| Field | Type | Notes |
|---|---|---|
| `claim_id` | uuid | PK |
| `investigation_id` | uuid | FK → Investigation. |
| `subject_ref` | uuid null | The resolved subject this claim attaches to: `counterparty_id` for company/domain claims, `candidate_id`/`person_id` for person claims. Null until resolved. |
| `claim_type` | enum | Extensible. Phase 1 set in §4. |
| `subject` | enum | `company` \| `person` \| `domain` \| `relationship`. |
| `statement` | text | Normalised human-readable claim. |
| `value` | jsonb | Structured value where applicable. |
| `asserted_by` | enum | `counterparty` \| `source` \| `system`. |
| `assertion_origin_ref` | text | Where the claim came from (intake field, URL, email). |
| `created_at` | timestamptz | |

`asserted_by` is the mechanical enforcement of the truth boundary: the UI
renders counterparty claims, source facts, and system assessments differently
based on this field.

### 2.4 Claim ↔ Evidence link

| Field | Type | Notes |
|---|---|---|
| `link_id` | uuid | PK |
| `claim_id` | uuid | FK → Claim. |
| `evidence_id` | uuid | FK → Evidence. |
| `relation` | enum | `supports` \| `contradicts` \| `partially_supports` \| `context`. |
| `created_by` | enum | `system` \| `analyst`. |
| `created_at` | timestamptz | |

### 2.5 Finding

| Field | Type | Notes |
|---|---|---|
| `finding_id` | uuid | PK |
| `investigation_id` | uuid | FK → Investigation. |
| `finding_type` | enum | See `SCREEN-STATES.md`: `CONTRADICTION`, `INCONSISTENCY`, `UNVERIFIED_CLAIM`, `ANOMALY`, `INSUFFICIENT_EVIDENCE`. |
| `severity` | enum | `high` \| `medium` \| `low`. |
| `title` | text | Short label, e.g. "Operating history". |
| `claim_text` | text | CLAIM block (what was stated). |
| `evidence_text` | text | EVIDENCE block (what sources establish). |
| `assessment_text` | text | ASSESSMENT block (why it needs attention). |
| `action_text` | text | ACTION block (what ARIE should do next). |
| `related_claim_ids` | uuid[] | |
| `related_evidence_ids` | uuid[] | |
| `review_status` | enum | `OPEN` \| `CONFIRMED` \| `DISMISSED` \| `INFO_REQUESTED`. |
| `created_by` | enum | `system` \| `analyst`. |
| `created_at` | timestamptz | |

Every finding carries the four-part **CLAIM / EVIDENCE / ASSESSMENT / ACTION**
structure. The UI never collapses these into a single label
(`PHASE-1-SCOPE.md` §6).

### 2.6 Investigation (management record)

One management row / one investigation. Holds the **raw labels** (immutable),
the intake and resolution state, non-evidentiary context, and a **reference** to
a shared Counterparty. It does **not** own the counterparty.

| Field | Type | Notes |
|---|---|---|
| `investigation_id` | uuid | PK. (Supersedes the earlier `case_id`.) |
| `company_label` | text | Raw management-supplied label, **never overwritten**. |
| `contact_label` | text | Raw management-supplied contact label, **never overwritten**. |
| `intake_state` | enum | `SUFFICIENT_FOR_DISCOVERY` \| `CLARIFICATION_REQUIRED` (see `SCREEN-STATES.md`). |
| `investigation_state` | enum | `NOT_STARTED` … `FAILED` (see `SCREEN-STATES.md`). |
| `company_identity_status` | enum | `CONFIRMED` \| `AMBIGUOUS` \| `NOT_VERIFIED`. Meaningful only once `intake_state = SUFFICIENT_FOR_DISCOVERY`. |
| `counterparty_id` | uuid null | FK → Counterparty. Non-null **only** when `company_identity_status = CONFIRMED`. |
| `company_match_basis` | text null | Plain-language "why matched" for the resolved counterparty + the identifiers that drove it (e.g. "registration number + jurisdiction match" vs "name only — weak"). Surfaced in Identity Resolution; keeps resolution visible/reversible (`COMPETITIVE-UX-PATTERN-AUDIT.md` §3, C4). |
| `completeness_state` | enum | 3-value. |
| `screening_state` | enum | 4-value. |
| `case_context` | jsonb null | Non-evidentiary imported context (see §2.10). |
| `import_batch_id` | uuid null | FK → ImportBatch (§2.12). **Null** for a single (non-bulk) investigation; set only for rows created by a bulk import. |
| `source_row_ref` | text null | Which spreadsheet row this investigation came from (e.g. sheet + row number). Null for single investigations. |
| `import_row_hash` | text null | Hash of the raw imported row. Used for **idempotency**: re-importing an identical row is detected and does not silently create an uncontrolled duplicate. Null for single investigations. |
| `created_by` | uuid | Analyst. |
| `created_at` / `updated_at` | timestamptz | |

**Invariants:**
- Raw labels are immutable; resolution never overwrites `company_label` /
  `contact_label`. `Vantar - Castellan` stays as-is even if the resolved
  counterparty is a different legal name.
- `intake_state = CLARIFICATION_REQUIRED` **blocks candidate discovery** — no
  normalisation, web/AI search, or entity resolution runs, and no counterparty
  is created. It is distinct from `AMBIGUOUS`.
- A Final Report may be generated only when `company_identity_status =
  CONFIRMED`. `AMBIGUOUS`, `NOT_VERIFIED`, or a `CLARIFICATION_REQUIRED` intake
  block it at the data layer, not just the UI.

**Bulk-import invariants** (single investigations are unaffected — the fields
above are all null for them):
- Bulk import creates **one Investigation per row** — never merges rows and never
  fans one row into several investigations.
- **Every** row passes the same intake quality gate (§2.6 / `SCREEN-STATES.md`
  §0); bulk import **never bypasses** it. A row with too-poor input becomes a
  `CLARIFICATION_REQUIRED` investigation exactly as a single one would.
- Malformed rows are **isolated**: one bad row is rejected on its own and does
  not corrupt, block, or alter the investigations created from other rows in the
  same batch.
- Commercial columns (buyer/seller, tier, product, quantity, Incoterm, port,
  comments) are retained as non-evidentiary `case_context` (§2.10), **never** as
  Claims, Evidence, or Sources.
- Re-import is **idempotent on `import_row_hash`**: an identical row re-imported
  is detected and does not silently create an uncontrolled duplicate
  investigation.

### 2.7 Counterparty (resolved legal entity — shared)

The resolved legal entity, created once and reused. Claims/evidence about "the
company" attach here (via the investigation), not to the raw label.

| Field | Type | Notes |
|---|---|---|
| `counterparty_id` | uuid | PK |
| `legal_name` | text | Resolved legal name (may differ from any label). |
| `registry_class` | enum | e.g. `corporate_registry` jurisdiction family. |
| `registry_id` | text | Registry number/identifier. |
| `jurisdiction` | text | |
| `status` | text | active / dissolved / etc. (as evidenced). |
| `identity_key` | text | Canonical dedupe key = f(jurisdiction, registry_id). |
| `first_resolved_at` | timestamptz | |

**Dedup invariant:** a Counterparty is matched/created on `identity_key`
(authoritative registry identity), **never** on label string similarity. Two
investigations that resolve to the same registry identity **link to the same**
`counterparty_id`; a repeated organisation across management rows must not
create a duplicate. Label-only matches must never silently merge counterparties.

### 2.8 Person (resolved individual — shareable)

A resolved individual. Optional in Phase 1 (a `contact_label` may never resolve
to a confirmed person). Shareable across investigations by the same key
discipline as Counterparty.

| Field | Type | Notes |
|---|---|---|
| `person_id` | uuid | PK |
| `display_name` | text | Resolved name. |
| `identity_key` | text null | Canonical key where an authoritative identifier exists. |
| `first_resolved_at` | timestamptz | |

### 2.9 PersonCandidate (derived from a contact_label)

The safe representation of partial/multiple contacts. Discovery derives **0..N**
candidates from one raw `contact_label` (e.g. `NOVEXA - Amara - via Delta Trading`
→ candidate "Amara"; `JR` → one initial-only candidate). The raw label is never
destructively parsed.

| Field | Type | Notes |
|---|---|---|
| `candidate_id` | uuid | PK |
| `investigation_id` | uuid | FK → Investigation. |
| `label_fragment` | text | The portion of `contact_label` this candidate came from. |
| `person_id` | uuid null | FK → Person, set only when resolved. |
| `person_evidence_status` | enum | 4-value (see `SCREEN-STATES.md`). |
| `relationship_state` | enum | 5-value: relationship of this candidate to the counterparty. |
| `match_basis` | text null | Plain-language "why matched" for this candidate + the identifiers that drove it (C4). |
| `created_by` | enum | `system` \| `analyst`. |
| `created_at` | timestamptz | |

**Invariant:** person evidence and relationship states live **per candidate**.
One `contact_label` with several people yields several candidates, each assessed
independently; the UI never collapses them into a single verdict.

### 2.10 case_context (non-evidentiary)

Imported commercial/management context, retained for traceability only. Stored
as an opaque, **retained-not-analysed** structure — deliberately **not** a
typed Phase 2 schema (no product/vessel/payment tables).

Suggested (all optional) keys: `buyer_seller`, `management_reference`,
`internal_tier`, `product`, `quantity`, `incoterm`, `port`,
`commercial_comments`, `raw_source_row`.

**Invariants:**
- `case_context` is never a Source, Claim, or Evidence, and is never an input to
  finding synthesis.
- It must not influence company/person integrity conclusions unless the same
  fact is independently established as Evidence.
- `internal_tier` (T1/T2/…) must never be surfaced or interpreted as a Sentinel
  integrity/risk rating.
- Product / price / port / Incoterm / commercial terms are **not analysed** in
  Phase 1 (scope guard, `PHASE-1-SCOPE.md` §5).

### 2.11 Audit event

Every state change and analyst action is appended here. Append-only.

| Field | Type | Notes |
|---|---|---|
| `event_id` | uuid | PK |
| `investigation_id` | uuid | FK. |
| `actor` | enum/uuid | Analyst id or `system`/`adapter:<name>`. |
| `action` | enum | `CONFIRM_FINDING`, `DISMISS_FINDING`, `REQUEST_INFORMATION`, `ADD_NOTE`, `FINALISE_REPORT`, `RESOLVE_IDENTITY`, `REQUEST_CLARIFICATION`, `LINK_COUNTERPARTY`, `STATE_CHANGE`, … |
| `target_ref` | text | Finding/claim/investigation/counterparty affected. |
| `rationale` | text null | **Required** for material dismissals. |
| `payload` | jsonb | Before/after where relevant. |
| `created_at` | timestamptz | |

### 2.12 ImportBatch (bulk-import grouping)

A minimal record that exists **only** to group Investigations created by one bulk
import (an uploaded spreadsheet). It holds no evidentiary data and takes no part
in claim/evidence/finding synthesis; investigations reference it via
`import_batch_id` (§2.6).

| Field | Type | Notes |
|---|---|---|
| `import_batch_id` | uuid | PK |
| `filename` | text | Name of the uploaded file. |
| `imported_by` | uuid | Analyst who ran the import. |
| `imported_at` | timestamptz | When the batch was imported. |
| `row_count` | int | Number of rows in the source file. |
| `source_format` | enum | `xlsx` \| `csv`. |

A single (non-bulk) investigation has no ImportBatch: its `import_batch_id`,
`source_row_ref`, and `import_row_hash` are null.

> **Derived views (no new persisted state).** The **analyst worklist** is a
> derived view over existing canonical states (Investigation / PersonCandidate /
> Finding / screening states) — it persists no new state of its own. The
> **structured export** is a projection over existing tables (no new data,
> licensing-aware per each Source's `license_class`).

---

## 3. Source classes (Phase 1)

`source_class` is a controlled vocabulary so evidence provenance is legible:

- `corporate_registry` — official company registry.
- `sanctions_pep_screening` — screening adapter response.
- `domain_registration` — RDAP/WHOIS.
- `official_publication` — gazette, regulator, court where available.
- `counterparty_asserted` — the counterparty's own website / materials / intake.
- `press_media` — news / media.
- `web_public` — other public web material.
- `analyst_supplied` — document/observation added by an analyst.

Source class drives how strongly evidence can support a fact and how it renders
(authoritative vs reported vs counterparty-asserted).

---

## 4. Claim types (Phase 1) — extensible

Kept deliberately small and additive. New types may be added later **without
schema change** (it is an enum value + handling), which is how the model
"designs for change without building the future" (`ARCHITECTURE.md`).

`legal_identity`, `registration_status`, `directorship`, `ownership`,
`address`, `operating_history`, `domain_ownership`, `person_role`,
`person_relationship`, `contact_detail`, `public_statement`.

> **Excluded (Phase 2, do not add):** any `transaction_*`, `mandate_*`,
> `vessel_*`, `payment_*`, `financial_capacity_*` claim types. Their absence is
> intentional and enforced by review, not by a placeholder schema.

---

## 5. Worked example (mirrors the brief)

```
Claim
  claim_type: operating_history
  subject: company
  statement: "Company operations since 2011"
  asserted_by: counterparty
  assertion_origin_ref: https://vantar-energy.test/about

Evidence
  source_class: corporate_registry
  observed_value: { incorporation_date: "2025-02-14" }
  excerpt: "Date of incorporation: 14 February 2025"
  extraction_confidence: authoritative

Link: relation = contradicts

Finding
  finding_type: INCONSISTENCY
  severity: medium
  title: "Operating history"
  claim_text:      "Company website states operations since 2011."
  evidence_text:   "Current legal entity incorporated 14 February 2025."
  assessment_text: "The stated history predates formation of the current legal
                    entity. This may reflect predecessor or management
                    experience."
  action_text:     "Clarify corporate history and obtain supporting evidence."
```

This never renders as "Suspicious company." It renders as an
inconsistency with claim, evidence, assessment, and a required action.

---

## 6. Why this model (design rationale)

- **Auditability:** every fact → evidence → source(version) → hash. A report
  is reconstructable and defensible.
- **Immutability:** sources are versioned, never overwritten, so a report
  reflects exactly what was known when.
- **Truth boundary by structure:** `asserted_by` + `source_class` make it
  impossible to render a counterparty claim as a source fact.
- **No graph DB needed:** the relationships here are shallow and bounded
  (claim↔evidence↔source, findings referencing claims). Relational tables with
  FKs and a couple of join tables model this cleanly. See the Technical
  Challenge Log in `ARCHITECTURE.md` (graph DB → REJECT for Phase 1).
- **Extensible without speculation:** new claim types / source classes are enum
  additions, not new tables. Phase 2 concepts are deliberately absent.
- **Record ≠ entity:** raw management labels live on the Investigation and never
  become identities or evidence; the resolved Counterparty is shared and
  deduplicated on authoritative registry identity, so the same organisation
  across many management rows links rather than duplicates.
- **Partial/multiple people are first-class:** a `contact_label` resolves
  through 0..N PersonCandidates, so initials, first names, and several people in
  one field are represented without destructive parsing or false single-person
  assumptions.
- **Context stays non-evidentiary:** `case_context` and internal tiers are
  retained for traceability but structurally excluded from evidence and finding
  synthesis, preventing commercial context or ARIE tiers from leaking into
  integrity conclusions — and without introducing Phase 2 schemas.
