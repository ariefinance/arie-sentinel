# User Flows

**Status:** Frozen for Phase 1.

Describes the primary journeys through Sentinel. Flows use the canonical states
from `SCREEN-STATES.md` and the IA from `INFORMATION-ARCHITECTURE.md`.

---

## 1. Primary flow (happy path + gates)

```
        ┌─────────────┐
        │ INVESTIGATE │  company_label + contact_label (raw labels) → [Investigate]
        └──────┬──────┘
               │ create investigation (NOT_STARTED)
               ▼
     ┌────────────────────────┐
     │ INTAKE QUALITY GATE     │  assess raw labels BEFORE any discovery
     └───┬──────────────────┬──┘
         │ CLARIFICATION_    │ SUFFICIENT_FOR_DISCOVERY
         │ REQUIRED          ▼
         ▼            ┌──────────────┐   ┌────────────────────┐   ┌──────────────────┐
  ┌──────────────┐   │ NORMALISATION│──▶│ CANDIDATE DISCOVERY│──▶│ IDENTITY         │
  │ INTAKE       │   └──────────────┘   └────────────────────┘   │ RESOLUTION (gate)│
  │ CLARIFICATION│                                                └────────┬─────────┘
  │ stop; ask    │        one entity (CONFIRMED)                           │
  │ minimum      │◀─────────  distinct from AMBIGUOUS  ────────────────────┤
  │ discriminator│                                                         │
  │ NO discovery │                    multiple entities (AMBIGUOUS)        │
  │ NO counter-  │                    analyst selects min. discriminator   │
  │ party        │                    (report generation BLOCKED until     │
  └──────────────┘                     company_identity_status = CONFIRMED)│
     only new input                                                        │
     → SUFFICIENT_FOR_DISCOVERY                       one entity CONFIRMED  ▼
                                              ┌──────────────────────┐
                                              │ INVESTIGATION         │
                                              │ WORKSPACE (Summary)   │
                                              └───────────┬──────────┘
                                                          │ analyst reviews:
                                                          │  FINDINGS / COMPANY /
                                                          │  PERSON / SCREENING
                                                          │  (+ Evidence drawer)
                                                          ▼
                                              ┌────────────────────────┐
                                              │ HUMAN REVIEW            │
                                              │ Confirm / Dismiss /     │
                                              │ Request info / Add note │
                                              └───────────┬────────────┘
                                                          │ company_identity_status
                                                          │ = CONFIRMED + manager
                                                          │ finalises
                                                          ▼
                                              ┌────────────────────────┐
                                              │ FINAL COUNTERPARTY      │
                                              │ INTEGRITY REPORT        │
                                              └────────────────────────┘
```

## 2. Flow A — Investigate (intake)

1. Analyst opens **Investigate**.
2. Enters two fields only — **Company label** (`company_label`) and **Contact
   label** (`contact_label`). Both are captured as **raw management labels**
   (e.g. `Vantar - Castellan`, `NOVEXA - Amara - via Delta Trading`), not
   established identities. They are **immutable** and are never overwritten by
   later resolution, and carry no evidentiary weight. Nothing else is requested.
3. Clicks **Investigate**. The investigation is created (`NOT_STARTED`); the raw
   labels are first assessed by the Intake Quality Gate (Flow A2) before any
   discovery is enqueued.
4. If `intake_state = SUFFICIENT_FOR_DISCOVERY`, jobs run and the analyst is
   taken to the workspace, which streams in as jobs complete
   (`RUNNING` → `PARTIAL_RESULTS` → `COMPLETED`).

Edge: required-field validation inline. No multi-step wizard.

## 3. Flow A2 — Intake Quality Gate & Clarification

Runs on the raw `company_label` + `contact_label` **before any discovery**
(no normalisation, no web/AI search, no entity resolution). See
`SCREEN-STATES.md` §0 and `PHASE-1-SCOPE.md` §2A.

1. The gate assigns `intake_state`:
   - `SUFFICIENT_FOR_DISCOVERY` — input is good enough to begin reliable company
     resolution → proceed to Normalisation → Candidate Discovery → Identity
     Resolution (Flow B).
   - `CLARIFICATION_REQUIRED` — input too poor to *start* discovery (e.g. `TBD`
     + a first name only, or `Unnamed Refinery`).
2. On `CLARIFICATION_REQUIRED`, Sentinel:
   - Returns *"Clarification required — insufficient information to begin
     reliable company resolution."*
   - Asks for **only the minimum useful discriminator**.
   - Launches **no** web/AI discovery, **manufactures no** likely entity, and
     creates **no** counterparty.
3. The state cannot be silently upgraded: **only new analyst input** can move it
   to `SUFFICIENT_FOR_DISCOVERY`, at which point discovery begins.

> **`CLARIFICATION_REQUIRED` ≠ `AMBIGUOUS`.** They have different causes and are
> never merged: `CLARIFICATION_REQUIRED` means the input is too poor to *start*
> discovery (this flow); `AMBIGUOUS` (Flow B) means discovery *ran* and returned
> several plausible entities.

## 3A. Flow A3 — Bulk list import

A secondary intake path for turning a management list into many investigations at
once. It never bypasses the per-row Intake Quality Gate (Flow A2).

1. Analyst chooses **bulk list import** and uploads an **XLSX or CSV** file.
2. **Minimal column mapping** — the analyst maps only the columns needed to seed
   an investigation (at minimum `company_label` and `contact_label`, e.g.
   `Castellan Trading` and `Amara`). Commercial columns (management reference,
   buyer/seller, product, port, etc. — e.g. `REF-207`, `Product-A`) are retained
   as **non-evidentiary `case_context`** only.
3. **Each row becomes its own Investigation** (`NOT_STARTED`) and **independently**
   passes the **Intake Quality Gate** → **Normalisation** → **Candidate
   Discovery** → **Identity Resolution**, exactly as a single investigation would.
   A row with poor labels (e.g. `TBD`, `Unnamed Refinery`) lands in
   `CLARIFICATION_REQUIRED` on its own, without affecting other rows.
4. **Malformed rows are isolated** — a single bad row is reported and skipped; it
   does **not** corrupt or block the other rows in the import.
5. **Re-import of the same file is idempotent** — rows already imported are
   **linked** (and warned about), producing no uncontrolled duplicate
   investigations; the shared Counterparty dedup (§5, `CLAIMS-EVIDENCE-MODEL.md`
   §2.7) still applies to resolved entities.

## 4. Flow B — Identity Resolution (gate)

This is the **`AMBIGUOUS`** case: discovery **ran** (the intake gate passed with
`SUFFICIENT_FOR_DISCOVERY`) and returned more than one plausible legal entity.
It is **distinct from** intake clarification (Flow A2) — do not conflate the two.
Appears **only when needed** (`company_identity_status = AMBIGUOUS`).

1. System presents the candidate legal entities with the **minimum
   discriminator** to tell them apart (jurisdiction, registry no., status).
2. **No option is pre-selected.** The analyst must actively choose, or choose
   "none of these / cannot determine".
3. On selection → `company_identity_status = CONFIRMED`, investigation continues.
4. If the analyst cannot resolve → stays `AMBIGUOUS` (or `NOT_VERIFIED`);
   **Final Report remains blocked**; system records the limitation and required
   action.

Invariant: no code path resolves ambiguity automatically (C1, U4).

## 5. Flow C — Investigation workspace review

Within the workspace the analyst moves across tabs in whatever order, but the
canonical reasoning path is `Summary → Findings → Company → Person → Screening`
(the five-tab bar from `INFORMATION-ARCHITECTURE.md` §1). **Evidence is not a
tab**: it is reached as an **in-context drawer** opened from any fact or finding
(≤2 interactions; the drawer closes back to the originating context in place —
never a page round-trip).

1. **Summary**: read the position in ~2 minutes — verified facts, unknowns,
   material conflicts (high-severity findings), required actions. Each line
   links deeper.
2. **Findings**: act on each finding (triage-first; Findings sits second so the
   read-position → act loop is tight).
3. **Company / Person**: inspect entity and person evidence with states.
   - The raw `contact_label` resolves to **0..N PersonCandidates** (initials, a
     first name, or several people in one field). **Each candidate is
     adjudicated independently** — its own `person_evidence_status` and
     `relationship_state` — and the UI never collapses them into a single person
     verdict (`CLAIMS-EVIDENCE-MODEL.md` §2.9).
   - The resolved **Counterparty is shared**: when this investigation resolves
     to an organisation already resolved by an earlier row, it **links to the
     existing counterparty** (same `identity_key`) rather than creating a
     duplicate (`CLAIMS-EVIDENCE-MODEL.md` §2.7).
4. **Screening**: review matches; adjudicate `MATCH_REQUIRES_REVIEW` →
   `CONFIRMED_MATCH` / dismiss.

**Inline provenance & "why matched".** Every fact/finding row across Findings,
Company, Person, and Screening carries an inline **provenance chip** (source
class + retrieved date) so provenance is legible without opening the drawer;
the chip opens the Evidence drawer for the full source record. Identity
candidates, screening matches, and PersonCandidates additionally show a
plain-language **`match_basis`** ("why matched" — e.g. *"same registration
number"* vs *"name only — weak"*) with the identifiers that drove the match, so
resolution stays visible and reversible (`COMPETITIVE-UX-PATTERN-AUDIT.md` §9
C3–C4; `INFORMATION-ARCHITECTURE.md` §4).

From any fact or finding, evidence is reachable in **≤2 interactions** via the
drawer (U3), which closes back to the originating fact/finding in context. A
secondary **"All sources"** browse (opened from the drawer or a header
affordance) covers the "review everything captured" need without a primary tab.

> **`case_context` is non-evidentiary.** Imported commercial/management context
> (buyer/seller, product, quantity, Incoterm, port, comments) and ARIE internal
> tier are retained for traceability only. They are never Claims, Evidence, or
> Sources, never drive any flow decision, and never influence a finding
> (`CLAIMS-EVIDENCE-MODEL.md` §2.10). Internal tiers never become Sentinel
> risk ratings.

## 6. Flow D — Human review actions

For each finding the analyst can:

| Action | Effect | Guardrail |
|---|---|---|
| `CONFIRM_FINDING` | status → `CONFIRMED` | Audited. |
| `DISMISS_FINDING` | status → `DISMISSED` | **Material (high-severity) dismissal requires a rationale.** Audited. |
| `REQUEST_INFORMATION` | status → `INFO_REQUESTED` | Records what's needed. Audited. |
| `ADD_NOTE` | attaches analyst note | Audited. |

Screening adjudication and evidence validation follow the same audit pattern.

## 7. Flow E — Finalisation

1. Precondition: `company_identity_status = CONFIRMED`. Otherwise **Finalise** is
   disabled with a stated reason. (The report gate is unchanged.)
2. Role: `manager` performs `FINALISE_REPORT`.
3. **No one-click finalise.** An explicit confirmation step guards against
   accidental finalisation.
4. On finalise: the Final Report is generated from stored claims/evidence/
   findings (not free-form), the event is audited, and the case reflects the
   finalised report.

**Report structure.** The report's fixed sections map 1:1 to the eight
management questions (`COMPETITIVE-UX-PATTERN-AUDIT.md` §8), so every question is
immediately answerable:

| # | Management question | Report section |
|---|---|---|
| 1 | Did we resolve the correct legal entity? | **Legal Identity** |
| 2 | What do we know about the named person? | **Named Person(s)** (per PersonCandidate) |
| 3 | Can we establish the person–company relationship? | **Contact Relationship** |
| 4 | Any formal screening concerns? | **Screening** (per screening state) |
| 5 | What material inconsistencies exist? | **Material Findings** |
| 6 | What could not be established? | **Unknown / Unresolved** |
| 7 | What action is required? | **Required Actions** |
| 8 | Material source limitations? | **Research Completeness** (checked-vs-not-established checklist) |

Plus **Verified Facts** (supporting) and an inline provenance chip / Evidence
drill-down on every material statement. Every statement stays **traceable to
stored evidence**; there is **no generic AI executive summary**. Research
Completeness is an explicit **checked-vs-not-established checklist**, not a bare
completeness label.

## 7A. Worklist usage

The **Analyst Worklist** (`INFORMATION-ARCHITECTURE.md` §7) lets an analyst see
which cases need action **without opening each one**. Its filters — Assigned to
me, Needs action, Clarification required, Identity ambiguous, Screening review
required, Findings requiring review, Completed — are **derived from the canonical
workflow states** (no new persisted state); "Needs action" is a derived umbrella
over the actionable sub-states. Opening a row enters the workspace at SUMMARY.

## 7B. Export

Alongside the Final Report, a **secondary structured export** produces a
**CSV/XLSX register** of investigations (e.g. entity/input name, contact,
investigation state, completeness, `company_identity_status`, owner, updated). It
is **licensing-aware**: fields whose source licence does not permit
redistribution are withheld or noted rather than exported. This register is a
secondary output — it does not replace the Final Report as the management
surface.

> Screening consumes provider-supplied **adverse-media event grouping** where the
> provider supplies it, rather than re-deriving that grouping.

## 8. Failure / degraded flows

| Situation | State | UX behaviour |
|---|---|---|
| A material source unreachable | `SOURCE_UNAVAILABLE` / completeness `MATERIAL_SOURCE_UNAVAILABLE` | Name the source + impact; offer retry; report shows limitation. |
| Some steps pending | `PARTIAL_RESULTS` | Show ready sections; mark pending clearly; no fake completeness. |
| Investigation cannot proceed | `FAILED` | State reason + next action (retry / adjust input). |
| Person not evidenced | `NO_RELIABLE_EVIDENCE_LOCATED` | Stated as absence of evidence, never "fake person". |
| Ambiguous person | `IDENTITY_AMBIGUOUS` | Present candidates; do not guess. |

## 9. Permission-gated variations

- `analyst`: all investigation and finding actions; cannot finalise.
- `manager`: all of the above **plus** `FINALISE_REPORT`.
- All actions server-authorised and audited regardless of role
  (`SECURITY-BOUNDARIES.md`).
