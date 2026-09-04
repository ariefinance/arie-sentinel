# UI / UX Specification

**Status (build-readiness gate):** **INTERACTION / IA: FROZEN** — navigation,
workflow, states, interaction budget, the five-tab workspace, evidence drawer,
worklist behaviour, and report information structure are locked for
implementation. **VISUAL DESIGN: SUBJECT TO RENDERED REVIEW** — spacing, colour,
type, and component polish will be reviewed once the first real UI is rendered;
the text wireframes here fix *intent and structure*, not final pixels. No
application code.

**Design objective:** *an analyst understands the counterparty position within
~2 minutes.* The product feels institutional, controlled, evidence-led, calm,
and high-trust. It is a **case-investigation workspace**, not an analytics
dashboard.

Read alongside `DESIGN-SYSTEM.md`, `SCREEN-STATES.md`,
`INFORMATION-ARCHITECTURE.md`, `USER-FLOWS.md`, and `COMPONENT-INVENTORY.md`.

---

## 0. Global conventions (apply to every screen)

- **Persistent case header** on every case screen shows the raw `company_label`
  **and** the resolved counterparty legal name **distinctly** (the raw label is
  never overwritten), the contact label, states, tab bar, and the
  disabled-until-CONFIRMED Final Report action — see
  `INFORMATION-ARCHITECTURE.md` §2. The resolved counterparty is a **shared**
  legal entity that may be **linked across multiple investigations**
  (`CLAIMS-EVIDENCE-MODEL.md` §2.7); where it is, the header indicates the link
  rather than implying a duplicate. The case tab bar is the **five-tab** set
  `SUMMARY · FINDINGS · COMPANY · PERSON · SCREENING`
  (`INFORMATION-ARCHITECTURE.md` §1); **Evidence is not a primary tab** — it
  opens as an in-context drawer (see below).
- **Evidence in context (C1):** evidence opens as an in-context **drawer** from
  any fact or finding — **one interaction**, closing back to the originating
  context and preserving the investigation position (never a page round-trip).
  A secondary **"All sources"** browse view remains available for reviewing
  everything captured (`COMPETITIVE-UX-PATTERN-AUDIT.md` §7, C1).
- **Inline provenance chips (C3):** every fact/finding row across Company,
  Person, Screening, Findings, Summary, and the report shows an inline
  **provenance chip** (source class + retrieved date) so provenance is legible
  without opening the drawer; the chip opens the Evidence drawer for the full
  source record (`COMPETITIVE-UX-PATTERN-AUDIT.md` §3, C3).
- **Match basis (C4):** identity candidates, screening matches, and
  PersonCandidates each show a short plain-language **"why matched"**
  (`match_basis`) plus the identifiers that drove the match (e.g. "registration
  number + jurisdiction match" vs "name only — weak"), keeping resolution
  visible and reversible (`CLAIMS-EVIDENCE-MODEL.md` §2.6, §2.9, C4).
- **Raw labels are not identities.** Intake fields (`company_label`,
  `contact_label`) are raw management/prospect **labels**, not established
  identities (`PHASE-1-SCOPE.md` §2). They are immutable, carry no evidentiary
  weight, and are **always shown distinctly from the resolved entity** — the raw
  label is never overwritten or replaced by the resolved counterparty legal name;
  both are visible.
- **Intake insufficiency ≠ identity ambiguity.** `CLARIFICATION_REQUIRED`
  (intake too poor to *start* discovery, `SCREEN-STATES.md` §0) and `AMBIGUOUS`
  (discovery *ran* and returned several plausible entities, §2) have different
  causes and **are never merged in the UI**: they are separate screens
  (Intake Clarification vs Identity Resolution) with different copy and actions.
- **Truth boundary** always visible: source fact vs counterparty claim vs
  system assessment are visually distinct (`DESIGN-SYSTEM.md` §6).
- **State is text-first**; colour never conveys status alone.
- **Evidence-based language only**; no "safe/fraudulent/genuine/fake/
  suspicious"; no numeric AI confidence.
- Every screen defines **loading / empty / partial / error / disabled** per
  `SCREEN-STATES.md` §8.
- Every mutating action is **audited**; material dismissals need a rationale;
  finalisation is guarded against accidental one-click.
- **Accessibility:** WCAG 2.2 AA intent — keyboard, focus, labels, non-colour
  status, target size (`DESIGN-SYSTEM.md` §11).

The per-screen template used below:
*purpose · target user · primary decision/task · information hierarchy ·
layout · components · controls · loading · error · empty · permissions ·
audit · accessibility · wireframe.*

---

## 1. Investigate screen

- **Purpose:** start an investigation with the minimum possible input.
- **Target user:** analyst.
- **Primary task:** capture the two raw management/prospect **labels** and
  launch. The fields record the `company_label` and `contact_label` exactly as
  management holds them (e.g. `Vantar - Castellan`, `NOVEXA - Amara - via V
  Energy`, `TBD`); they are **not** established identities and are not assumed to
  be clean legal names (`PHASE-1-SCOPE.md` §2).
- **Information hierarchy:** product identity → two raw-label fields → single
  primary action. A **quiet secondary** bulk-intake link sits below and never
  competes with the single investigation. Nothing else competes.
- **Layout:** centred, single column, generous whitespace. No dashboard, no
  tips clutter. The single investigation stays dominant; the bulk-intake
  affordance is a subdued secondary link, not a co-equal button.
- **Components:** intake form (2 fields), primary button, inline validation,
  quiet secondary **[ Import list ]** link (bulk intake), (optional) recent
  cases link.
- **Controls:** `Company` (raw company label, required), `Contact person` (raw
  contact label, required), **[ Investigate ]** (primary). On submit, the Intake
  Quality Gate assesses the labels: `SUFFICIENT_FOR_DISCOVERY` proceeds to
  discovery, `CLARIFICATION_REQUIRED` routes to the Intake Clarification screen
  (§2) — it does not launch discovery or create a counterparty. A secondary
  **[ Import list ]** link opens the Bulk list import screen (§1a) for analysts
  intaking many counterparties at once; it is deliberately understated so the
  single investigation remains the primary action.
- **Loading:** on submit, button → progress; navigates to workspace as case is
  created.
- **Error:** field-level validation; submission error stated plainly with retry.
- **Empty:** n/a (this is the entry point).
- **Permissions:** `analyst` and `manager`.
- **Audit:** case creation recorded (actor, timestamp, inputs).
- **Accessibility:** labelled fields above inputs; error text associated with
  fields; single logical tab order; submit via Enter.

```
┌───────────────────────────────────────────────────────────────┐
│  ARIE Sentinel                                     [ ismael ▾ ] │
│                                                                 │
│                                                                 │
│                Counterparty Integrity — Investigate             │
│                                                                 │
│        Company  (as management recorded it)                     │
│        ┌───────────────────────────────────────────────┐       │
│        │ Vantar - Castellan                              │       │
│        └───────────────────────────────────────────────┘       │
│                                                                 │
│        Contact person  (as management recorded it)              │
│        ┌───────────────────────────────────────────────┐       │
│        │ Jordan Rivera                                        │       │
│        └───────────────────────────────────────────────┘       │
│                                                                 │
│                        [   Investigate   ]                      │
│                                                                 │
│        Import list →   (bulk intake, secondary)                 │
│        Recent cases →                                           │
└───────────────────────────────────────────────────────────────┘
```

---

## 1a. Bulk list import screen

- **Purpose:** intake **many** counterparties at once from a management list,
  where each row becomes a **separate Investigation** that passes the same gates
  as a single investigation — the simplest professional import, **explicitly not
  an ETL / data-mapping platform**.
- **Target user:** analyst (also `manager`).
- **Primary task:** upload an XLSX/CSV, map the minimum columns, and launch one
  investigation per row. No transformation, enrichment, or scripting.
- **Information hierarchy:** upload → minimal column mapping → per-row result
  list. Nothing more; the mapping step is intentionally sparse.
- **Layout:** single column, calm, staged (upload → map → results). No
  dashboard, no charts, no import "designer" canvas.
- **Column mapping (minimal only):** map file columns to **company label**
  (required), **contact label** (required), and an **optional context column**
  captured verbatim as non-evidentiary `case_context`
  (`CLAIMS-EVIDENCE-MODEL.md` §2.10). That is the whole mapping surface — no
  per-field typing, joins, transforms, or formulae. Mapped values are raw
  management/prospect **labels**, never assumed identities (§0; `PHASE-1-SCOPE.md`
  §2).
- **Gate behaviour (never bypassed):** each row is created as its own
  Investigation that runs the **Intake Quality Gate → Normalisation → Candidate
  Discovery → Identity Resolution** exactly as a single investigation would. Bulk
  import creates investigations; it **never** pre-confirms an entity, skips a
  gate, or manufactures a counterparty. A row whose labels are
  `CLARIFICATION_REQUIRED` lands in that state (surfaced later on the Analyst
  Worklist, §1b), not silently dropped.
- **Per-row result list:** every row reports **accepted** (investigation created,
  with its state) or **malformed — rejected** with a plain reason (e.g. missing
  required company/contact label, unreadable row). **Malformed rows are
  isolated** — one bad row never corrupts or blocks the others.
- **Duplicate / re-import safety:** re-importing the **same file** (or rows that
  match an existing investigation on the same raw labels + context) **warns and
  links** to the existing investigation rather than silently creating duplicates;
  the analyst chooses to skip or create anew. De-duplication is at the
  investigation/raw-label level and does **not** pre-resolve or merge legal
  entities.
- **Components:** file drop/upload control, minimal column-mapping selects
  (company / contact / optional context), per-row result table (row ref, mapped
  labels, outcome, reason/link), duplicate-warning rows, primary
  **[ Import <n> rows ]** action.
- **Controls:** **[ Choose file ]** / drop zone (XLSX, CSV), mapping selects,
  **[ Import <n> rows ]**, per-row **[ view ▸ ]** / **[ open existing ▸ ]**
  (duplicates), **[ Cancel ]**.
- **Loading:** upload/parse shows progress; import shows per-row progress as
  investigations are created (`PARTIAL_RESULTS` — accepted rows appear as they
  complete). Nothing blocks on the slowest row.
- **Error:** an unreadable/unsupported file is stated plainly with retry; a
  parse that yields no usable rows returns to upload with the reason. Row-level
  problems are **partial**, not a whole-file error (see result list).
- **Empty:** before upload, the screen states what a valid list needs (a column
  for the company label and one for the contact label; an optional context
  column). An empty/headers-only file is reported as "no rows to import".
- **Partial:** the result list shows accepted **and** malformed-rejected rows
  together with counts; the analyst proceeds with the accepted set while
  malformed rows remain listed with reasons for correction and re-import.
- **Permissions:** `analyst`, `manager`.
- **Audit:** the import is recorded (actor, timestamp, file reference, row
  counts); each accepted row's investigation records its own creation as usual;
  duplicate-link decisions are recorded. No counterparty is confirmed here.
- **Accessibility:** labelled upload control and mapping selects; result table
  with header scope; per-row outcome stated in text (not colour alone); disabled
  **[ Import ]** state announced with reason (WCAG 2.2 AA intent).

```
┌──────────────────────────────────────────────────────────────────────┐
│  Bulk list import                                       [ Cancel ]     │
│  Each row becomes its own investigation and passes the same gates.     │
│  This is a simple import, not a data-mapping platform.                 │
├──────────────────────────────────────────────────────────────────────┤
│  1) File                                                               │
│     ┌────────────────────────────────────────────────────────────┐   │
│     │  counterparties.xlsx        [ Choose file ]  · drop here     │   │
│     └────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  2) Map columns  (minimum only)                                        │
│     Company label   → [ column: "Counterparty" ▾ ]   (required)        │
│     Contact label   → [ column: "Contact"      ▾ ]   (required)        │
│     Context (opt.)  → [ column: "Notes/Ref"    ▾ ]   → case_context     │
│        (non-evidentiary; not analysed)                                 │
│                                                                        │
│  3) Result  (12 rows · 9 accepted · 2 rejected · 1 duplicate)          │
│     Row  Company (raw)         Contact (raw)      Outcome              │
│     ───  ───────────────────   ────────────────   ──────────────────  │
│     1    Vantar - Castellan    Jordan Rivera      Accepted · SUFFICIENT│
│     2    TBD                    Amara              Accepted ·          │
│                                                    CLARIFICATION_REQ.  │
│     3    Castellan Trading FZE  JR                 Accepted · SUFFICIENT│
│     7    (missing)             Amara               Rejected · no       │
│                                                    company label       │
│     8    Unnamed Refinery      (missing)           Rejected · no       │
│                                                    contact label       │
│     9    Vantar - Castellan    Jordan Rivera      Duplicate of         │
│                                                    existing [ open ▸ ] │
│                                                                        │
│  Malformed rows are isolated — they never affect the accepted rows.    │
│                                   [ Import 9 rows ]                     │
└──────────────────────────────────────────────────────────────────────┘
```

> Bulk import is a convenience over the single Investigate flow, not a shortcut
> around it: every accepted row enters the **same** Intake Quality Gate →
> Normalisation → Candidate Discovery → Identity Resolution pipeline (§1, §2, §3)
> and appears on the Analyst Worklist (§1b) in whatever state it reaches. It
> never confirms an entity, skips a gate, or creates duplicates silently.

---

## 1b. Analyst Worklist screen

- **Purpose:** answer one question — **"what requires my attention now?"** — by
  presenting open investigations as a quiet, filterable worklist. This
  **replaces** the informal "Recent cases" list; it is **not** a portfolio
  dashboard.
- **Target user:** analyst (primary), manager (secondary).
- **Primary task:** find the investigations needing the analyst's action and open
  one. Triage, not analytics.
- **Information hierarchy:** filter set (attention-first) → quiet table of
  investigations (raw label, resolved entity where known, state, what's needed,
  last activity) → open.
- **Layout:** single quiet table with a filter row. **No charts, no vanity
  stats, no portfolio or risk score, no aggregate "health" tiles.** Rows are
  calm and text-first.
- **Filters (all DERIVED from canonical states — no new states introduced):**
  - **Assigned to me** — investigations owned by the current analyst.
  - **Needs action** — umbrella over the actionable sub-states below (a derived
    grouping, not a new state).
  - **Clarification required** — intake `CLARIFICATION_REQUIRED` (§2).
  - **Identity ambiguous** — identity `AMBIGUOUS` (§3).
  - **Screening review required** — screening `MATCH_REQUIRES_REVIEW`
    / `POTENTIAL_MATCH` awaiting adjudication (§7).
  - **Findings requiring review** — open findings awaiting CONFIRM / DISMISS /
    REQUEST INFO (§9).
  - **Completed** — investigations at `COMPLETED` (including
    `COMPLETE_WITH_LIMITATIONS`).
  These are **views over existing states**; the worklist coins no state of its
  own.
- **Components:** filter chips/toggles, quiet investigation table (raw label,
  resolved entity, state pill, "needs" summary, last activity, assignee), row
  open affordance. No summary charts or counters beyond a plain per-filter row
  count.
- **Controls:** filter selection, row **[ open ▸ ]**, sort by last activity;
  **[ New investigation ]** and **[ Import list ]** shortcuts back to §1 / §1a.
- **Loading:** table skeleton rows.
- **Error / unavailable:** if the list cannot load, state plainly with retry;
  a per-row state that depends on an unavailable source shows that in text.
- **Empty:** per filter — e.g. "Nothing needs action right now" — stated
  neutrally; never implies everything is "safe".
- **Partial:** rows appear as investigations resolve (`PARTIAL_RESULTS`); a row
  mid-pipeline shows its current state rather than a blank.
- **Permissions:** `analyst`, `manager`; analysts default to **Assigned to me**.
- **Audit:** views are not audited; opening or acting from a row follows that
  screen's audit rules.
- **Accessibility:** filters as a labelled group with announced active state;
  table header scope; state and "needs" in text (not colour alone); single
  logical tab order; WCAG 2.2 AA intent.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Analyst Worklist — what needs my attention now?    [ New ] [ Import ] │
│  [Assigned to me] [Needs action] [Clarification required]              │
│  [Identity ambiguous] [Screening review] [Findings review] [Completed] │
├──────────────────────────────────────────────────────────────────────┤
│  Raw label            Resolved entity        State          Needs      │
│  ───────────────────  ─────────────────────  ─────────────  ─────────  │
│  TBD                  —                       CLARIFICATION  Add        │
│                                               _REQUIRED      discrim. ▸ │
│  Vantar - Castellan   (discovery ran)         AMBIGUOUS      Choose     │
│                                                              entity ▸   │
│  Castellan Trading …  Castellan Trading FZE   SCREENING      Adjudicate │
│                                               review         match ▸    │
│  Vantar - Castellan   Vantar Energy Trading   FINDINGS       Review     │
│                       FZE                      review         findings ▸ │
│  NOVEXA - Amara -     Vantar Energy Trading   COMPLETED_     —          │
│  via Delta Trading    FZE                      WITH_LIMIT.               │
│                                                                        │
│  No charts, no scores — a quiet worklist. Filters are views over the   │
│  canonical states above; they introduce no new state.                  │
└──────────────────────────────────────────────────────────────────────┘
```

> The worklist is a triage surface, not a dashboard: no portfolio view, no risk
> score, no vanity metrics. Every filter is derived from a canonical state
> (`SCREEN-STATES.md`), and "Needs action" is a derived umbrella over the
> actionable sub-states, not a new state.

---

## 2. Intake Clarification screen

- **Purpose:** collect the minimum useful discriminator when the raw labels are
  too poor to begin reliable discovery. **Gate — before discovery.**
- **Target user:** analyst.
- **Primary decision/task:** supply one additional discriminator so intake can
  move from `CLARIFICATION_REQUIRED` to `SUFFICIENT_FOR_DISCOVERY`, or abandon
  the record. This is **not** entity selection.
- **Information hierarchy:** the clarification statement → the single most useful
  discriminator requested → submit. No candidate list (none exist — discovery
  has not run).
- **Layout:** single column, calm, minimal; echoes the raw labels back so the
  analyst sees exactly what was insufficient. No dashboard, no manufactured
  suggestions.
- **Components:** raw-label echo (read-only), one clarification prompt, one or
  two discriminator inputs (only the minimum useful), primary submit.
- **Controls:** discriminator field(s) (e.g. jurisdiction/country, full legal
  name, or a fuller contact name), **[ Continue ]** (disabled until a useful
  discriminator is entered), **[ Cancel ]**. Submitting re-runs the Intake
  Quality Gate; it **does not** launch discovery directly and **never**
  manufactures an entity or creates a counterparty.
- **Loading:** on submit, button → progress while the Intake Quality Gate
  re-assesses; a still-insufficient result returns to this screen with a plain
  restatement of what is missing.
- **Error:** submission error stated plainly with retry; a repeated
  `CLARIFICATION_REQUIRED` outcome is a state, not an error — it re-prompts.
- **Empty:** n/a — this screen appears precisely because intake is
  `CLARIFICATION_REQUIRED`; the raw labels are always present to echo.
- **Permissions:** `analyst`, `manager`.
- **Audit:** `REQUEST_CLARIFICATION` recorded (actor, timestamp, raw labels);
  the supplied discriminator recorded on re-submission. No counterparty is
  created and no discovery is launched from this screen.
- **Accessibility:** clarification message as a labelled region; inputs labelled
  above; continue disabled state announced with reason; single logical tab
  order; submit via Enter.

```
┌──────────────────────────────────────────────────────────────┐
│  Company (raw label): TBD                                      │
│  Contact (raw label): Amara                                    │
│  Intake: CLARIFICATION_REQUIRED   (discovery not started)      │
├──────────────────────────────────────────────────────────────┤
│  More information is required before Sentinel can reliably     │
│  search for the legal entity.                                  │
│                                                                │
│  The company label "TBD" and a first-name-only contact are    │
│  not enough to begin reliable company resolution. Please add   │
│  the minimum needed to identify the company.                   │
│                                                                │
│  Company — full or fuller name                                 │
│  ┌───────────────────────────────────────────────┐            │
│  │                                                 │            │
│  └───────────────────────────────────────────────┘            │
│                                                                │
│  Country / jurisdiction (if known)                             │
│  ┌───────────────────────────────────────────────┐            │
│  │                                                 │            │
│  └───────────────────────────────────────────────┘            │
│                                                                │
│                       [ Continue ] (disabled)   [ Cancel ]     │
└──────────────────────────────────────────────────────────────┘
```

> This is **not** Identity Resolution (§3). No discovery has run, no candidates
> exist, and no entity is manufactured. The raw labels (e.g. `TBD`, or
> `Unnamed Refinery`) are echoed but never overwritten. Sentinel asks only for the
> minimum useful discriminator to reach `SUFFICIENT_FOR_DISCOVERY`.

---

## 3. Identity Resolution screen

- **Purpose:** resolve which legal entity the name refers to. **Gate — after
  discovery.**
- **Target user:** analyst.
- **Primary decision:** select the correct legal entity, or declare it cannot be
  determined.
- **Information hierarchy:** the ambiguity statement → candidate list with the
  minimum discriminator and each candidate's **`match_basis`** ("why matched")
  → explicit choice.
- **Layout:** single column; candidates as a radio list; no data beyond what
  distinguishes them.
- **Match basis (C4):** each candidate shows a short plain-language "why
  matched" (`company_match_basis`) plus the identifiers that drove it — e.g.
  "registration number + jurisdiction match" vs "name only — weak"
  (`CLAIMS-EVIDENCE-MODEL.md` §2.6; `COMPETITIVE-UX-PATTERN-AUDIT.md` C4). It
  keeps resolution visible and reversible; it is a basis, never a numeric score.
- **Components:** identity resolution chooser (each candidate row carries its
  one-line match basis), "cannot determine" option, continue button (disabled
  until a choice is made).
- **Controls:** radio selection (no default), **[ Continue ]**, **[ Cannot
  determine ]**.
- **Loading:** candidate resolution shows a skeleton list.
- **Error:** if candidate lookup fails → `SOURCE_UNAVAILABLE` message + retry.
- **Empty:** if no candidates at all → `NOT_VERIFIED`, explain, offer to
  proceed with limitations (report still blocked).
- **Permissions:** `analyst`, `manager`.
- **Audit:** `RESOLVE_IDENTITY` recorded with the chosen entity.
- **Accessibility:** radio group with fieldset/legend; keyboard selectable;
  continue disabled state announced with reason.

```
┌──────────────────────────────────────────────────────────────┐
│  Vantar Energy Trading FZE · Contact: Jordan Rivera                 │
│  Legal entity: AMBIGUOUS   (report generation blocked)         │
├──────────────────────────────────────────────────────────────┤
│  We found multiple possible legal entities.                    │
│  Select the one you are investigating.                         │
│                                                                │
│  ○  Vantar Energy Trading FZE                                  │
│        UAE · Free Zone · Reg 12345 · Status: Active            │
│        Why matched: registration number + jurisdiction match   │
│                                                                │
│  ○  Vantar Energy Trading Ltd                                  │
│        UK · Companies House 09876543 · Status: Active          │
│        Why matched: name + jurisdiction; reg not corroborated  │
│                                                                │
│  ○  Vantar Energy Trading LLC                                  │
│        USA (DE) · Status: Active                               │
│        Why matched: name only — weak                           │
│                                                                │
│  ○  Cannot determine from available information                │
│                                                                │
│                                   [ Continue ]  (disabled)     │
└──────────────────────────────────────────────────────────────┘
```

> No option is pre-selected. Continue stays disabled until the analyst chooses.
> Selecting a real entity sets `CONFIRMED`; "Cannot determine" keeps the report
> blocked and records a limitation + required action.

> **This is the `AMBIGUOUS` case** (`SCREEN-STATES.md` §2): discovery *ran* and
> returned multiple plausible legal entities. It is **distinct from Intake
> Clarification (§2)**, which handles poor input where discovery has *not*
> started (`CLARIFICATION_REQUIRED`). The two are never merged: here candidates
> exist and the analyst chooses among them; there no candidates exist and the
> analyst supplies a discriminator.

---

## 4. Investigation Summary

- **Purpose:** convey the whole counterparty position in ~2 minutes.
- **Target user:** analyst (primary), manager (secondary).
- **Primary task:** understand verified / unknown / conflicting / required, and
  drill in.
- **Information hierarchy (the five questions, in order):**
  1. What has been verified? 2. What cannot be established? 3. What materially
  conflicts? 4. What requires action? 5. What evidence supports each? (links)
- **Layout:** case header, then five compact sections. **Not a data dump** —
  shortlists only, each line links deeper (`INFORMATION-ARCHITECTURE.md` §4).
- **Components:** verified-facts list, unknown/unresolved list, high-severity
  findings list (type + title + severity), required-actions list, completeness
  banner.
- **Controls:** links into FINDINGS/COMPANY/PERSON/SCREENING; inline provenance
  chips / `(src ▸)` open the Evidence drawer in context; Final Report action in
  header (disabled with reason unless `CONFIRMED`).
- **Loading:** section skeletons; sections appear as jobs complete
  (`PARTIAL_RESULTS`).
- **Error / source unavailable:** completeness banner names the source and
  impact.
- **Empty:** if nothing verified yet → each section states what will populate it.
- **Permissions:** all roles read; finalise is `manager`.
- **Audit:** views not audited; actions from here are.
- **Accessibility:** heading order matches the five sections; high-severity
  findings reachable without excessive scroll (U2).

```
┌──────────────────────────────────────────────────────────────────────┐
│ Raw label: "Vantar Energy Trading"        Investigation: COMPLETED      │
│ Resolved entity: Vantar Energy Trading FZE Completeness: WITH_LIMITATIONS│
│   (UAE Free Zone · Reg 12345) · shared counterparty (2 investigations)  │
│ Contact (raw label): Jordan Rivera                                          │
│ Legal entity: CONFIRMED · Relationship: SELF-ASSERTED                    │
│ [SUMMARY]  FINDINGS  COMPANY  PERSON  SCREENING       [Final Report ▸]  │
│   (Evidence opens as a drawer)                                          │
├──────────────────────────────────────────────────────────────────────┤
│ ⚠ Completeness: COMPLETE_WITH_LIMITATIONS — corporate ownership source  │
│   unavailable for this jurisdiction.                             (why ▸)│
│                                                                        │
│ VERIFIED                                                               │
│  • Legal entity confirmed — UAE Free Zone, Reg 12345, Active   (src ▸) │
│  • Domain vantar-energy.test registered 2025-03-01                (src ▸) │
│                                                                        │
│ CANNOT BE ESTABLISHED                                                  │
│  • Ownership / directors — source unavailable (this jurisdiction)      │
│  • Person↔company relationship — self-asserted only                    │
│                                                                        │
│ MATERIAL CONFLICTS (high severity)                                     │
│  • [INCONSISTENCY] Operating history                            (open ▸)│
│  • [CONTRADICTION] Stated headquarters vs registered address    (open ▸)│
│                                                                        │
│ REQUIRES ACTION                                                        │
│  • Clarify corporate history; obtain supporting evidence               │
│  • Obtain evidence linking Jordan Rivera to the entity                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Company view

- **Purpose:** present the legal entity and corporate facts with provenance.
- **Target user:** analyst.
- **Primary task:** verify identity, registration/status, directors/ownership,
  address, domain relationship.
- **Information hierarchy:** legal identity block → registration/status →
  directors/ownership → address → domain relationship → **Related parties** →
  (optional) imported commercial context. Each datum shows provenance and state.
- **Layout:** case header + labelled fact blocks; quiet tables for
  directors/ownership. Any imported commercial context sits last, in a
  visually-separated, clearly-labelled **non-evidentiary** block.
- **Inline provenance chips (C3):** every fact row carries an inline provenance
  chip (source class + retrieved date) so provenance is legible without opening
  the drawer; the chip opens the Evidence drawer for the full record
  (`INFORMATION-ARCHITECTURE.md` §4; `COMPETITIVE-UX-PATTERN-AUDIT.md` C3).
- **Related parties (C5, lightweight — no graph):** a bounded list of
  directors / officers / owners / linked parties already within Phase 1 scope.
  Each row carries the **relationship type**, its **state**, and a **source**
  (provenance chip), and **expands on demand** for the next hop. It is a *list*,
  **never** a force-directed graph or a graph database
  (`INFORMATION-ARCHITECTURE.md` §4; `COMPETITIVE-UX-PATTERN-AUDIT.md` §7, §10,
  C5).
- **Components:** truth-boundary renderer (source fact vs claim), quiet data
  table, status pills, inline provenance chips, inline evidence links (open the
  drawer), domain-timing note, bounded Related-parties list,
  non-evidentiary `case_context` panel.
- **Imported context (non-evidentiary):** where `case_context` exists
  (buyer/seller, internal tier, product, quantity, Incoterm, port, comments,
  management reference), it may be shown **only** as clearly-labelled
  non-evidentiary context, never as a fact, claim, or finding
  (`CLAIMS-EVIDENCE-MODEL.md` §2.10). ARIE **internal tiers must never render as
  a Sentinel risk/integrity rating**, and commercial terms are **not analysed**
  (Phase 1 scope guard, `PHASE-1-SCOPE.md` §5). It carries no provenance pill
  and never links to evidence.
- **Controls:** open evidence (drawer), links to related findings.
- **Loading:** block skeletons; per-block partial states.
- **Error / unavailable:** per-block `SOURCE_UNAVAILABLE` with impact.
- **Empty:** "No directors/ownership obtainable from available sources" —
  stated as a limitation, not an absence of the fact.
- **Permissions:** all roles read.
- **Audit:** evidence validation actions audited.
- **Accessibility:** tables with header scope; each fact's provenance
  programmatically associated.

```
┌──────────────────────────────────────────────────────────────────────┐
│ (case header)  SUMMARY  FINDINGS  [COMPANY]  PERSON  SCREENING          │
│   (Evidence opens as a drawer)                                          │
├──────────────────────────────────────────────────────────────────────┤
│ LEGAL IDENTITY                                          CONFIRMED       │
│  │ Vantar Energy Trading FZE                                            │
│  │ Registry: UAE Free Zone · No. 12345 · Status: Active                 │
│  │ Incorporated: 14 Feb 2025                                            │
│  │   [corporate_registry · 2026-09-04 · authoritative] (src ▸)          │
│                                                                        │
│ ADDRESS                                                                 │
│  │ Registered: Unit 00, Example Free Zone, UAE                          │
│  │   [corporate_registry · 2026-09-04] (src ▸)                          │
│  » Counterparty claim: "Head office, Dubai Marina"  (claim)            │
│    → see Finding: Stated HQ vs registered address                (▸)   │
│                                                                        │
│ DIRECTORS / OWNERSHIP                                   NOT VERIFIED    │
│  │ Ownership source unavailable for this jurisdiction (limitation)      │
│                                                                        │
│ DOMAIN RELATIONSHIP                                                     │
│  │ vantar-energy.test · registered 2025-03-01                            │
│  │   [domain_registration · 2026-09-04] (src ▸)                        │
│  │ Sentinel assessment: domain registration post-dates incorporation   │
│  │   by ~2 weeks (assessment)                                          │
│                                                                        │
│ RELATED PARTIES  (directors / officers / owners / linked — list, no graph)│
│  │ J. Doe — director (asserted)   SELF-ASSERTED                        │
│  │     [counterparty_asserted · 2026-09-04] (src ▸)          expand ▸  │
│  │ Example Holdings Ltd — parent (reported)   NOT VERIFIED             │
│  │     [press_media · 2026-09-02] (src ▸)                    expand ▸  │
│  │ No further linked parties obtainable from available sources.        │
│  │ Each row: relationship type + state + source; expand for next hop.  │
│                                                                        │
│ IMPORTED CONTEXT — NON-EVIDENTIARY (management-supplied; not analysed)  │
│  │ Buyer/seller: seller · Product: gasoil · Qty: 50,000 MT             │
│  │ Incoterm: CIF · Port: Fujairah · Internal tier: T2                  │
│  │ Not evidence. Internal tier is not a Sentinel risk/integrity rating; │
│  │ commercial terms are not analysed in Phase 1.                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Person view

- **Purpose:** present evidence about the named contact(s) and the
  person↔company relationship, **per candidate**.
- **Target user:** analyst.
- **Primary task:** for each candidate, judge whether that person is credibly
  connected to the entity, on what basis.
- **Information hierarchy:** raw `contact_label` → the **0..N PersonCandidates**
  derived from it → per candidate: person evidence state → located evidence
  (with an inline provenance chip) → `match_basis` ("why matched") →
  relationship state + basis → gaps.
- **Layout:** raw-label echo, then a **candidate list**; each candidate is its
  own block with its own person-evidence and relationship states. Candidates are
  never collapsed into a single person verdict.
- **Inline provenance chips (C3):** each located-evidence row carries an inline
  provenance chip (source class + retrieved date); the chip opens the Evidence
  drawer for the full record.
- **Match basis (C4):** each candidate shows a short plain-language "why
  matched" (`PersonCandidate.match_basis`) plus the identifiers that drove it
  (e.g. "first name + role reference on counterparty site" vs "initials only —
  weak"); it is a basis, never a numeric score
  (`CLAIMS-EVIDENCE-MODEL.md` §2.9, C4).
- **Components:** raw-label echo, per-candidate cards, status pills (person
  evidence 4-state; relationship 5-state — **one pair per candidate**),
  per-candidate match-basis line, truth-boundary renderer, inline provenance
  chips, evidence links (open the drawer).
- **Controls:** open evidence; link to relationship finding — per candidate.
- **Loading / partial / error:** as global.
- **Empty:** if the raw `contact_label` yields **no** candidates, state that no
  person candidate could be derived. Where a candidate has no evidence,
  `NO_RELIABLE_EVIDENCE_LOCATED` is stated as absence of evidence for that
  candidate — never "fake person".
- **Permissions:** all roles read.
- **Audit:** evidence validation audited (per candidate).
- **Accessibility:** state labels textual per candidate; each candidate a
  distinct region; relationship basis explained in text.

```
┌──────────────────────────────────────────────────────────────────────┐
│ (case header)  SUMMARY  FINDINGS  COMPANY  [PERSON]  SCREENING          │
│   (Evidence opens as a drawer)                                          │
├──────────────────────────────────────────────────────────────────────┤
│ Contact (raw label): "NOVEXA - Amara - via Delta Trading"                  │
│ 3 person candidates derived — each assessed independently.             │
│                                                                        │
│ ┌────────────────────────────────────────────────────────────────┐   │
│ │ CANDIDATE 1  from "NOVEXA"                                      │   │
│ │ Why matched: label fragment only — weak                         │   │
│ │ PERSON EVIDENCE                          NO_RELIABLE_EVIDENCE_…  │   │
│ │  │ No reliable evidence located for this name (limitation)       │   │
│ │ RELATIONSHIP (company ↔ person)          UNVERIFIED             │   │
│ └────────────────────────────────────────────────────────────────┘   │
│ ┌────────────────────────────────────────────────────────────────┐   │
│ │ CANDIDATE 2  from "Amara"  (first name only)                    │   │
│ │ Why matched: first name + role reference on counterparty site   │   │
│ │ PERSON EVIDENCE                          LIMITED_EVIDENCE       │   │
│ │  │ Located: role reference on counterparty website (claim)       │   │
│ │  │   [counterparty_asserted · 2026-09-04] (src ▸)                │   │
│ │  │ No independent authoritative reference located (limitation)   │   │
│ │ RELATIONSHIP (company ↔ person)          SELF-ASSERTED          │   │
│ │  │ Basis: counterparty website only; not independently           │   │
│ │  │   corroborated. (assessment)                                  │   │
│ │  │ → Finding: Person relationship unverified               (▸)   │   │
│ └────────────────────────────────────────────────────────────────┘   │
│ ┌────────────────────────────────────────────────────────────────┐   │
│ │ CANDIDATE 3  from "Delta Trading"  (possible separate party)         │   │
│ │ Why matched: name only — multiple persons, cannot disambiguate  │   │
│ │ PERSON EVIDENCE                          IDENTITY_AMBIGUOUS     │   │
│ │  │ Multiple candidate persons; cannot disambiguate (limitation)  │   │
│ │ RELATIONSHIP (company ↔ person)          UNVERIFIED             │   │
│ └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ REQUIRED ACTION                                                        │
│  │ Obtain authoritative or independent evidence for each candidate;    │
│  │ candidates are not merged into a single verdict.                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 7. Screening view

- **Purpose:** present sanctions / PEP / adverse-intelligence results for
  adjudication. **Never auto-decides.**
- **Target user:** analyst.
- **Primary task:** adjudicate matches (`MATCH_REQUIRES_REVIEW` →
  `CONFIRMED_MATCH` or dismiss).
- **Information hierarchy:** overall screening state → match list (subject,
  list/source, match state, **match basis**) → per-match detail + provenance.
- **Layout:** summary line + quiet match table + detail drawer.
- **Match basis (C4):** each match row carries a short plain-language "why
  matched" (`match_basis`) plus the identifiers that drove it (e.g. "name + DOB
  match" vs "name only — weak"), so the analyst sees the strength of the match
  before opening it; it is a basis, never a numeric score
  (`COMPETITIVE-UX-PATTERN-AUDIT.md` C4).
- **Inline provenance chips (C3):** each match row shows source class + retrieved
  date inline; the chip and `open ▸` both open the Evidence drawer.
- **Grouped adverse-media events (provider-aware):** where the provider supplies
  **grouping** for adverse-media results, show **one event row** with its
  article / source count and **expand** to the underlying articles, instead of N
  duplicate rows for the same event. Where the provider gives **no** grouping,
  list the articles **individually** as before — the UI never fabricates
  grouping. Expansion is text-first (an "N articles ▸" affordance, not colour),
  and each underlying article keeps its own provenance chip and Evidence drawer.
- **Components:** screening match row/list, status pills (4-state), per-row match
  basis, inline provenance chips, grouped adverse-media event row with
  expandable article list (provider-supplied grouping only), evidence drawer,
  adjudication controls.
- **Controls:** open match, **[ Confirm match ]**, **[ Dismiss ]** (with
  rationale for material), **[ Request info ]**.
- **Loading:** table skeleton; provider latency shown.
- **Error / unavailable:** `SOURCE_UNAVAILABLE` for the screening provider named
  explicitly; affects completeness.
- **Empty:** `NO_MATERIAL_MATCH` stated plainly ("No material match located"),
  recorded, low emphasis.
- **Permissions:** analyst adjudicates; audited.
- **Audit:** every adjudication recorded with actor + rationale where required.
- **Accessibility:** table semantics; match state textual; drawer focus-trapped.

```
┌──────────────────────────────────────────────────────────────────────┐
│ (case header)  SUMMARY  FINDINGS  COMPANY  PERSON  [SCREENING]          │
│   (Evidence opens as a drawer)                                          │
├──────────────────────────────────────────────────────────────────────┤
│ Screening: POTENTIAL_MATCH — 1 item requires review                     │
│                                                                        │
│  Subject         List / source        State              Match basis    │
│  ──────────────  ──────────────────   ─────────────────  ─────────────  │
│  Global Energy…  Sanctions (adapter)  NO_MATERIAL_MATCH  no match located│
│  J. Doe          PEP (adapter)        MATCH_REQUIRES_REV name + DOB match│
│  Global Energy…  Adverse media        POTENTIAL_MATCH    name only — weak│
│    ▸ 4 articles (provider-grouped) — expand to underlying articles      │
│                                                                        │
│  Where the provider groups adverse-media coverage, one event row shows  │
│  its article count and expands to the underlying articles; with no      │
│  provider grouping, articles are listed individually.                   │
│                                                                        │
│  Each row also shows a provenance chip (source class · retrieved date)  │
│  and an `open ▸` affordance. `open ▸` / the chip open the Evidence      │
│  drawer: matched attributes, source, retrieved timestamp, excerpt, the  │
│  match basis + driving identifiers, limitations, and adjudication       │
│  controls — closing back to this table.                                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 8. Evidence (in-context drawer + "All sources") — surface, not a primary tab

- **Not a primary tab (C1).** Evidence is **not** in the five-tab case bar. Its
  **primary form is an in-context drawer** opened from any fact or finding, with
  a **secondary "All sources" browse** for reviewing everything captured
  (`INFORMATION-ARCHITECTURE.md` §1; `COMPETITIVE-UX-PATTERN-AUDIT.md` §7, C1).
- **Purpose:** reach the source behind any statement without leaving context,
  and (secondarily) browse all captured sources and inspect any one's full
  provenance.
- **Target user:** analyst.
- **Primary task:** verify a conclusion by reaching its source quickly —
  **≤2 interactions from a finding**, and **never a page round-trip**.

### 8a. Evidence drawer (primary form)

- **How it opens:** from any provenance chip, `(src ▸)` link, or a finding's
  EVIDENCE line — **one interaction**. It opens **over the current context**
  (Company / Person / Screening / Findings / Summary) as a side drawer; the tab
  and scroll position behind it are preserved.
- **How it closes:** closes **back to the originating context in place** (no
  navigation back through pages). This satisfies the "finding → evidence ≤2
  interactions" and "return to context" interaction budgets
  (`COMPETITIVE-UX-PATTERN-AUDIT.md` §6).
- **Drill-down fields (retained in full):** source title, source class, source
  URL/reference (where permitted by `license_class`), retrieved timestamp,
  evidence excerpt/data, claim supported/contradicted, analyst validation,
  source limitations.
- **Controls:** **[ Mark validated ]** (analyst); **[ All sources ▸ ]** to open
  the secondary browse; **[ Close ]** returns to context.

### 8b. "All sources" browse (secondary form)

- **Purpose:** the legitimate "review everything captured" need, met **without**
  a primary tab. Reachable from the drawer or a header affordance.
- **Information hierarchy:** source list (class, title, retrieved, supports/
  contradicts what) → source detail (the same drill-down fields as the drawer).
- **Controls:** filter by class; open any source into the same detail view;
  back-link/breadcrumb to the originating finding/fact.

- **Loading / partial / error:** as global.
- **Empty:** "No sources captured yet" with what will populate it.
- **Permissions:** analyst validates; audited.
- **Audit:** validation recorded.
- **Accessibility:** drawer **focus-trapped** while open and focus returns to the
  invoking control on close; reference links clearly labelled; license-restricted
  content indicated in text.

Evidence drawer opened from a finding (primary form):

```
┌──────────────────────────────────────────────────────────────────────┐
│ (case header)  SUMMARY  [FINDINGS]  COMPANY  PERSON  SCREENING          │
├──────────────────────────────────────────┬───────────────────────────┤
│ Findings ▸ Operating history              │ EVIDENCE (drawer)   [Close]│
│  [INCONSISTENCY] Operating history   HIGH │  Title:  UAE Free Zone     │
│  CLAIM    …since 2011                      │         registry record    │
│  EVIDENCE …incorporated 14 Feb 2025 (src▸)│  Class:  corporate_registry│
│  ASSESSMENT …                             │  Ref:    [registry ref]    │
│  ACTION   …                               │  Retrieved: 2026-09-04     │
│                                           │  Excerpt: "Date of         │
│  (drawer opened from EVIDENCE line;       │   incorporation:           │
│   one interaction; closes back here —     │   14 February 2025"        │
│   context and scroll preserved)           │  Supports/Contradicts:     │
│                                           │   contradicts "operating   │
│                                           │   since 2011"              │
│                                           │  Limitations: none noted   │
│                                           │  Validation:[Mark validated]│
│                                           │  [ All sources ▸ ]         │
└──────────────────────────────────────────┴───────────────────────────┘
```

"All sources" browse (secondary form):

```
┌──────────────────────────────────────────────────────────────────────┐
│ All sources (browse)                    Findings ▸ Operating history ▸  │
├───────────────────────────────┬──────────────────────────────────────┤
│ SOURCES              [filter▾] │ SOURCE DETAIL                          │
│  ▸ Registry record             │  Title:  UAE Free Zone registry record │
│    corporate_registry          │  Class:  corporate_registry            │
│  ▸ Website /about              │  Ref:    [registry ref] (permitted)    │
│    counterparty_asserted       │  Retrieved: 2026-09-04 09:12 UTC       │
│  ▸ RDAP vantar-energy.test       │  Excerpt: "Date of incorporation:      │
│    domain_registration         │            14 February 2025"           │
│  ▸ Screening response          │  Supports/Contradicts:                 │
│    sanctions_pep_screening     │    contradicts claim "operating since  │
│                                │    2011"                               │
│                                │  Limitations: none noted               │
│                                │  Analyst validation: [ Mark validated ]│
└───────────────────────────────┴──────────────────────────────────────┘
```

---

## 9. Findings view

- **Purpose:** present every finding in the four-part structure and let the
  analyst act.
- **Target user:** analyst.
- **Primary task:** review, then CONFIRM / DISMISS / REQUEST INFO / ADD NOTE.
- **Information hierarchy:** findings sorted by severity → each as CLAIM /
  EVIDENCE / ASSESSMENT / ACTION → actions.
- **Layout:** stacked finding panels (`DESIGN-SYSTEM.md` §7), high severity
  first.
- **Components:** finding panel, type pill, severity, action bar, evidence
  links, rationale dialog.
- **Controls:** **[ Confirm ]**, **[ Dismiss ]** (rationale required for
  high-severity), **[ Request info ]**, **[ Add note ]**; each finding's
  EVIDENCE links to its source.
- **Loading / partial / error:** as global.
- **Empty:** "No findings" stated neutrally (absence of conflict is not
  "safe").
- **Permissions:** analyst acts; audited.
- **Audit:** every action recorded; material dismissal rationale stored.
- **Accessibility:** each panel a landmark/region; actions keyboard-reachable;
  dialog focus-trapped; status announced.

```
┌──────────────────────────────────────────────────────────────────────┐
│ (case header)  SUMMARY  [FINDINGS]  COMPANY  PERSON  SCREENING          │
│   (Evidence opens as a drawer)                                          │
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ [INCONSISTENCY]  Operating history                    severity: HIGH│ │
│ │ CLAIM      Company website states operations since 2011.           │ │
│ │ EVIDENCE   Current legal entity incorporated 14 Feb 2025. (src ▸)  │ │
│ │ ASSESSMENT The stated history predates formation of the current    │ │
│ │            legal entity. This may reflect predecessor or           │ │
│ │            management experience.                                  │ │
│ │ ACTION     Clarify corporate history and obtain supporting evidence.│ │
│ │ ─────────────────────────────────────────────────────────────────│ │
│ │ [Confirm] [Dismiss] [Request info] [Add note]     status: OPEN     │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ [UNVERIFIED_CLAIM] Person relationship               severity: HIGH│ │
│ │ CLAIM …  EVIDENCE …  ASSESSMENT …  ACTION …          status: OPEN   │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

> Dismissing a HIGH-severity finding opens a rationale dialog; dismissal cannot
> complete without it (audited).

---

## 10. Final Counterparty Integrity Report

- **Purpose:** the management deliverable — understandable in ~2 minutes,
  without reading the investigation history.
- **Target user:** management (`manager`); also analysts.
- **Primary task:** grasp the position and required actions; drill to evidence
  only if desired.
- **Information hierarchy (fixed sections, mapped 1:1 to the eight management
  questions — `COMPETITIVE-UX-PATTERN-AUDIT.md` §8, C6):**
  1. **Legal Identity** — did we resolve the correct legal entity?
  2. **Named Person(s)** *(new)* — what do we know about the named person? One
     block **per PersonCandidate**: what evidence was located (with provenance)
     and its `person_evidence_status`; candidates are never collapsed into a
     single verdict.
  3. **Contact Relationship** — can we establish the person↔company relationship?
  4. **Screening** *(new)* — any formal screening concerns? Stated **per
     screening state**; **confirmed matches highlighted** (text + label, not
     colour alone); where clear, **"No material match located"** stated plainly.
  5. **Material Findings** — what material inconsistencies exist?
  6. **Unknown / Unresolved** — what could not be established?
  7. **Required Actions** — what action is required?
  8. **Research Completeness & Source Limitations** — material source
     limitations, **strengthened to an explicit checked-vs-not-established
     checklist**: which lines of enquiry were completed vs. what could not be
     established and why (not just a completeness label).
  Plus **Verified Facts** (supporting) and **Evidence drill-down** on every
  material statement. **No generic AI executive summary**; every statement stays
  traceable to dated evidence.
- **AI-drafted narrative summary — DEFERRED (not Phase 1):** an AI-drafted
  narrative summary is explicitly **out of Phase 1 scope**. The report stays the
  concise, structured, evidence-led output above with every statement traceable
  to dated evidence; no auto-generated prose narrative is produced.
- **Layout:** clean report document; sections in the order above; each material
  statement links to evidence via the in-context Evidence drawer.
- **Components:** report section blocks (incl. per-candidate Named Person blocks
  and a per-state Screening block), status pills, truth-boundary renderer,
  inline provenance chips, checked-vs-not-established completeness checklist,
  evidence drill-down links (open the drawer), (optional) non-evidentiary
  context block, secondary evidence & findings register export
  (CSV/XLSX, licensing-aware).
- **Imported context (non-evidentiary):** any `case_context` (buyer/seller,
  internal tier, product, quantity, Incoterm, port, comments) may appear only as
  a clearly-labelled non-evidentiary block, never among Verified Facts, Material
  Findings, or Required Actions. Internal tiers must **never** render as a
  risk/integrity rating and commercial terms are **not analysed**
  (`CLAIMS-EVIDENCE-MODEL.md` §2.10; `PHASE-1-SCOPE.md` §5).
- **Controls:** **[ Finalise report ]** (manager, guarded) when
  `company_identity_status = CONFIRMED`; export/print (institutional layout).
  Secondary **[ Export register (CSV/XLSX) ]** produces a structured evidence &
  findings register (see below) — it is **secondary** to the management report,
  never a replacement for it.
- **Evidence & findings register export (secondary, licensing-aware):**
  **[ Export register (CSV/XLSX) ]** emits one structured row per material
  evidence/finding item with columns: **investigation ref · resolved entity ·
  person / contact · claim · finding type · finding status · source class ·
  source ref / URL (where `license_class` permits) · retrieved date · analyst
  decision · required action**. It is **licensing-aware**: it carries **no vendor
  payloads and no restricted source content**; where `license_class` forbids
  reproducing a reference or excerpt, the cell states the restriction rather than
  the content. Available on the workspace and the report; secondary to the
  management report.
- **Precondition / disabled:** report generation is gated on
  `company_identity_status = CONFIRMED`. A `CLARIFICATION_REQUIRED` intake or an
  `AMBIGUOUS` / `NOT_VERIFIED` identity blocks it; the action states why
  (`SCREEN-STATES.md` §9).
- **Loading / partial:** if generated from `PARTIAL_RESULTS`, limitations are
  prominent.
- **Error:** generation failure stated with retry.
- **Empty:** n/a (report exists only post-investigation).
- **Permissions:** finalisation is `manager`; guarded against accidental
  one-click.
- **Audit:** `FINALISE_REPORT` recorded (actor, timestamp).
- **Accessibility:** document structure with proper headings; links labelled;
  print stylesheet preserves state labels (not colour-only).

```
┌──────────────────────────────────────────────────────────────────────┐
│  COUNTERPARTY INTEGRITY REPORT                                          │
│  Resolved entity: Vantar Energy Trading FZE · 2026-09-04               │
│  Raw label: "Vantar Energy Trading" · Contact (raw): Jordan Rivera          │
│  Prepared for management review                                         │
├──────────────────────────────────────────────────────────────────────┤
│  1. LEGAL IDENTITY                                       CONFIRMED      │
│   UAE Free Zone · Reg 12345 · Active · Incorporated 14 Feb 2025 (ev ▸) │
│                                                                        │
│  2. NAMED PERSON(S)   (per candidate — not collapsed)                   │
│   • "Amara" (from contact label)          LIMITED_EVIDENCE       (ev ▸)│
│      Located: role reference on counterparty site; no independent ref.  │
│   • "NOVEXA"                             NO_RELIABLE_EVIDENCE_LOCATED  │
│   • "Delta Trading"                            IDENTITY_AMBIGUOUS            │
│                                                                        │
│  3. CONTACT RELATIONSHIP                                 SELF-ASSERTED  │
│   Relationship asserted by counterparty; not independently corroborated.│
│                                                                        │
│  4. SCREENING                                            POTENTIAL_MATCH│
│   • Sanctions (entity): No material match located.                     │
│   • PEP (J. Doe): MATCH_REQUIRES_REVIEW — name + DOB match      (ev ▸) │
│   • Adverse media (entity): POTENTIAL_MATCH — name only, weak   (ev ▸) │
│   (Confirmed matches, if any, are highlighted with a text label.)       │
│                                                                        │
│  5. MATERIAL FINDINGS                                                   │
│   • [INCONSISTENCY] Operating history — website 2011 vs incorp 2025 (ev▸)│
│   • [CONTRADICTION] Stated HQ vs registered address                (ev▸)│
│                                                                        │
│  6. UNKNOWN / UNRESOLVED                                                │
│   • Directors / ownership · Independent person↔company link             │
│                                                                        │
│  7. REQUIRED ACTIONS                                                    │
│   1. Clarify corporate history with supporting evidence.               │
│   2. Obtain authoritative evidence of the contact relationship.        │
│                                                                        │
│  8. RESEARCH COMPLETENESS & SOURCE LIMITATIONS   COMPLETE_WITH_LIMIT.   │
│   Checked / established:                                                │
│    ✓ Legal entity & registration (corporate_registry)                  │
│    ✓ Domain registration timing (RDAP)                                 │
│    ✓ Sanctions/PEP/adverse-media screening run                         │
│   Not established / could not be verified:                             │
│    ✗ Directors / ownership — source unavailable for this jurisdiction  │
│    ✗ Independent person↔company link — only self-asserted located      │
│    ✗ Contact identity for "NOVEXA" / "Delta Trading" — no reliable evidence │
│                                                                        │
│  VERIFIED FACTS  (supporting)                                          │
│   • Legal entity, registration, status (corporate_registry)       (ev▸)│
│   • Domain registration date (domain_registration)                (ev▸)│
│                                                                        │
│  EVIDENCE DRILL-DOWN → every (ev ▸) opens the source in the Evidence   │
│  drawer with full provenance. No AI executive summary.                  │
│  (AI-drafted narrative summary is DEFERRED — not Phase 1.)              │
├──────────────────────────────────────────────────────────────────────┤
│   [ Export register (CSV/XLSX) ] (secondary)  [ Finalise report ]      │
│                                               (manager · confirms)     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 11. Screen → primary-question map (quick reference)

The case workspace is a **five-tab** bar
(`SUMMARY · FINDINGS · COMPANY · PERSON · SCREENING`); **Evidence is not a
primary tab** — it is an in-context **drawer** (plus a secondary "All sources"
browse), reachable in ≤2 interactions from any finding. The pre-workspace
surfaces (Investigate, Bulk list import, Analyst Worklist, and one of Intake
Clarification / Identity Resolution) and the Final Report sit outside the tab
bar.

| # | Screen / surface | In tab bar? | Answers first |
|---|---|---|---|
| 1 | Investigate | no (entry) | (start) — capture raw company + contact labels |
| 1a | Bulk list import | no (entry, secondary) | Intake many rows at once — one investigation per row, same gates |
| 1b | Analyst Worklist | no (triage) | What requires my attention now? (views over canonical states) |
| 2 | Intake Clarification | no (pre-discovery gate) | Is the input good enough to start? (`CLARIFICATION_REQUIRED`) |
| 3 | Identity Resolution | no (post-discovery gate) | Which legal entity? (`AMBIGUOUS`; shows `match_basis`) |
| 4 | Summary | **tab 1** | Overall position in ~2 min |
| 5 | Findings | **tab 2** | What needs my judgment and action? |
| 6 | Company | **tab 3** | Who is the entity? (identity, status, ownership, domain, related parties) |
| 7 | Person | **tab 4** | Who are the candidate(s), and is each link real? (per-candidate `match_basis`) |
| 8 | Screening | **tab 5** | Any sanctions/PEP/adverse match? (per-row `match_basis`) |
| — | Evidence (drawer + "All sources") | **no — drawer** | What source establishes this? (opened in context from any fact/finding) |
| — | Final Report | no (management deliverable) | Management-facing conclusion + actions |

**Final Report → eight management questions (1:1):**

| # | Management question | Report section |
|---|---|---|
| 1 | Did we resolve the correct legal entity? | Legal Identity |
| 2 | What do we know about the named person? | Named Person(s) *(per candidate)* |
| 3 | Can we establish the person–company relationship? | Contact Relationship |
| 4 | Any formal screening concerns? | Screening *(per state)* |
| 5 | What material inconsistencies exist? | Material Findings |
| 6 | What could not be established? | Unknown / Unresolved |
| 7 | What action is required? | Required Actions |
| 8 | Material source limitations? | Research Completeness & Source Limitations *(checked-vs-not-established checklist)* |

> Intake Clarification (2) and Identity Resolution (3) are distinct gates and
> are never merged: poor input before discovery vs multiple entities after
> discovery.
>
> Findings sits second in the tab bar (triage-first); Evidence is a drawer, not
> a tab (`INFORMATION-ARCHITECTURE.md` §1; `COMPETITIVE-UX-PATTERN-AUDIT.md`
> §7).
