# Information Architecture

**Status:** Frozen for Phase 1 (navigation may be refined, not expanded).

Defines how information is organised, navigated, and distributed across screens
so an analyst reaches any conclusion — and its evidence — quickly, and so the
Summary never becomes a data dump.

---

## 1. Two levels of navigation

### Global navigation (minimal)
Sentinel is a workspace, not a suite. Global chrome is intentionally thin:

- **Investigate** (new case / intake) — two intake paths: **single
  investigation** (primary — the two-label Investigate form, Flow A) and **bulk
  list import** (secondary — upload an XLSX/CSV list, Flow A3). Each imported row
  becomes its own Investigation and passes the same Intake Quality Gate; the gate
  is **never bypassed** by bulk import.
- **Cases** (list of investigations the user can access)
- **(account / role indicator)**

No dashboards, no analytics landing page, no metric tiles.

**Intake Clarification ≠ Identity Resolution.** The **Investigate** flow can
pause at two distinct gates that must never be presented as the same step
(`SCREEN-STATES.md` §0, §2; `PHASE-1-SCOPE.md` §2A, §4):

- **Intake Clarification** (`intake_state = CLARIFICATION_REQUIRED`) — raw labels
  are too poor to *begin* discovery. It asks for the minimum useful
  discriminator; no discovery, web/AI search, or counterparty creation runs.
- **Identity Resolution** (`company_identity_status = AMBIGUOUS`) — discovery
  *ran* and returned several plausible entities; it asks the analyst to
  disambiguate.

Each surfaces its own copy and neither is folded into the other.

### Case navigation (the workspace)
Within a case, tabs (in this order):

```
SUMMARY · FINDINGS · COMPANY · PERSON · SCREENING      (+ Evidence drawer, everywhere)
```

Rationale (revised per `COMPETITIVE-UX-PATTERN-AUDIT.md` §7): read the position
(Summary) → act on what needs judgment (Findings) → dig into the entity, person,
and screening detail as needed. **Findings sits second** (triage-first, matching
the market norm of leading with the "what needs my attention" queue) without
changing interaction counts. **Evidence is not a primary tab**: it is an
**in-context drawer** opened from any fact or finding (1 interaction, closes back
to context), with a secondary **"All sources"** browse for reviewing everything
captured. This overturns the earlier "Evidence-as-tab" choice because both the
interaction budget and the market norm favour drill-to-source *in context*
(§6, and the audit §7). **Screening stays a dedicated tab** — every screening
product gives sanctions/PEP/adverse-media its own adjudication surface; folding
it into Company/Person would bury formal concerns.

## 2. Persistent case header

Present on every case screen. Read-at-a-glance orientation:

```
┌────────────────────────────────────────────────────────────────────┐
│ Legal entity: Vantar Energy Trading FZE      [Investigation: COMPLETED]│
│ Company label (as supplied): "Vantar - Castellan"                      │
│ Contact label: "NOVEXA - Amara"             [Completeness: WITH_LIMITATIONS]│
│ Company identity: CONFIRMED · Relationship: SELF-ASSERTED               │
│ SUMMARY  FINDINGS  COMPANY  PERSON  SCREENING            [Final Report] │
└────────────────────────────────────────────────────────────────────┘
      (Evidence opens as a drawer from any fact/finding — not a tab)
```

The header always shows two distinct company identifiers, never conflated:

- the **raw `company_label`** exactly as management supplied it, on its own
  "Company label (as supplied)" line — quoted, and **never overwritten** by
  resolution (`CLAIMS-EVIDENCE-MODEL.md` §2.6);
- the **resolved Counterparty legal name** (from the shared Counterparty, §2.7),
  shown once `company_identity_status = CONFIRMED`. Before that it reads
  "Legal entity: not yet resolved" — the raw label is never promoted into the
  legal-name slot.

It also shows the contact label (raw), investigation state, completeness state,
`company_identity_status` (**CONFIRMED / AMBIGUOUS / NOT_VERIFIED**, always as an
explicit text label — never a colour or a risk score), relationship state, and
the tab bar. When `intake_state = CLARIFICATION_REQUIRED`, the header surfaces
that intake banner instead of an identity status (discovery has not run, so
`company_identity_status` is not yet meaningful — `CLAIMS-EVIDENCE-MODEL.md`
§2.6): e.g. *"Clarification required — insufficient information to begin reliable
company resolution."*

State labels are text (colour is secondary). The **Final Report** action is
present but **disabled with reason** until `company_identity_status = CONFIRMED`
(e.g. "Finalise disabled: company identity is AMBIGUOUS"). A
`CLARIFICATION_REQUIRED` intake also blocks it (discovery has not begun);
`AMBIGUOUS` and `NOT_VERIFIED` block it as well. The gate is enforced in the
data layer, not just the UI (`SCREEN-STATES.md` §9).

## 2A. Investigation ≠ Counterparty ≠ Person

The header renders three distinct things the data model keeps separate
(`CLAIMS-EVIDENCE-MODEL.md` §1A, §2.6–2.9):

- the **Investigation** — this one management row, owning the raw labels;
- the **Counterparty** — the resolved legal entity, which is **shared and
  deduplicated across investigations** (one per real legal person);
- the **Person(s)** — resolved from the contact label.

Because a Counterparty is shared, the header/Summary may note that the same
resolved entity is *"also referenced by N other investigations"* (linked
investigations), as a plain wayfinding cue on the Company tab. This is a count
and, at most, links to those investigations — it **does not** import their
claims, evidence, findings, or `case_context` into this case. Keep it minimal;
there is no cross-investigation aggregation, merged timeline, or heavy
cross-linking UI in Phase 1.

**Person tab lists candidates, not a single assumed person.** A raw
`contact_label` maps to **0..N PersonCandidates** (`CLAIMS-EVIDENCE-MODEL.md`
§2.9) — initials, a first name, or several people in one field. The Person tab
therefore lists the candidates derived from the label, each with its own person
evidence state and relationship state; the UI never collapses them into one
person verdict.

## 3. Breadcrumbs

Shallow hierarchy → breadcrumbs are minimal. Used only for drill-down out of
Evidence back to the originating finding/fact (e.g. `Findings ▸ Operating
history ▸ Evidence`). The case header + tabs carry primary wayfinding.

## 4. What lives where (Summary vs drill-down)

The Summary answers the five questions and **links out**; it does not reproduce
detail. Detail lives on the specialised tabs.

| Question | On SUMMARY (concise) | Drill-down home |
|---|---|---|
| What is verified? | Verified-facts shortlist (top items) | COMPANY / PERSON |
| What cannot be established? | Unknown/unresolved shortlist | COMPANY / PERSON / SCREENING |
| What materially conflicts? | High-severity findings (titles + type) | FINDINGS |
| What requires action? | Required-actions shortlist | FINDINGS |
| What evidence supports each? | Inline **provenance chip** per line; full record in the **Evidence drawer** | Evidence drawer (in context) / "All sources" browse |

Summary rules:
- Show **high-severity** findings and **material** facts only; everything else
  is one click away.
- Every Summary line is a link to its full context.
- No raw tables, no full evidence excerpts, no charts on Summary.

**Inline provenance chips.** Across Company, Person, Screening, Findings, and the
report, every fact/finding row carries an inline **provenance chip** (source
class + retrieved date) so provenance is legible *without* opening the drawer
(pattern from Moody's Grid / Sayari; `COMPETITIVE-UX-PATTERN-AUDIT.md` §3). The
chip opens the Evidence drawer for the full source record.

**Related parties (lightweight, no graph).** Company and Person may show a
bounded **Related parties** list — directors/officers/owners and linked parties
already within Phase 1 scope — each row carrying relationship type, its state,
and a source, expand-on-demand for the next hop. This is a *list*, never a
force-directed graph or a graph database (audit §7, §10).

### Where `case_context` lives

Imported commercial/management context (`case_context`,
`CLAIMS-EVIDENCE-MODEL.md` §2.10) is **non-evidentiary** and must never sit on
the evidence/findings path. It appears as a clearly-labelled **"Source context"**
area — a small, explicitly non-evidentiary panel on the **Company** tab (buyer/
seller, management reference, product, port, commercial comments, etc.), plainly
marked as retained-not-analysed context, not a finding or a source. It is
**never** shown on EVIDENCE or FINDINGS, and it **never** feeds finding
synthesis. `internal_tier` (T1/T2/…), if displayed at all, is labelled as an
ARIE internal reference and **never** rendered as a Sentinel integrity/risk
rating. The Summary stays free of `case_context` clutter — it answers the five
questions from evidence, not from imported context.

## 5. Analyst vs management actions

| Actor | Can do |
|---|---|
| **Analyst** (`analyst`) | Run/resume investigation, resolve identity, CONFIRM/DISMISS/REQUEST-INFO on findings, ADD NOTE, add analyst-supplied sources, validate evidence. |
| **Management** (`manager`) | Everything an analyst can, plus **FINALISE_REPORT**. Primary consumer of the Final Report view. |

Management does **not** read the whole investigation history: the Final Report
is the management surface (`UI-UX-SPEC.md`). Actions are audited regardless of
actor.

## 6. Navigation alternatives considered (and why rejected)

- **Merge COMPANY+PERSON into "Entities":** rejected — person evidence and
  relationship reasoning deserve their own focus; merging buries the
  person↔company question.
- **Evidence as a drawer, not a primary tab:** **adopted** (revised — was
  previously rejected). The interaction budget and the market norm both favour
  drill-to-source *in context*; the legitimate "browse all captured sources" need
  is met by a **secondary "All sources" view** rather than a primary tab
  (`COMPETITIVE-UX-PATTERN-AUDIT.md` §7). Net tab count: 6 → 5.
- **Findings second (triage-first):** adopted — leads the analyst with the "what
  needs my attention" surface; interaction counts unchanged.
- **A separate ACTIONS tab:** rejected — required actions belong with the
  findings that generate them (FINDINGS) and are summarised on SUMMARY; a
  separate tab fragments the workflow.
- **Screening folded into Findings:** rejected — screening has its own state
  model and adjudication workflow; it warrants a dedicated view, and confirmed
  matches surface as findings anyway.

Net: the **five-tab** IA in §1 (Summary · Findings · Company · Person ·
Screening) plus an in-context Evidence drawer stands.

## 7. Analyst Worklist (Cases)

A quiet table that answers one question — **"what requires my attention now?"**
It is **not a dashboard**: no charts, no vanity stats, no portfolio view, no
aggregate risk score. Columns: entity/input name, contact, investigation state,
completeness, `company_identity_status`, updated timestamp, owner. Sortable.
No metrics tiles above it. Opening a row enters the workspace at SUMMARY.

Filters are each **derived from canonical workflow states** — they add **no new
persisted state**. Each filter and the canonical state it derives from:

| Filter | Derived from |
|---|---|
| **Assigned to me** | owner = current analyst |
| **Needs action** (umbrella) | any actionable sub-state below (derived, **not stored**) |
| **Clarification required** | `intake_state = CLARIFICATION_REQUIRED` |
| **Identity ambiguous** | `company_identity_status = AMBIGUOUS` |
| **Screening review required** | `screening_state = MATCH_REQUIRES_REVIEW` |
| **Findings requiring review** | open (un-adjudicated) findings |
| **Completed** | `investigation_state = COMPLETED` |

**"Needs action"** is a computed umbrella over the actionable sub-states
(clarification required, identity ambiguous, screening review required, findings
requiring review); it is **derived at read time, never a stored state**.
