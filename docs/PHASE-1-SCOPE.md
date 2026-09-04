# Phase 1 Scope — Counterparty Integrity Engine

**Status:** Frozen. Changes require explicit product sign-off.
**Owner:** ARIE Product / Compliance.
**Audience:** ARIE analysts, compliance management, engineering.

This document is the single source of truth for what ARIE Sentinel Phase 1
does and — equally important — what it does not do. Every other specification
in this repository inherits its scope, terminology, and boundaries from here.

---

## 1. One-sentence definition

> Given a **company name** and a **contact person**, Sentinel establishes who
> the counterparty legally is, whether the named person is credibly connected
> to it, what public and screening intelligence exists, and where claims and
> evidence disagree — then produces a single, auditable **Counterparty
> Integrity Report** that an analyst can understand in about two minutes.

Sentinel is a **case-investigation workspace**, not an analytics dashboard and
not a decision engine. It surfaces evidence and contradictions. Humans decide.

---

## 2. Inputs (Phase 1) — raw labels, not identities

Intake has **two paths**, and both produce the same kind of work item — one
**Investigation** carrying **raw management/prospect labels**, not established
identities:

1. **Single investigation** — an analyst enters exactly two fields (below).
2. **Bulk list import** — an analyst uploads an **XLSX/CSV** management list;
   **each row becomes one separate Investigation** (§2C).

Every Investigation, regardless of path, captures the same raw labels and
**must pass the same gates** — Intake Quality Gate (§2A) → Normalisation →
Candidate Discovery → Identity Resolution (§4). Bulk import never bypasses any
gate.

| Field | Required | Notes |
|---|---|---|
| Company label (`company_label`) | Yes | Free text as management recorded it — e.g. `NORDIC-HALCYON`, `Vantar - Castellan`, `?? Halcyon Oil`, `Unnamed Refinery`, `TBD`. |
| Contact label (`contact_label`) | Yes | Free text — may be a full name, a first name, initials (`JR`), an informal name, or **several people at once** (`NOVEXA - Amara - via Delta Trading`). |

Raw labels are **immutable** and are never overwritten by later resolution, and
they carry **no evidentiary weight** (§7). No other input is required to *start*.
Additional discriminators are requested only when the system cannot proceed —
either at the **Intake Quality Gate** (§2A) or during Identity Resolution (§4),
which are distinct.

### 2A. Intake Quality Gate (added revision)

Before any discovery runs, Sentinel assesses whether the raw labels are good
enough to begin reliable company resolution:

```
company_label + contact_label → INTAKE QUALITY GATE → NORMALISATION
    → CANDIDATE DISCOVERY → LEGAL ENTITY RESOLUTION
```

Canonical intake states (`SCREEN-STATES.md` §0):

- `SUFFICIENT_FOR_DISCOVERY` — proceed with discovery.
- `CLARIFICATION_REQUIRED` — input too poor to start (e.g. `TBD` + a first name
  only, or `Unnamed Refinery`). Sentinel **must not** launch a broad web/AI
  investigation and manufacture a likely entity. It returns:
  *"Clarification required — insufficient information to begin reliable company
  resolution,"* and asks for the minimum useful discriminator.

`CLARIFICATION_REQUIRED` (insufficient input) and `AMBIGUOUS` (§4: discovery ran
but several identities remain) are **different states** and must never be merged.

### 2B. Record ≠ entity, and context ≠ evidence (added revision)

- One management row is one **Investigation**; the resolved legal entity is a
  separate, shared **Counterparty**; the contact resolves to **0..N persons**.
  A repeated organisation across management rows **links** to the existing
  counterparty rather than creating a duplicate.
- Imported commercial context (buyer/seller, internal tier, product, quantity,
  Incoterm, port, comments) is retained as non-evidentiary **`case_context`**
  only. It never influences integrity conclusions unless independently
  evidenced, ARIE internal tiers never become Sentinel risk ratings, and
  commercial terms are **not analysed** in Phase 1 (§5). See
  `CLAIMS-EVIDENCE-MODEL.md`.

### 2C. Bulk list import (added revision)

Management already keeps counterparties in a spreadsheet, so intake supports a
bulk path: upload an **XLSX/CSV**, and **each row becomes one separate
Investigation** that enters the same pipeline as a single investigation —
Intake Quality Gate → Normalisation → Candidate Discovery → Identity
Resolution. **Gates are never bypassed for bulk rows.**

- **Columns** may include a company label, a contact label, buyer/seller, a
  management reference, and other optional context. Company and contact labels
  populate the two raw fields (§2); the remaining **non-Phase-1 commercial
  fields are retained as non-evidentiary `case_context`** (§2B), never as
  evidence.
- **Simplest professional import.** Phase 1 uses a straightforward file import,
  **not** an ETL / column-mapping platform.
- **Idempotent.** Re-importing the same list must **not** silently create
  uncontrolled duplicates; an **import row hash** identifies rows already
  ingested (see `ARCHITECTURE.md` §4). Repeated organisations still **link** to
  the existing shared Counterparty (§2B), never a duplicate.
- **Malformed-row isolation.** One bad row is isolated and reported; it must
  **not** corrupt or block the other rows in the same file.

---

## 3. What Sentinel must establish

Each item below is a first-class deliverable of the investigation and maps to a
screen and/or a report section.

1. **Exact legal entity** — the specific registered legal person, not a brand.
2. **Corporate registration / status** — registry, number, incorporation date,
   status (active/dissolved/etc.), jurisdiction.
3. **Directors / ownership** — where obtainable from authoritative sources.
4. **Evidence concerning the named person** — existence, role, footprint.
5. **Company ↔ person relationship** — is the person credibly connected to the
   entity, and on what basis.
6. **Company ↔ domain relationship** — does the claimed web presence belong to
   the legal entity, and what does registration timing indicate.
7. **Sanctions / PEP / adverse-intelligence results** — via external adapters.
8. **Material public intelligence** — relevant, sourced, dated.
9. **Claims vs evidence** — what the counterparty asserts vs what sources show.
10. **Contradictions / inconsistencies / unverified claims / anomalies.**
11. **Research limitations** — what could not be established and why.
12. **Required verification actions** — concrete next steps for ARIE.
13. **Auditable Counterparty Integrity Report** — the management deliverable.

> The **Counterparty Integrity Report remains the primary output.** A
> **structured analyst export** (§3A) is a **secondary** deliverable for
> analysts working across cases; it never replaces or outranks the report.

### 3A. Structured analyst export (secondary deliverable, added revision)

A **CSV/XLSX evidence & findings register**, assembled from stored
claims / evidence / findings, for analysts who need a tabular working view
across investigations. It is **secondary** to the management report.

- **Fields:** investigation reference, resolved entity, person / contact,
  claim, finding type, finding status, source class, source reference / URL
  (only where licensing permits), retrieved date, analyst decision, required
  action.
- **Licensing-aware.** The export **never** includes proprietary vendor
  payloads or source content where licensing prohibits it — only a reference
  is emitted in that case (`SECURITY-BOUNDARIES.md`).
- Uses **evidence-based language only** (§6) and preserves the truth boundary
  (§7): source fact vs counterparty claim vs system assessment stay distinct.

---

## 4. Identity Resolution is a gate, not a feature

If discovery from the `company_label` returns more than one plausible legal
entity, the investigation **pauses** and asks the analyst to disambiguate,
presenting the minimum discriminator needed. (This is `AMBIGUOUS` — discovery
ran; it is not `CLARIFICATION_REQUIRED`, which is a poor-input state at the
intake gate, §2A.)

- **Ambiguous identity blocks final report generation.** There is no code path
  that silently picks an entity. This is an acceptance criterion (see
  `ACCEPTANCE-CRITERIA.md`) and a hard invariant in the data model
  (`CLAIMS-EVIDENCE-MODEL.md`).

---

## 5. Explicitly EXCLUDED from Phase 1

The following are **out of scope** and must not appear in code, schema,
navigation, report sections, or UI copy. They are documented here so the
boundary is auditable and so "helpful" scope creep can be rejected on sight.

- Transaction-chain analysis.
- Oil/gas (or any) mandate verification.
- Product verification.
- Commercial plausibility assessment (price/quantity/Incoterm/port/terms).
- Vessels / cargo / logistics.
- Payment-release decisions.
- Transaction authority determinations.
- Financial-capacity or credit scoring.
- Document-forgery claims / authenticity adjudication.
- Continuous / ongoing monitoring.
- **Composite / global risk score** (no single blended risk number).
- **Graph database** and **graph-first UI / navigation** (relational store;
  see `ARCHITECTURE.md` §10).
- **Opaque AI conclusions** — no model-authored verdict without traceable,
  dated sources (§7).
- **Automatic clearance** and **autonomous acceptance / decline** — Sentinel
  never accepts, declines, or clears a counterparty on its own; humans decide.
- **Converting absence of evidence into an adverse judgment** — see the
  principle below.
- Any Phase 2 functionality.

> **Absence of evidence is never an adverse judgment.** "No reliable evidence
> located" is a *research limitation* (§3, item 11), recorded as such — it is
> never rendered, scored, or reported as a negative finding, a risk signal, or
> an implied conclusion about the counterparty or person.

> Management's real spreadsheet contains some of the above (product, quantity,
> Incoterm, port, buyer/seller, tier). Importing that context as non-evidentiary
> `case_context` (§2B) does **not** authorise analysing it — these remain out of
> scope and must not surface in findings, reports, or UI as conclusions.

### 5A. Non-goals — Sentinel is not sales-enablement

Sentinel is a **counterparty-integrity investigation** tool. It is **not** a
sales-enablement / lead-generation system. Out of scope by purpose (these belong
to a **different ARIE system**, not Sentinel):

- CRM lead routing, prospect scoring, or "buying signals".
- Slack / channel alerts, newsletters, or digests.
- Competitor battlecards or sales-intelligence feeds.

### 5B. Deferred — not a Phase 1 requirement

- **AI-drafted management summary.** Explicitly **not** required in Phase 1.
  The report is already concise and structured, and a generated summary would
  add a factual-control and citation-validation surface. The architecture may
  permit it **later** — only if report-writing proves a bottleneck, and only as
  a sentence-level cited draft under **mandatory human approval**. It is **not**
  built or specified now (`ARCHITECTURE.md` §10, Revision 4).

See `ARCHITECTURE.md` for how boundaries are kept clean (adapter and
claim-type extensibility) **without** building any of the above now.

---

## 6. Design & language safety rules (product-level)

These apply to every screen, report, and generated sentence. They are repeated
in the design and security specs because they are non-negotiable.

Sentinel must **never** state or imply:

- "safe company", "fraudulent company", "genuine company"
- "fake person", "safe transaction", "verified credibility"
- "suspicious", "probably fake", or any subjective character judgment.

Sentinel uses **evidence-based language only**. It reports what sources show,
what the counterparty claims, where they diverge, and what to do next.

| Not allowed | Allowed |
|---|---|
| "Suspicious website." | "Domain registration substantially post-dates legal entity formation." |
| "Person probably fake." | "No reliable evidence located linking the named person to the legal entity." |
| "Genuine company." | "Legal entity confirmed against [registry]; status: active." |

---

## 7. Truth boundary (applies everywhere)

The system must always let the analyst distinguish three different kinds of
statement, and must never blur them:

1. **Source fact** — established by an authoritative/external source.
2. **Counterparty claim** — asserted by the counterparty (website, intake,
   email).
3. **System assessment** — Sentinel's reasoning about the relationship between
   the two.

**AI/LLM output is never evidence by itself.** A model may draft an assessment
or extract a candidate claim, but the underlying fact must trace to a stored,
dated source (`CLAIMS-EVIDENCE-MODEL.md`). This is enforced structurally, not
by prompt.

---

## 8. Success in one line

An analyst opens a completed case, reads the Summary, and within ~2 minutes
knows: **what is verified, what cannot be established, what materially
conflicts, and what to do next** — with every material statement one or two
clicks from its evidence.
