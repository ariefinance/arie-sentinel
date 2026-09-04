# Component Inventory

**Status:** Frozen for Phase 1 (components may be refined, not expanded).
Implementation-neutral catalogue of every UI component required for Phase 1's
nine screens. This is a design/spec artifact, **not** code — no framework, no
TypeScript, no styling values. It fixes each component's *purpose, placement,
inputs, states, accessibility, and variants*.

All state names are the canonical enums from `SCREEN-STATES.md`. All truth-boundary
and finding rules trace to `DESIGN-SYSTEM.md` and `CLAIMS-EVIDENCE-MODEL.md`. All
placement traces to `INFORMATION-ARCHITECTURE.md`.

---

## 0. Global rules every component honours

These are non-negotiable and are **not** repeated in full under each component.

1. **Colour never conveys state alone.** Every status carries a text label; icon
   and position are reinforcement. All status treatments remain legible in
   greyscale and under common colour-vision deficiencies (`SCREEN-STATES.md`
   cross-cutting rule; `DESIGN-SYSTEM.md` §4).
2. **Evidence-based language only.** Never "safe", "fraudulent", "genuine",
   "fake", or "suspicious". Positive states state the evidentiary fact only
   (e.g. "Legal entity confirmed"), never reassurance (`DESIGN-SYSTEM.md` §4).
3. **No numeric AI confidence.** Provenance is expressed as the three classes
   `authoritative` · `reported` · `inferred` (`CLAIMS-EVIDENCE-MODEL.md` §2.2).
4. **Truth boundary is visible.** Source fact, counterparty claim, and system
   assessment are visually distinct everywhere (`DESIGN-SYSTEM.md` §6).
5. **WCAG 2.2 AA intent.** Full keyboard operability, a visible focus ring on
   every interactive element, programmatic labels and error association on forms,
   heading/landmark order matching the visual hierarchy, target size ≥24×24px,
   reduced-motion respected (`DESIGN-SYSTEM.md` §11).
6. **Universal states.** Where a component fetches or gates data it must define
   Loading, Empty, Partial, Error, Disabled, and Source-unavailable behaviour per
   `SCREEN-STATES.md` §8 (see the universal state components in §22–25).

### The nine Phase 1 screens (placement reference)

| # | Screen | Global / case |
|---|---|---|
| 1 | Investigate (intake) | Global |
| 2 | Cases (list) | Global |
| 3 | Case ▸ SUMMARY | Case tab (1st) |
| 4 | Case ▸ COMPANY | Case tab (3rd) |
| 5 | Case ▸ PERSON | Case tab (4th) |
| 6 | Case ▸ SCREENING | Case tab (5th) |
| 7 | Case ▸ EVIDENCE | Case (in-context **drawer** from any fact/finding + secondary "All sources" browse — **not** a tab) |
| 8 | Case ▸ FINDINGS | Case tab (2nd) |
| 9 | Final Report | Case (gated view) |

Screen numbers above are stable placement IDs, **not** tab order. The case tab
bar (§3) carries five tabs in this order: `SUMMARY · FINDINGS · COMPANY · PERSON
· SCREENING` (Findings sits second). Evidence remains a Phase 1 surface but is
reached as an in-context drawer, not a tab (`INFORMATION-ARCHITECTURE.md` §1;
audit §7).

The Identity Resolution gate (§9) is a case-level gate surfaced over SUMMARY /
COMPANY, not a tenth screen.

---

## 1. App shell / global navigation

**Purpose.** The thin global chrome that hosts every screen and carries the two
top-level destinations. Sentinel is a workspace, not a suite — no dashboard, no
analytics landing, no metric tiles (`INFORMATION-ARCHITECTURE.md` §1).

**Where used.** All nine screens (persistent frame).

**Key inputs.**
- Active destination (`Investigate` | `Cases`).
- Current user identity and role indicator (`analyst` | `manager`).
- ARIE wordmark (restrained; single accent — `DESIGN-SYSTEM.md` §10).

**States.**
- Default (a destination active).
- Loading — shell renders immediately; the *content region* shows the relevant
  Loading skeleton (§22), never a blank frame.

**Accessibility.**
- `<nav>` landmark with an accessible name ("Global").
- Destinations are links; active one carries `aria-current="page"` (not colour
  alone — weight + marker reinforce).
- Skip-to-content link as the first focusable element.
- Role indicator is text, exposed to assistive tech.

**Variants.** None. Two destinations only; the set is frozen.

---

## 2. Case header (persistent)

**Purpose.** Read-at-a-glance orientation present on every case screen. Shows the
resolved entity, contact, and the case-level state machine, hosts the case tab
bar, and presents the Final Report action gated with reason
(`INFORMATION-ARCHITECTURE.md` §2).

**Where used.** Screens 3–9 (every case screen; also rendered above the Final
Report view).

**Key inputs.**
- Raw + resolved company identity, rendered via the Raw-label vs resolved-identity
  renderer (§27): the immutable `company_label` is always shown, alongside the
  resolved Counterparty `legal_name` when `company_identity_status = CONFIRMED`.
  When not confirmed, the raw label stands alone, explicitly marked as the
  supplied label (not a verified name).
- Raw `contact_label` (immutable), with resolved PersonCandidates surfaced on
  PERSON (§28), not collapsed into a single name here.
- `intake_state` (2-value: `SUFFICIENT_FOR_DISCOVERY` | `CLARIFICATION_REQUIRED`),
  via Status pill (§4 intake-quality group).
- `investigation_state` (6-value), rendered via Status pill.
- `completeness_state` (3-value), via Status pill.
- `company_identity_status` (3-value: `CONFIRMED` | `AMBIGUOUS` | `NOT_VERIFIED`),
  via Status pill (§4 legal-entity group). Meaningful only once
  `intake_state = SUFFICIENT_FOR_DISCOVERY`.
- `relationship_state` — surfaced per PersonCandidate on PERSON (§28), not as a
  single case-level pill.
- Linked-investigations indicator (§30) where the Counterparty is shared.
- Active tab (for the embedded Case tab bar, §3).
- Final Report enablement + disabled reason.

**States.**
- Default — all state pills present.
- Loading — pills render as skeleton chips (§22) while the case loads; entity
  name skeleton if the name is still resolving.
- Partial — when `investigation_state = PARTIAL_RESULTS`, the pill reads
  "Partial results"; header does not imply completeness.
- Source unavailable — when a material source failed, the header pairs with a
  case-level Alert/banner (§17); the completeness pill reflects
  `MATERIAL_SOURCE_UNAVAILABLE`.
- Disabled (Final Report action) — see below.

**Final Report action (disabled-with-reason).**
- Enabled **iff** `company_identity_status = CONFIRMED` (`SCREEN-STATES.md` §9
  gate).
- When disabled it remains visible and focusable, is `aria-disabled`, and states
  the reason in text, e.g. "Final Report disabled: legal entity is AMBIGUOUS",
  "… is NOT_VERIFIED", or — at the intake gate — "Final Report disabled:
  clarification required before discovery can run". A `CLARIFICATION_REQUIRED`
  intake also blocks the report (no discovery has run, no counterparty exists).
  The reason is exposed to assistive tech (not tooltip-only).
- Enablement never bypasses the intake or identity gate (§6, §26).
  (§26 is the Intake Clarification surface; §6 the Identity resolution chooser.)

**Accessibility.**
- `<header>` region with an accessible name (the entity/input name).
- State pills are Status pills (§4) — label-led, greyscale-safe.
- Heading order: entity name is the case H1.

**Variants.**
- *Resolved* (raw label + resolved `legal_name`, `CONFIRMED`) vs *Unresolved*
  (raw label alone, labelled as supplied, `AMBIGUOUS` / `NOT_VERIFIED`) vs
  *Clarification pending* (raw label alone, `intake_state =
  CLARIFICATION_REQUIRED`, discovery not run).

---

## 3. Case tab bar

**Purpose.** Primary navigation within a case. Fixed five-tab set in fixed order
(`INFORMATION-ARCHITECTURE.md` §1). Evidence is **not** a tab — it is the
in-context Evidence drawer (§13), opened from any fact/finding.

**Where used.** Embedded in the Case header (§2); on every case tab screen
(SUMMARY, FINDINGS, COMPANY, PERSON, SCREENING).

**Key inputs.**
- Ordered tabs: `SUMMARY · FINDINGS · COMPANY · PERSON · SCREENING`. **Findings
  sits second** (triage-first: read the position on Summary, then act on what
  needs judgment) per `COMPETITIVE-UX-PATTERN-AUDIT.md` §7 (C2).
- Active tab.
- Optional per-tab count/marker where meaningful (e.g. open findings), rendered
  as text, not a coloured badge alone.

**States.**
- Default, Active (current tab).
- Loading — tab labels present; the panel below shows the tab's Loading skeleton.

**Accessibility.**
- ARIA tabs pattern: `role="tablist"`, each tab `role="tab"` controlling a
  `role="tabpanel"`.
- Current tab: `aria-selected` / `aria-current` **and** weight + underline (not
  colour alone — `DESIGN-SYSTEM.md` §5).
- Left/Right arrow keys move between tabs; Enter/Space activates; focus visible.

**Variants.** None — the five-tab set is frozen
(`INFORMATION-ARCHITECTURE.md` §1, §6).

---

## 4. Status pill

**Purpose.** The single, canonical way to render any state. Label-led: `● LABEL`
where the dot/icon reinforces and the **word is the message**
(`DESIGN-SYSTEM.md` §4). Greyscale-safe.

**Where used.** Everywhere state appears — Case header, Cases list, Screening
rows, Finding panel status, Evidence provenance, banners.

**Key inputs.**
- State value (from one of the canonical enums).
- Semantic tone slot: `attention` | `caution` | `positive` | `info` | `neutral`
  (muted; label-paired — `DESIGN-SYSTEM.md` §4).
- Icon token (shape reinforcement).
- Size (default | compact for dense tables).

**States.** The pill *is* the state display; it has no independent loading/error
state (it renders inside a skeleton when its host is loading).

**Accessibility.**
- The label text is the accessible name; the icon is decorative
  (`aria-hidden`) with meaning carried by the word.
- Tone meets ≥3:1 non-text / ≥4.5:1 text contrast; distinguishable by
  label + icon + shape without colour.

**Variants — canonical state → label / icon / tone.**
Icons are described by shape (implementation picks the glyph; shape must survive
greyscale). Tone is muted reinforcement only.

Intake quality (`SCREEN-STATES.md` §0) — assessed by the Intake Quality Gate on
the raw labels *before* discovery runs:

| State | Label | Icon shape | Tone |
|---|---|---|---|
| `SUFFICIENT_FOR_DISCOVERY` | Sufficient for discovery | filled check | positive |
| `CLARIFICATION_REQUIRED` | Clarification required | question mark | caution |

> This group is **distinct** from the legal-entity `AMBIGUOUS` pill (below):
> `CLARIFICATION_REQUIRED` means the input is too poor to *start* discovery,
> whereas `AMBIGUOUS` means discovery *ran* and returned several plausible
> entities (`SCREEN-STATES.md` §0). They use different labels and icon shapes
> (question mark vs branching/fork) and must never be merged or styled alike.

Investigation lifecycle (`SCREEN-STATES.md` §1):

| State | Label | Icon shape | Tone |
|---|---|---|---|
| `NOT_STARTED` | Not started | hollow circle | neutral |
| `RUNNING` | Investigation running | progressing arc | info |
| `PARTIAL_RESULTS` | Partial results | half-filled square | caution |
| `SOURCE_UNAVAILABLE` | Source unavailable | broken-link | caution |
| `COMPLETED` | Completed | filled check | positive |
| `FAILED` | Investigation failed | filled triangle | attention |

Legal entity (`SCREEN-STATES.md` §2):

| State | Label | Icon shape | Tone |
|---|---|---|---|
| `CONFIRMED` | Legal entity confirmed | filled check | positive |
| `AMBIGUOUS` | Legal entity ambiguous | branching/fork | caution |
| `NOT_VERIFIED` | Legal entity not verified | hollow circle | caution |

Person evidence (`SCREEN-STATES.md` §3):

| State | Label | Icon shape | Tone |
|---|---|---|---|
| `IDENTITY_EVIDENCE_FOUND` | Identity evidence found | filled check | positive |
| `LIMITED_EVIDENCE` | Limited evidence | half-filled square | caution |
| `IDENTITY_AMBIGUOUS` | Identity ambiguous | branching/fork | caution |
| `NO_RELIABLE_EVIDENCE_LOCATED` | No reliable evidence located | hollow circle | neutral |

Relationship (`SCREEN-STATES.md` §4):

| State | Label | Icon shape | Tone |
|---|---|---|---|
| `VERIFIED` | Relationship verified | filled check | positive |
| `CORROBORATED` | Relationship corroborated | double check | info |
| `SELF_ASSERTED` | Self-asserted | quote mark | caution |
| `UNVERIFIED` | Unverified | hollow circle | neutral |
| `CONTRADICTED` | Contradicted | crossed bars | attention |

Research completeness (`SCREEN-STATES.md` §5):

| State | Label | Icon shape | Tone |
|---|---|---|---|
| `COMPLETE` | Complete | filled check | positive |
| `COMPLETE_WITH_LIMITATIONS` | Complete with limitations | check + asterisk | caution |
| `MATERIAL_SOURCE_UNAVAILABLE` | Material source unavailable | broken-link | caution |

Screening (`SCREEN-STATES.md` §7):

| State | Label | Icon shape | Tone |
|---|---|---|---|
| `NO_MATERIAL_MATCH` | No material match | hollow circle | neutral |
| `POTENTIAL_MATCH` | Potential match | half-filled square | caution |
| `MATCH_REQUIRES_REVIEW` | Match requires review | flag | attention |
| `CONFIRMED_MATCH` | Confirmed match | filled flag | attention |

Finding review status (`SCREEN-STATES.md` §6):

| State | Label | Icon shape | Tone |
|---|---|---|---|
| `OPEN` | Open | hollow circle | info |
| `CONFIRMED` | Confirmed | filled check | attention |
| `DISMISSED` | Dismissed | strikethrough | neutral |
| `INFO_REQUESTED` | Information requested | outbound arrow | caution |

Finding severity (`SCREEN-STATES.md` §6) — rendered as a distinct severity marker
(§10), also label-led:

| Severity | Label | Reinforcement |
|---|---|---|
| `high` | High | full bar / triple mark |
| `medium` | Medium | two-thirds bar / double mark |
| `low` | Low | one-third bar / single mark |

---

## 5. Intake form + Investigate button

**Purpose.** Create a new investigation from exactly two **raw labels**
(`CLAIMS-EVIDENCE-MODEL.md` §2.6: `company_label`, `contact_label`) and start the
investigation. The form captures labels **as supplied** — it never asserts them
as identities and never rewrites them.

**Where used.** Screen 1 (Investigate).

**Key inputs.**
- Company label (`company_label`, required) — free text exactly as management
  recorded it (e.g. `NORDIC-HALCYON`, `Vantar - Castellan`, `Unnamed Refinery`, `TBD`).
  Field copy frames it as a label to search, not a verified name.
- Contact label (`contact_label`, required) — free text; may be a full name, a
  first name, initials, or several people at once; captured verbatim (resolves
  later to 0..N PersonCandidates, §28).
- Submit action ("Investigate").

**States.**
- Default (empty, actionable).
- Validating / inline error — field-level messages, error text associated with
  the field; no placeholder-as-label (`DESIGN-SYSTEM.md` §5).
- Disabled (submit) — until required fields are non-empty; reason stated.
- Submitting — button shows in-progress; on success the investigation is created
  and passes through the Intake Quality Gate. On `SUFFICIENT_FOR_DISCOVERY` it
  routes to SUMMARY (`NOT_STARTED` / `RUNNING`); on `CLARIFICATION_REQUIRED` it
  surfaces the Intake Clarification panel (§26) — **no** discovery runs and
  **no** counterparty is created.
- Error — creation failed: what failed + recovery (retry), via Error state (§24).

**Accessibility.**
- Labels above inputs, programmatically associated; required state announced.
- One primary button per view ("Investigate").
- Error summary receives focus; each field error is linked with
  `aria-describedby`.

**Variants.** None.

---

## 6. Identity resolution chooser

**Purpose.** The gate shown when `company_identity_status = AMBIGUOUS`: presents the
candidate entities so an analyst adjudicates. Multiple plausible entities cannot
be silently resolved by any code path (`SCREEN-STATES.md` §2, §9). Records a
`RESOLVE_IDENTITY` audit event.

**Where used.** Case-level gate over SUMMARY / COMPANY (screens 3–4); blocks the
Final Report while unresolved.

**Key inputs.**
- Ordered list of candidate entities, each with a **minimum discriminator** —
  the smallest set of fields that tells candidates apart (e.g. registry ID,
  jurisdiction, incorporation date, status), rendered with Mono IDs.
- A **match-basis line** (§32) per candidate — a short "why matched" plus the
  driving identifiers (`COMPETITIVE-UX-PATTERN-AUDIT.md` C4), keeping the choice
  visible and reversible; never a numeric score.
- Each candidate's provenance (source class of the authoritative match), shown via
  an inline provenance chip (§31).
- Confirm-selection action; each candidate links to its Evidence.

**States.**
- Default — **no candidate pre-selected** (no default selection); Confirm is
  disabled with reason until one is chosen.
- Loading — candidate skeleton rows.
- Empty — no candidates located → routes toward `NOT_VERIFIED` handling with a
  stated next action, not a blank.
- Error — resolution source failed; recovery stated.
- Disabled (Confirm) — "Select a candidate to resolve identity".

**Accessibility.**
- A radio group (`role="radiogroup"`) with an accessible name; each candidate is
  a radio option; arrow keys move within the group; nothing checked initially.
- The discriminator fields are readable per option (not colour/position only).

**Variants.** None. (This gate never auto-decides; it only records an analyst's
choice.)

---

## 7. Verified-facts list / Unknown-unresolved list

**Purpose.** The two Summary shortlists answering "What is verified?" and "What
cannot be established?" — concise, material items only, each a link to full
context; no raw tables or excerpts inline (`INFORMATION-ARCHITECTURE.md` §4).

**Where used.** Screen 3 (SUMMARY). Drill-down homes: COMPANY / PERSON /
SCREENING.

**Key inputs.**
- Ordered list of shortlist items (material only), each with: short statement,
  truth-boundary kind (source fact vs system assessment — rendered via §11),
  provenance class where a source fact, and a link target.

**States.**
- Default.
- Loading — line skeletons.
- Empty — Verified: "No facts established yet" with why; Unknown: "Nothing
  outstanding" — explanatory, never an ambiguous void (§23).
- Partial — when investigation is `PARTIAL_RESULTS`, a divider separates ready
  items from a "pending" note (§25 partial pattern).

**Accessibility.**
- Rendered as a list; each line is a link with descriptive text.
- Source facts vs assessments distinguished via the Truth-boundary renderer, not
  colour alone.

**Variants.**
- *Verified-facts* (positive/neutral, source-fact treatment).
- *Unknown/unresolved* (neutral/caution, states what would establish it).

---

## 8. Finding panel

**Purpose.** The canonical rendering of a Finding: four fixed, always-labelled
regions **CLAIM / EVIDENCE / ASSESSMENT / ACTION**, plus type pill, severity,
review actions, and review status. Never collapsed into a one-line verdict
(`DESIGN-SYSTEM.md` §7; `CLAIMS-EVIDENCE-MODEL.md` §2.5).

**Where used.** Screen 8 (FINDINGS) primarily; high-severity finding titles are
summarised (title + type only) on SUMMARY and drill in here. Confirmed findings
also surface from SCREENING.

**Anatomy (mirrors `DESIGN-SYSTEM.md` §7).**

```
┌───────────────────────────────────────────────┐
│ [TYPE pill]  Title                 [severity]   │
├───────────────────────────────────────────────┤
│ CLAIM        What was stated.                   │
│ EVIDENCE     What sources establish. [source ▸] │
│ ASSESSMENT   Why it needs attention.            │
│ ACTION       What ARIE should do next.          │
├───────────────────────────────────────────────┤
│ [Confirm] [Dismiss] [Request info] [Add note]   │
│ status: OPEN                                     │
└───────────────────────────────────────────────┘
```

**Key inputs.**
- `finding_type` (§ SCREEN-STATES §6): `CONTRADICTION` | `INCONSISTENCY` |
  `UNVERIFIED_CLAIM` | `ANOMALY` | `INSUFFICIENT_EVIDENCE` → Type pill.
- `severity`: `high` | `medium` | `low` → severity marker (§10).
- `title`.
- `claim_text` / `evidence_text` / `assessment_text` / `action_text` — the four
  regions (always present, always labelled).
- Related evidence link(s) → open Evidence drawer (§13) within two interactions.
- `review_status`: `OPEN` | `CONFIRMED` | `DISMISSED` | `INFO_REQUESTED` →
  Status pill.
- Embedded Finding action bar (§9-review actions live below).

**States.**
- Default (any review status).
- Loading — four labelled regions render as skeleton lines (labels stay so the
  structure is legible while text loads).
- Partial — EVIDENCE region may note "Evidence pending" when a source is still
  running; the region is never omitted.
- Error — if a region's underlying data failed to load, the region states the
  failure and recovery inline; the finding is not silently dropped.
- Disabled — action bar disabled states handled in §9.

**Accessibility.**
- The panel is an article/region named by its title; the four region labels are
  real labels (headings or `dt`/`dd`-style), readable in order.
- Type pill and status pill are label-led; severity marker is label + shape, not
  colour alone.
- EVIDENCE region's `[source ▸]` is a link/button with an accessible name naming
  the source.

**Variants.**
- By `finding_type` (type pill wording/icon changes; structure identical).
- Compact reference (SUMMARY) = title + type pill only, linking to the full panel.

---

## 9. Finding action bar

**Purpose.** The review controls on a Finding: `CONFIRM_FINDING`,
`DISMISS_FINDING`, `REQUEST_INFORMATION`, `ADD_NOTE`. Enforces
rationale-required-on-material-dismissal and no-accidental-finalise behaviour.
Every action writes an audit event (`CLAIMS-EVIDENCE-MODEL.md` §2.7).

**Where used.** Inside the Finding panel (§8), screen 8; wherever a finding is
actioned.

**Key inputs.**
- Finding id + current `review_status` + `severity`.
- Actor role (`analyst` | `manager`) — both may review findings
  (`INFORMATION-ARCHITECTURE.md` §5).
- Handlers: Confirm → `CONFIRMED`; Dismiss → `DISMISSED`; Request info →
  `INFO_REQUESTED`; Add note → opens Note composer (§21).

**Behaviour rules.**
- **Rationale required on material dismissal.** `DISMISS_FINDING` on
  `severity = high` opens a Confirmation dialog (§20) that captures a mandatory
  rationale; the audit event's `rationale` must be non-null (`SCREEN-STATES.md`
  §9; `CLAIMS-EVIDENCE-MODEL.md` §2.7). Dismiss cannot complete without it.
- **No accidental finalise / no accidental destructive action.** Dismissal (and
  finalise, §20) require an explicit, non-accidental confirmation step; single
  stray clicks never commit an irreversible/material change
  (`DESIGN-SYSTEM.md` §5; `SCREEN-STATES.md` §9).

**States.**
- Default (actions available per current status).
- Disabled — an action not valid for the current status is disabled with reason
  (e.g. "Already dismissed"); reason exposed to assistive tech.
- In-progress — the acting button shows progress; others locked until it settles.
- Error — action failed: what failed + retry (§24); status is not changed
  optimistically past a failure.

**Accessibility.**
- Buttons with clear text labels; destructive Dismiss visually distinct and
  confirmed.
- Focus moves into the Confirmation dialog / Note composer on open and returns
  on close.

**Variants.** None (the four actions are the frozen review set).

---

## 10. Severity marker

**Purpose.** Render finding `severity` (`high` | `medium` | `low`) as a
label-led, greyscale-safe marker distinct from the Type pill and Status pill.

**Where used.** Finding panel header (§8); high-severity findings on SUMMARY.

**Key inputs.** `severity` value; size (default | compact).

**States.** Display-only.

**Accessibility.** Label ("High"/"Medium"/"Low") is the accessible name; a bar or
stepped-mark shape reinforces; never colour alone.

**Variants.** Three (per §4 severity table).

---

## 11. Truth-boundary renderer

**Purpose.** Render any statement in exactly one of three visually distinct
treatments so an analyst tells them apart at a glance, without colour
(`DESIGN-SYSTEM.md` §6). Driven mechanically by the claim/evidence model, not by
prose.

**Where used.** Everywhere statements appear — Summary shortlists, COMPANY /
PERSON facts, Finding regions, the Evidence drawer / All-sources browse, the
Final Report.

**Key inputs.**
- Kind, derived from data:
  - **Source fact** — from Evidence whose Claim `asserted_by = source`
    (`CLAIMS-EVIDENCE-MODEL.md` §2.3).
  - **Counterparty claim** — Claim `asserted_by = counterparty`.
  - **System assessment** — Claim/finding `asserted_by = system`.
- For source facts: source chip (title + `source_class`) and provenance class
  (`authoritative` | `reported` | `inferred`).
- Statement text.

**Treatments (mandatory, per `DESIGN-SYSTEM.md` §6).**

| Kind | Treatment | Example label |
|---|---|---|
| Source fact | Solid left rule, neutral/positive, source chip attached | "Registry — authoritative" |
| Counterparty claim | Quoted style, distinct claim marker, muted | "Counterparty claim" |
| System assessment | Distinct assessment marker, labelled as Sentinel's reasoning | "Sentinel assessment" |

**States.**
- Default.
- Partial — a source fact whose source is still being captured shows the claim
  with an "evidence pending" note rather than promoting it to a fact.

**Accessibility.**
- The kind is announced in text (the label), not signalled by rule/quote styling
  alone; source chip is readable; provenance is one of the three named classes,
  never a number.

**Variants.** Three kinds (above); source-fact variant additionally varies by
provenance class label.

---

## 12. Quiet data table

**Purpose.** The institutional table used for companies, directors, and screening
detail rows: light row separation, no zebra noise, right-aligned numerics,
monospace IDs, sortable headers, sticky header on scroll (`DESIGN-SYSTEM.md` §5).

**Where used.** COMPANY (entity / directorship / ownership / address rows),
PERSON (person-role rows), SCREENING (match rows via §16), EVIDENCE (source
list). Also the base for the Cases list (§15).

**Key inputs.**
- Column definitions (label, alignment, type: text | numeric | mono-ID | status |
  timestamp | link).
- Rows.
- Sort state (column + direction).
- Row-open handler (drill to detail / drawer) where applicable.

**States.**
- Default.
- Loading — header present; body shows skeleton rows (§22).
- Empty — explains why and what would populate it (e.g. "No directors located"),
  never a blank grid (§23).
- Partial — ready rows shown with a divider and a "pending" note for sections
  still running (§25).
- Error — states what failed to load + retry (§24), header retained.

**Accessibility.**
- Semantic table with `<th scope>`; sortable headers are buttons exposing
  `aria-sort`; sort is keyboard-operable.
- Sticky header remains associated with cells; Mono IDs are plain text (readable
  character-by-character).
- Status cells use Status pills (§4).

**Variants.**
- *Companies / entity facts*, *directors*, *ownership*, *addresses*, *person
  roles*, *screening detail* — same component, different column sets. Numeric
  columns right-aligned; ID columns mono.

---

## 13. Evidence drawer (primary evidence surface)

**Purpose.** The **primary** way evidence is reached in Sentinel: an in-context
drawer presenting a single piece of Evidence and its Source with full provenance,
opened directly from any fact or finding in **one interaction** and closing back
to the originating context in place (`INFORMATION-ARCHITECTURE.md` §1, §3, §6;
`COMPETITIVE-UX-PATTERN-AUDIT.md` §7, C1). Evidence is drill-to-source *in
context*, not a separate destination — there is no primary Evidence tab. The
"review everything captured" need is met by the secondary **All-sources browse
view** (§13a), not by this drawer.

**Opening / closing (interaction budget).**
- Opened in **1 interaction** from an inline provenance chip (§31), a Summary
  line, a COMPANY/PERSON fact, a Finding EVIDENCE region, a screening match row,
  or a related-parties row.
- **Closes back to the exact originating context** (Esc or close returns focus to
  the trigger; the case tab and scroll position are preserved) — no page
  round-trip (satisfies the "return to context" interaction budget, audit §6).

**Where used.** Opened inline from Summary items, COMPANY/PERSON facts, Finding
EVIDENCE regions, screening match rows, related-parties rows, and every inline
provenance chip (§31). Also the detail surface reached from the All-sources
browse view (§13a).

**Key inputs.** (`CLAIMS-EVIDENCE-MODEL.md` §2.1–2.2, §2.4)
- Source `title`.
- `source_class` (Phase 1 controlled vocabulary — §3 of the claims model).
- Reference (`origin_ref`, where license permits) — Mono where an ID.
- `retrieved_at` timestamp (Mono).
- `excerpt`.
- Relation to the claim: `supports` | `contradicts` | `partially_supports` |
  `context`.
- Provenance / `extraction_confidence`: `authoritative` | `reported` |
  `inferred` (never numeric).
- Analyst validation control + current validation state.
- Source `limitations` (staleness, partial access, jurisdiction).
- Optional version / `supersedes` indicator (versioned source).

**States.**
- Default.
- Loading — drawer skeleton with the field labels retained.
- Empty — reached where no evidence record exists yet: "No evidence captured yet"
  with why (§23).
- Error — capture/render failed: what failed + retry (§24).
- Source unavailable — the source could not be reached: names the source and its
  effect on completeness (§26), rather than showing a fabricated excerpt.
- Disabled (validation control) — when the actor lacks the action; reason stated.

**Accessibility.**
- Drawer is a dialog: focus moves in on open, is trapped, returns to the trigger
  on close; Esc closes and restores the originating context.
- Breadcrumb back to the originating finding/fact (e.g. `Findings ▸ Operating
  history ▸ Evidence`).
- `supports` / `contradicts` shown as text labels; source class and provenance
  are text; no colour-only signalling.

**Variants.**
- *Drawer* (inline drill-down, the primary form) — dialog behaviour + breadcrumb
  back to the originating context. The same evidence content is also rendered as
  a *detail record* opened from the All-sources browse view (§13a). There is no
  primary-tab card list.

---

## 13a. All-sources browse view (secondary)

**Purpose.** The **secondary** evidence surface: a browsable list of everything
captured for the case, meeting the legitimate "review all sources" need without
reinstating a primary Evidence tab (`INFORMATION-ARCHITECTURE.md` §1, §6; audit
§7). It is a browse-and-filter list, never the default landing surface — the
primary path to any single source is the in-context drawer (§13).

**Where used.** Opened as a secondary view from a header affordance or from the
Evidence drawer (§13) — not a tab in the case tab bar (§3).

**Key inputs.**
- The case's captured sources/evidence rows, built on the Quiet data table (§12):
  source `title`, `source_class`, `retrieved_at` (Mono), relation to claim
  (`supports` | `contradicts` | `partially_supports` | `context`), provenance
  class (`authoritative` | `reported` | `inferred`, never numeric), and
  `limitations`.
- Filter/sort controls (by source class, relation, retrieved date).
- Row-open handler → opens the Evidence drawer (§13) for the full record.

**States.**
- Default.
- Loading — skeleton rows (§22).
- Empty — "No evidence captured yet" with why (§23).
- Partial — ready rows with a divider and "pending" note (§25).
- Error — list failed to load + retry (§24).
- Source unavailable — a specific source that failed is named with its
  completeness impact (§26), never rendered as a clean negative.

**Accessibility.**
- Built on the Quiet data table (§12): `aria-sort` headers, keyboard sort/filter,
  source class and relation as text; row activation via keyboard opens the drawer.

**Variants.** None. (Browse list only; single-record detail lives in the drawer.)

---

## 14. Screening match row / list

**Purpose.** Present sanctions/PEP/adverse screening results. The system proposes;
a human adjudicates — screening **never auto-decides** (`SCREEN-STATES.md` §7).

**Where used.** Screen 6 (SCREENING); confirmed matches also surface as findings
(§8). Built on the Quiet data table (§12).

**Key inputs.**
- Per row: matched name/alias, list/programme, reference (Mono), match state, an
  inline provenance chip (§31), and a link to the underlying Evidence (§13).
- A **match-basis line** (§32) per row — a short "why matched" plus the driving
  identifiers (e.g. "name + DOB" vs "name only — weak") in words, never a numeric
  score (`COMPETITIVE-UX-PATTERN-AUDIT.md` C4).
- Match state: `NO_MATERIAL_MATCH` | `POTENTIAL_MATCH` | `MATCH_REQUIRES_REVIEW`
  | `CONFIRMED_MATCH` → Status pill (§4 screening variants).
- Adjudication action (routes `MATCH_REQUIRES_REVIEW` for human decision; records
  the analyst's determination; audited).
- For adverse-media results **where the provider supplies event grouping**, rows
  are rendered as **Grouped adverse-media event rows** (§37) — one event with an
  article/source count expanding to the underlying articles — instead of one flat
  row per article; with no provider grouping, results render as individual rows
  here.

**States.**
- Default (any match state).
- Loading — skeleton rows (§22).
- Empty — "No screening matches located" (explicit, per `SCREEN-STATES.md` §8),
  which corresponds to `NO_MATERIAL_MATCH` at case level.
- Error — screening adapter failed: what failed + impact + retry (§24).
- Source unavailable — screening source unreachable: named, with completeness
  impact (§26); state is not silently treated as "no match".
- Disabled (adjudication) — reason stated; the system never sets
  `CONFIRMED_MATCH` on its own.

**Accessibility.**
- Table rows; match state via label-led Status pill; adjudication controls
  keyboard-operable with clear labels.

**Variants.**
- Row *emphasis* follows state: `NO_MATERIAL_MATCH` low emphasis;
  `MATCH_REQUIRES_REVIEW` / `CONFIRMED_MATCH` high emphasis — expressed by label
  and position, reinforced (not carried) by tone.

---

## 15. Cases list table

**Purpose.** The quiet table of investigations the user can access; opening a row
enters the workspace at SUMMARY. No metric tiles above it
(`INFORMATION-ARCHITECTURE.md` §7).

> **Upgraded by the Analyst worklist (§35).** This plain list is retained as the
> table base; the default Cases surface is now the Analyst worklist (§35), which
> adds state-derived filter chips over this same column set without adding charts,
> stats, or a risk score.

**Where used.** Screen 2 (Cases).

**Key inputs.** (columns) entity/input name, contact, `investigation_state`,
`completeness_state`, `company_identity_status`, updated timestamp (Mono), owner.
Sortable; filterable by state.

**States.**
- Default.
- Loading — skeleton rows (§22).
- Empty — no cases yet / none match the filter: explains and offers "Investigate"
  (§23).
- Error — list failed to load + retry (§24).

**Accessibility.**
- Built on the Quiet data table (§12): `aria-sort` headers, keyboard sort, state
  cells as Status pills; filter controls labelled; row activation via keyboard.

**Variants.** None (single column set, per IA §7).

---

## 16. Alert / banner (case-level)

**Purpose.** Communicate case-level conditions that affect the whole workspace:
**source unavailable** and the **ambiguous-identity gate** (`DESIGN-SYSTEM.md`
§5; `INFORMATION-ARCHITECTURE.md` §2).

**Where used.** Below the Case header on affected case screens (3–9).

**Key inputs.**
- Variant (see below).
- Message: for source-unavailable — the named source + its effect on
  completeness; for ambiguous identity — that the Final Report is blocked and the
  path to resolve (opens §6).
- Optional action (e.g. "Resolve identity", "Retry source").
- Dismissible flag (dismissible only where safe).

**States.**
- Default (shown while the condition holds).
- Not dismissible — for gating conditions (ambiguous identity) that must persist
  until resolved.

**Accessibility.**
- Appropriate live-region role (status vs alert) by urgency; message is text-first
  with an icon reinforcement; action is a labelled button; dismiss control
  labelled where present.

**Variants.**
- *Source unavailable* — pairs with `SOURCE_UNAVAILABLE` /
  `MATERIAL_SOURCE_UNAVAILABLE`; names the source and completeness impact.
- *Ambiguous-identity gate* — pairs with `company_identity_status = AMBIGUOUS`; states
  the Final Report block and links to the Identity resolution chooser (§6);
  non-dismissible until resolved.

---

## 17. Audit / history timeline

**Purpose.** A quiet, chronological, read-only record of every state change and
analyst action: actor, action, timestamp, and rationale where present
(`DESIGN-SYSTEM.md` §9; `CLAIMS-EVIDENCE-MODEL.md` §2.7). A record to trust, not
a feature to show off.

**Where used.** Within a case (history view / drawer accessible from the case
workspace); rationale entries surface alongside the findings they concern.

**Key inputs.** Per event: `actor` (analyst id or `system` / `adapter:<name>`),
`action` (`CONFIRM_FINDING` | `DISMISS_FINDING` | `REQUEST_INFORMATION` |
`ADD_NOTE` | `FINALISE_REPORT` | `RESOLVE_IDENTITY` | `STATE_CHANGE` | …),
`target_ref`, `created_at` (Mono), `rationale` (shown where non-null).

**States.**
- Default.
- Loading — skeleton entries (§22).
- Empty — "No recorded activity yet" (§23).
- Error — history failed to load + retry (§24).

**Accessibility.**
- Ordered list read chronologically; actor/action/timestamp use Label + Mono
  roles; read-only (no interactive commit here).

**Variants.** None. Append-only presentation of a single event stream.

---

## 18. Final report layout blocks

**Purpose.** The management surface: the Final Report composed of fixed section
components. Generatable **iff** `company_identity_status = CONFIRMED`
(`SCREEN-STATES.md` §9; `CLAIMS-EVIDENCE-MODEL.md` §2.6 invariant). Management
reads this, not the whole investigation history (`INFORMATION-ARCHITECTURE.md` §5).

**Where used.** Screen 9 (Final Report).

**Section blocks (each an implementation-neutral component).** The sections map
**1:1 to the eight management questions** and appear in that order
(`COMPETITIVE-UX-PATTERN-AUDIT.md` §8, C6), with supporting blocks after them.

| # | Block | Management question | Content | Sourced from |
|---|---|---|---|---|
| — | Report header | — | Entity (`CONFIRMED` name), contact, case ref, generated timestamp, finalised-by | Case + audit |
| 1 | Legal Identity | Did we resolve the correct legal entity? | Resolved legal entity facts + `company_identity_status` | COMPANY (source facts) |
| 2 | **Named Person(s)** — *new* | What do we know about the named person? | **Per PersonCandidate** (§28): `person_evidence_state`, `relationship_state`, and each candidate's match-basis (§32); never collapsed into one verdict | PERSON |
| 3 | Contact Relationship | Can we establish the person–company relationship? | `relationship_state` + basis | Relationship reasoning |
| 4 | **Screening** — *new* | Any formal screening concerns? | **Per screening state**: screening state + adjudicated matches, each with match-basis (§32) | SCREENING (§14) |
| 5 | Material Findings | What material inconsistencies exist? | Confirmed / material findings, four-region form retained | FINDINGS (§8) |
| 6 | Unknown / Unresolved | What could not be established? | Outstanding unknowns/unresolved shortlist | Verified/Unknown lists (§7) |
| 7 | Required Actions | What action is required? | Outstanding actions shortlist | FINDINGS actions |
| 8 | **Research Completeness** — *checklist* | Material source limitations? | An explicit **checked-vs-not-established checklist** (each item marked *checked* or *not established*, with the reason it could not be established), replacing a single completeness label; caveats prominent when `MATERIAL_SOURCE_UNAVAILABLE` | Completeness state |
| — | Verified Facts (supporting) | — | Supporting source facts, truth-boundary preserved (§11) | COMPANY / PERSON |
| — | Provenance / audit reference | — | Sources cited with class + retrieved timestamps (inline provenance chips §31 on material statements) | Evidence / audit |

No generic AI executive summary. Every material statement stays traceable to
evidence via the Evidence drawer (§13) and carries an inline provenance chip
(§31).

**States.**
- Default (finalised or draft-preview).
- Disabled / unavailable — when not `CONFIRMED`, the report cannot be generated;
  the view states the reason and points to the identity gate (mirrors the header
  disabled action, §2).
- Loading — section skeletons (§22).
- Partial — a section whose data is limited shows the limitation inline rather
  than omitting the section; the Research Completeness checklist marks the
  affected items "not established" with the reason.

**Accessibility.**
- Proper heading hierarchy and landmark structure; sections navigable; truth
  boundary preserved in the report (source fact vs counterparty claim vs system
  assessment via §11); provenance as named classes, never numeric.

**Variants.**
- *Complete* vs *Complete with limitations* — the Research Completeness checklist
  gains prominence and its "not established" items are surfaced up front; no other
  structural change.

---

## 19. Confirmation dialog

**Purpose.** Capture an explicit, non-accidental confirmation for irreversible or
material actions — **finalise** and **material (high-severity) dismissal
rationale capture** (`SCREEN-STATES.md` §9; `DESIGN-SYSTEM.md` §5).

**Where used.** Finalise action (Case header §2 / Final Report §18); material
dismissal from the Finding action bar (§9).

**Key inputs.**
- Variant (finalise | material-dismissal).
- Summary of what will happen (and that it is irreversible where applicable).
- For material dismissal: a **required rationale** field (must be non-null —
  becomes the audit event `rationale`).
- For finalise: role check (`manager` only) and an explicit confirm step.
- Confirm / Cancel handlers.

**States.**
- Default (open).
- Disabled (Confirm) — until the required rationale is entered (material
  dismissal) or the confirmation step is explicitly completed (finalise); reason
  stated.
- In-progress — committing; controls locked.
- Error — the action failed on commit: what failed + retry (§24); nothing is
  finalised/dismissed on failure.

**Accessibility.**
- Modal dialog: focus trapped, moves to the dialog on open, returns to trigger on
  close; Esc cancels (never confirms); confirm/cancel clearly labelled;
  destructive confirm visually distinct.

**Variants.**
- *Finalise report* — `manager` role, requires `CONFIRMED` entity, explicit
  non-accidental confirmation (`SCREEN-STATES.md` §9).
- *Material dismissal* — mandatory rationale captured and written to audit.

---

## 20. Note composer

**Purpose.** Capture an analyst note (`ADD_NOTE`) against a finding or case;
writes an audit event (`CLAIMS-EVIDENCE-MODEL.md` §2.7).

**Where used.** Finding action bar (§9) and case-level where notes are permitted.

**Key inputs.** Target (`target_ref`), note text, submit/cancel; actor recorded
as author.

**States.**
- Default.
- Disabled (submit) — empty note; reason stated.
- In-progress — saving.
- Error — save failed + retry (§24); the note is not lost on failure.

**Accessibility.**
- Labelled multi-line field (no placeholder-as-label); submit/cancel labelled;
  opens with focus, returns focus on close.

**Variants.** None. (Distinct from the rationale field in §19, which is mandatory
and dismissal-scoped.)

---

## Universal state components (`SCREEN-STATES.md` §8)

These four are reusable primitives every data-bearing component composes with.
Naming here matches the canonical universal-state vocabulary.

## 21. Loading skeleton

**Purpose.** Placeholder that states *what is being fetched*; never a blank, never
a spinner without context (`SCREEN-STATES.md` §8; `DESIGN-SYSTEM.md` §8).

**Where used.** Every fetching component (tables, header pills, finding panels,
evidence cards, report sections, timeline, lists).

**Key inputs.** Shape hint (line | row | card | pill | section); an accessible
description of what is loading.

**States.** Loading only (transitions to Default / Empty / Error).

**Accessibility.** Exposes a busy state with a text description of what is being
fetched; respects reduced-motion (no essential info conveyed by motion).

**Variants.** By shape hint (matches the host component's layout).

---

## 22. Empty state

**Purpose.** Explain *why there's nothing* and *what would populate it* — never an
ambiguous void (`SCREEN-STATES.md` §8). Uses canonical empty wording where
defined (e.g. "No screening matches located").

**Where used.** Every list/table/card region that can be empty.

**Key inputs.** Reason text; optional next action (e.g. "Investigate").

**States.** Empty only.

**Accessibility.** Text-first explanation; any action is a labelled control.

**Variants.** By host (Cases, Evidence, Screening, Findings, timeline, shortlists)
— wording differs; structure identical.

---

## 23. Error state

**Purpose.** State *what failed, the impact, and the recovery action*. No raw
stack traces; no swallowed errors (`SCREEN-STATES.md` §8).

**Where used.** Any component whose fetch or commit can fail.

**Key inputs.** What failed (plain language), impact on completeness where
relevant, recovery action (retry / alternative).

**States.** Error only.

**Accessibility.** Announced appropriately (alert where the failure is
consequential); recovery action is a labelled, keyboard-operable button.

**Variants.** *Load error* vs *commit/action error* (the latter guarantees no
partial state change — the underlying value is unchanged on failure).

---

## 24. Disabled state

**Purpose.** State *why* an action is unavailable, e.g. "Finalise disabled: legal
entity is AMBIGUOUS" (`SCREEN-STATES.md` §8, §9). Applies to any gated control.

**Where used.** Final Report action (§2), Finalise / Confirm (§19), Identity
Confirm (§6), Finding actions (§9), form submits (§5, §20).

**Key inputs.** Reason text (references the blocking state by its canonical name).

**States.** Disabled only.

**Accessibility.** `aria-disabled` with the reason exposed to assistive tech (not
tooltip-only); the control remains discoverable/focusable so the reason is
reachable.

**Variants.** None structurally; the reason string varies with the gate.

---

## 25. Source-unavailable treatment

**Purpose.** The universal "material source could not be reached" presentation:
names the source and its effect on completeness (`SCREEN-STATES.md` §8). Pairs
with `SOURCE_UNAVAILABLE` / `MATERIAL_SOURCE_UNAVAILABLE`.

**Where used.** Case-level via the Alert/banner (§16); inline in Evidence (§13)
and Screening (§14) where a specific source failed.

**Key inputs.** Source name/class; impact on completeness; optional retry.

**States.** Source-unavailable only.

**Accessibility.** Text-first; names the source; distinguishes "unavailable" from
"no result found" so an absent source is never read as a clean negative.

**Variants.** *Case-level* (banner) vs *inline* (within a specific table/card).

---

## 26. Intake clarification panel

**Purpose.** The surface shown when the Intake Quality Gate returns
`intake_state = CLARIFICATION_REQUIRED`: the raw labels are too poor to *begin*
reliable company resolution (e.g. `TBD`, `Unnamed Refinery`). It states that discovery
has **not** run and captures **only** a minimum useful discriminator so the
investigation can move to `SUFFICIENT_FOR_DISCOVERY`. It is **distinct** from the
Identity resolution chooser (§6), which handles `AMBIGUOUS` *after* discovery ran
(`SCREEN-STATES.md` §0, §9; `PHASE-1-SCOPE.md` §2A).

**Where used.** Screen 1 (Investigate) immediately after submit when the gate
returns `CLARIFICATION_REQUIRED`; also surfaced over the case on SUMMARY while the
investigation remains in that state (no discovery has run, so there is no full
workspace yet).

**Key inputs.**
- The immutable raw `company_label` and `contact_label` as supplied (via §27),
  shown so the analyst sees exactly what was recorded.
- Fixed message: *"More information is required before Sentinel can reliably
  search for the legal entity."* (Evidence-based, non-judgmental — never implies
  the label is fake or invalid.)
- A single minimum-discriminator field (e.g. jurisdiction, city/port, or a fuller
  company name) — the *smallest* useful addition, not a full re-intake form.
- Submit ("Add detail") and cancel/leave-as-is actions.

**Behaviour rules.**
- **No discovery, no manufactured entity, no counterparty** while
  `CLARIFICATION_REQUIRED` holds — the panel launches no web/AI investigation
  (`SCREEN-STATES.md` §9 intake gate).
- The state **cannot be silently upgraded**: only new analyst input moves it to
  `SUFFICIENT_FOR_DISCOVERY`. Submitting a discriminator re-runs the gate; it may
  clear or may remain `CLARIFICATION_REQUIRED`.
- Records a `REQUEST_CLARIFICATION` audit event
  (`CLAIMS-EVIDENCE-MODEL.md` §2.11).

**States.**
- Default (awaiting the discriminator).
- Disabled (submit) — until the discriminator field is non-empty; reason stated
  (§24).
- In-progress — re-assessing the gate; controls locked.
- Error — the gate re-assessment failed: what failed + retry (§23).

**Accessibility.**
- Labelled single-field form (label above, associated; no placeholder-as-label);
  the fixed message is a heading/region announced to assistive tech.
- Clearly **not** presented as a candidate chooser — a text field, never a radio
  group (contrast with §6), so the two gates are not confused.

**Variants.** None. (Single discriminator capture; distinct from §6.)

---

## 27. Raw-label vs resolved-identity renderer

**Purpose.** Always render the immutable raw `company_label` **alongside** and
**visually distinct from** the resolved Counterparty `legal_name`, so the analyst
never mistakes what management typed for a verified identity. The raw label is
never overwritten by resolution (`CLAIMS-EVIDENCE-MODEL.md` §1A, §2.6).

**Where used.** Case header (§2), SUMMARY, and the Final Report header (§18);
anywhere the company is named.

**Key inputs.**
- Raw `company_label` (immutable), explicitly marked as the supplied label.
- Resolved Counterparty `legal_name` where `company_identity_status = CONFIRMED`
  (with registry class/id available for drill-down via §12/§13).
- `company_identity_status` (drives which parts render).

**Treatments.**
- The raw label carries an explicit "as supplied" text marker and a distinct,
  quieter typographic treatment; the resolved legal name is the prominent,
  authoritative identity with its Legal-entity Status pill (§4). Distinction is by
  label + typographic role, **never colour alone**.
- When not `CONFIRMED`, only the raw label renders, marked as supplied; no
  resolved name is shown or implied (no manufactured identity).

**States.**
- *Confirmed* — raw label + resolved legal name (both visible, distinct).
- *Unresolved* (`AMBIGUOUS` / `NOT_VERIFIED`) — raw label alone, "as supplied".
- *Clarification pending* (`CLARIFICATION_REQUIRED`) — raw label alone, with a
  note that discovery has not run.
- Loading — label renders immediately; the resolved-name slot is a skeleton (§21).

**Accessibility.**
- Both strings are real text with their roles announced ("supplied label" vs
  "resolved legal entity"); the distinction is not conveyed by styling alone.

**Variants.** The three status-driven treatments above.

---

## 28. PersonCandidate list

**Purpose.** Render the **0..N PersonCandidates** derived from a single raw
`contact_label` (`CLAIMS-EVIDENCE-MODEL.md` §2.9). A contact label may hold
initials, a first name, or several people at once; each candidate is assessed
**independently** and **never collapsed into one person verdict**
(`SCREEN-STATES.md` §3 per-candidate note).

**Where used.** Screen 5 (PERSON) primarily; a compact reference on SUMMARY.

**Key inputs.**
- The immutable raw `contact_label` (via §27's discipline — shown as supplied,
  never destructively parsed), displayed once above the list.
- Ordered PersonCandidate rows, each with:
  - `label_fragment` — the portion of the contact label this candidate came from.
  - `person_evidence_status` (4-value: `IDENTITY_EVIDENCE_FOUND` |
    `LIMITED_EVIDENCE` | `IDENTITY_AMBIGUOUS` | `NO_RELIABLE_EVIDENCE_LOCATED`) →
    Status pill (§4 person-evidence group).
  - `relationship_state` (5-value: `VERIFIED` | `CORROBORATED` | `SELF_ASSERTED` |
    `UNVERIFIED` | `CONTRADICTED`) → Status pill (§4 relationship group).
  - A **match-basis line** (§32) — a short "why matched" plus the driving
    identifiers for the candidate (`COMPETITIVE-UX-PATTERN-AUDIT.md` C4), in
    words, never a numeric score.
  - An inline provenance chip (§31) and a link to the candidate's Evidence (§13),
    plus the resolved Person where set.

**States.**
- Default (one row per candidate, each carrying its own two pills).
- Empty — **zero** candidates: "No person candidates derived from the contact
  label" with why (a label may never resolve to a candidate), never a blank (§22);
  this is not read as "no person exists".
- Loading — skeleton rows retaining the two pill slots (§21).
- Partial — candidates whose evidence is still running note "Evidence pending" per
  row; rows are never merged while pending (§25 pattern).

**Accessibility.**
- A list; each candidate is a labelled row read as its own item; the two states
  are label-led Status pills (never colour alone).
- The raw contact label and each `label_fragment` are plain readable text; the
  1-to-many relationship (one label → many candidates) is stated, not implied by
  layout alone.

**Variants.**
- *Full* (PERSON) vs *compact reference* (SUMMARY: fragment + the two pills,
  linking to the full row). Never a single-verdict summary.

---

## 29. case_context (non-evidentiary) panel

**Purpose.** Present the imported commercial/management context retained on the
Investigation as **`case_context`**, clearly and unmistakably labelled
**non-evidentiary** — retained for traceability only, never a Source, Claim, or
Evidence, and never an input to finding synthesis
(`CLAIMS-EVIDENCE-MODEL.md` §2.10; `PHASE-1-SCOPE.md` §2B, §5).

**Where used.** Screen 3 (SUMMARY) as a distinct, visually set-apart region; may
also appear on the Final Report as a clearly-marked non-evidentiary context block.

**Key inputs.** (all optional keys from `case_context`)
- `buyer_seller`, `management_reference`, `internal_tier`, `product`, `quantity`,
  `incoterm`, `port`, `commercial_comments`, `raw_source_row` — shown as retained
  context values only.

**Behaviour rules.**
- **Must visually signal it is not evidence.** A persistent, text-first
  "Non-evidentiary — retained context, not analysed" label heads the panel, set
  apart from the truth-boundary treatments (§11); it must never be mistaken for a
  source fact, counterparty claim, or system assessment.
- **`internal_tier` (T1/T2/…) is never styled as a risk/integrity rating.** It
  renders as a plain retained value with no tone, badge, or ranking treatment, and
  no colour implying severity — ARIE internal tiers must never read as Sentinel
  ratings.
- Commercial terms (product / quantity / Incoterm / port / price) are displayed as
  retained context only and are **not analysed** in Phase 1 (§5 scope guard); the
  panel draws no conclusions from them.

**States.**
- Default (context present).
- Empty — no imported context: "No commercial context imported" (§22); the panel
  may be omitted entirely when `case_context` is null.
- Loading — labelled skeleton (§21).

**Accessibility.**
- The non-evidentiary label is real text announced to assistive tech, not a
  colour/box cue alone; values are read as a labelled description list; the tier
  value carries no status semantics.

**Variants.** None. (Retained-not-analysed presentation only.)

---

## 30. Linked-investigations indicator

**Purpose.** A small, non-intrusive marker that a resolved **Counterparty** is
referenced by **other investigations** (the shared/deduplicated entity of
`CLAIMS-EVIDENCE-MODEL.md` §2.7). It signals shared identity without building a
heavy cross-linking or relationship-graph UI (out of the quiet-workspace intent).

**Where used.** Case header (§2) beside the resolved legal name; optionally on
SUMMARY and the COMPANY entity row.

**Key inputs.**
- Count of other investigations linked to the same `counterparty_id` (shown as
  text, e.g. "Referenced by 2 other investigations").
- Present **only** when `company_identity_status = CONFIRMED` and a shared
  counterparty exists (linked on authoritative `identity_key`, never on label
  similarity).

**Behaviour rules.**
- Non-intrusive: a quiet text marker, not a panel; it may link to a minimal list
  of the other investigations but introduces no cross-case merge/analysis UI.
- States shared identity only; it never implies any evidentiary or risk
  relationship between the linked investigations.

**States.**
- Default (shown when links exist).
- Empty/absent — no other investigation references the counterparty: the marker is
  simply not rendered (no "0 links" noise).
- Loading — omitted until the link count resolves (never a flashing placeholder).

**Accessibility.**
- Text-first marker with an accessible name stating the count and meaning; if it
  links out, it is a labelled link; not conveyed by icon/colour alone.

**Variants.** None.

---

## 31. Inline provenance chip

**Purpose.** A compact, inline marker on any fact or finding row that makes
provenance legible **without opening the drawer**: it shows the **source class**
and the **retrieved date** of the backing evidence, and opens the Evidence drawer
(§13) for the full source record (pattern from Moody's Grid / Sayari;
`COMPETITIVE-UX-PATTERN-AUDIT.md` §3, C3; `INFORMATION-ARCHITECTURE.md` §4). It
is the always-visible surface of provenance; the drawer is the drill-down.

**Where used.** On every fact/finding row that has backing evidence — Summary
shortlists (§7), COMPANY / PERSON facts (§12), Finding EVIDENCE regions (§8),
screening match rows (§14), related-parties rows (§33), and the Final Report's
material statements (§18).

**Key inputs.**
- `source_class` (Phase 1 controlled vocabulary — `CLAIMS-EVIDENCE-MODEL.md` §3),
  rendered as its text label.
- `retrieved_at` date (Mono), shown as a date (the drawer holds the full
  timestamp and record).
- Open-drawer handler → the originating fact/finding's Evidence drawer (§13),
  reached in 1 interaction.
- Size (default | compact for dense table rows).

**States.**
- Default (source class + retrieved date shown, actionable).
- Loading — renders inside its host's skeleton (§21); the chip itself has no
  independent fetch.
- Multiple sources — where a row is backed by more than one source, the chip
  states the count in text (e.g. "Registry +2") and opens the drawer to the full
  list; it never hides that multiple sources exist.
- Source unavailable — where the backing source failed, the chip reads the
  source-unavailable label (§25) rather than implying a captured source; it never
  reads as a clean negative.

**Accessibility.**
- The accessible name states class **and** retrieved date in words (e.g.
  "Source: registry, authoritative — retrieved 2026-02-11; open evidence").
- **Greyscale-safe and non-colour-dependent:** the source class is carried by its
  text label (and optional shape token), never by colour alone
  (`DESIGN-SYSTEM.md` §4; global rule §0.1).
- Keyboard-operable with a visible focus ring; target size ≥24×24px (§0.5).
- Provenance is one of the three named classes — **never** a numeric AI
  confidence (§0.3).

**Variants.** *Default* vs *compact* (dense rows); *single-source* vs
*multi-source* (count shown). No colour-only variant.

---

## 32. Match-basis line

**Purpose.** A short, plain-language **"why matched"** line plus the **driving
identifiers**, attached to any candidate/match so resolution stays visible and
reversible (Sayari `match_strength` + human-readable explanation; World-Check
secondary identifiers; `COMPETITIVE-UX-PATTERN-AUDIT.md` §3, C4). It states the
basis in evidence-based language (e.g. "same registration number" or "name only
— weak"), never a numeric score.

**Where used.** On each option of the Identity resolution chooser (§6), each
screening match row (§14), and each PersonCandidate row (§28).

**Key inputs.**
- `match_basis` — a short human-readable string describing why this candidate
  matched (additive field, `CLAIMS-EVIDENCE-MODEL.md` `match_basis`).
- The **driving identifiers** — the specific fields that drove the match (e.g.
  registry ID, jurisdiction, DOB, alias), rendered with Mono for IDs.
- Optional strength wording in words only (e.g. "strong — registry ID match" /
  "weak — name only"); **never** a numeric confidence or percentage.

**States.**
- Default (basis + identifiers shown).
- Loading — renders inside the host row's skeleton (§21).
- Partial — where an identifier is still resolving, the line notes it in text
  rather than omitting the basis.
- Empty — where no discriminating basis exists, it states "name only — no
  distinguishing identifiers" rather than implying a stronger match.

**Accessibility.**
- Real text read with its host row; the basis and each identifier are readable
  (not conveyed by position/colour alone).
- Strength is expressed in words; **no numeric AI confidence** (§0.3);
  greyscale-safe (§0.1).

**Variants.** None structurally; wording varies with the basis and host
(identity candidate / screening match / PersonCandidate).

---

## 33. Related-parties list

**Purpose.** A bounded, lightweight list of the directors / officers / owners and
other linked parties already within Phase 1 scope, presenting existing relationship
data better **without** a graph (Quantexa/Sayari graph-overwhelm avoided;
`COMPETITIVE-UX-PATTERN-AUDIT.md` §3, §10, C5; `INFORMATION-ARCHITECTURE.md` §4).
Each row is expand-on-demand for the next hop. It is explicitly a **list, never a
force-directed graph or a graph database**.

**Where used.** COMPANY (screen 4) and PERSON (screen 5). Built on the Quiet data
table (§12).

**Key inputs.**
- Bounded, ordered rows (capped for legibility — the most material parties first;
  it does not attempt to enumerate an entire network), each with:
  - Party name (Mono for any registry ID).
  - **Relationship type** (e.g. director, officer, beneficial owner, linked
    party) — text label.
  - **State** — the relationship state (`SCREEN-STATES.md` §4) via Status pill
    (§4), or the party's evidence state where that is what is known; label-led.
  - **Source** — an inline provenance chip (§31) opening the Evidence drawer (§13).
  - Expand-on-demand control revealing the next hop / detail for that row only.

**States.**
- Default (bounded list of rows).
- Loading — skeleton rows (§22).
- Empty — "No related parties located" with why (§23); never a blank grid, and
  never read as "none exist".
- Partial — ready rows with a divider and a "pending" note for sources still
  running (§25).
- Error — states what failed to load + retry (§24).

**Accessibility.**
- Built on the Quiet data table (§12): semantic rows, keyboard-operable
  expand/collapse with `aria-expanded`, state via label-led Status pills, source
  via the accessible provenance chip (§31).
- Relationship type and state are text; **not** conveyed by colour or a visual
  graph layout.

**Variants.** *Company* (directors / officers / owners) vs *Person* (roles /
linked parties) — same component, different party sets. **No** graph variant.

---

## 34. Bulk import panel

**Purpose.** Create many investigations at once from a spreadsheet of raw labels,
routing **each accepted row through the same Intake Quality Gate as the single
Investigate form** (§5). It is a batch entry path, **not** an ETL platform: it
does no transformation, enrichment, scheduling, or pipeline orchestration — it
captures raw labels verbatim (`CLAIMS-EVIDENCE-MODEL.md` §2.6) and hands each to
the existing intake flow. Malformed rows are isolated, never silently created.

**Where used.** A secondary bulk-entry surface reached from the Investigate
destination (screen 1); not a tenth case screen and not a case tab.

**Key inputs.**
- **File upload** — a single XLSX or CSV. States what it accepts (two required
  label columns + optional context); rejects other formats with a stated reason.
- **Minimal column mapping** — the *smallest* mapping, not a field-by-field ETL
  mapper:
  - source column → `company_label` (required, captured as supplied, e.g.
    `Vantar - Castellan`, `NORDIC-HALCYON`, `TBD`, `Unnamed Refinery`).
  - source column → `contact_label` (required, captured verbatim, e.g.
    `Jordan Rivera`, `NOVEXA - Amara - via Delta Trading`, `JR`).
  - optional source column(s) → `case_context` (non-evidentiary, §29 — e.g.
    `management_reference` `REF-207`, `port` `Port A`); never mapped to a Source,
    Claim, or Evidence.
- **Per-row result list** — one row per input line with a **row status**:
  - *Accepted* — the two required labels are present; the row becomes an
    Investigation through the intake gate (which may itself return
    `SUFFICIENT_FOR_DISCOVERY` or `CLARIFICATION_REQUIRED`, §26 — the panel forces
    no discovery and manufactures no entity).
  - *Malformed — rejected* — with the specific reason (e.g. "no company label",
    "no contact label", "unreadable row"); isolated, creating nothing.

**Behaviour rules.**
- **Each accepted row goes through the intake gate.** No row bypasses §5/§26; a
  row whose labels are too poor (e.g. `TBD`, `Unnamed Refinery`) is created as an
  investigation in `CLARIFICATION_REQUIRED` — it is **not** rejected as malformed
  (malformed = missing a required column; clarification = poor but present labels).
- **Malformed rows are isolated.** They are listed with a reason and create
  nothing; a partial file still imports its valid rows.
- **Re-import is idempotent.** A row matching an existing investigation (same raw
  labels / declared `management_reference`) **warns and links** to the existing
  case rather than creating a silent duplicate; re-running the same file produces
  no duplicate investigations.
- **Not an ETL platform.** No column transforms, joins, enrichment, or scheduled
  syncs; commercial context is retained as non-evidentiary `case_context` only,
  never analysed (`PHASE-1-SCOPE.md` §5).

**States.**
- Default (awaiting a file).
- Loading — parsing/validating the file: skeleton result rows (§21) with a text
  description of what is being processed.
- Empty — no file chosen, or a file with zero readable rows: explains what a valid
  file looks like (§22), never a blank drop zone.
- Partial — some rows accepted, some malformed: both groups shown with counts in
  text; the accepted rows are created, the malformed rows isolated with reasons
  (§25 pattern).
- Error — the upload or batch create failed: what failed + recovery/retry (§24);
  no half-created investigations left implicit.

**Accessibility.**
- Labelled file input (not drag-only); mapping controls are labelled selects with
  programmatic association; required mappings announced.
- The per-row result list is a semantic list/table; each **row status uses a
  label-led Status pill** (§4) — accepted vs malformed distinguished by word +
  shape, **never colour alone**; each malformed reason is real text.
- Errors summarised and focus-managed as in §5; counts stated in words.

**Variants.** None. (XLSX and CSV share one mapping + result flow.)

---

## 35. Analyst worklist

**Purpose.** The analyst's quiet, filterable worklist of investigations —
upgrading the Cases list table (§15) from a plain list into a triage surface,
while keeping its quiet-workspace discipline: **no charts, no vanity stats, no
risk score, no dashboard tiles** (`INFORMATION-ARCHITECTURE.md` §7). Opening a row
enters the workspace at SUMMARY.

**Where used.** Screen 2 (Cases). Built on the Quiet data table (§12); supersedes
the plain Cases list table (§15) as the default Cases surface.

**Key inputs.**
- Table columns as in §15: entity/input name (via §27 raw-vs-resolved), contact,
  `investigation_state`, `completeness_state`, `company_identity_status`, updated
  timestamp (Mono), owner. Sortable.
- **Filter chips DERIVED from canonical states** (`SCREEN-STATES.md`) — these are
  **derived views, not new persisted states**; nothing new is written to any
  investigation:
  - *Assigned to me* — owner = current analyst.
  - *Needs action* — an **umbrella** derived over the actionable chips below
    (union of clarification required / identity ambiguous / screening review
    required / findings requiring review).
  - *Clarification required* — `intake_state = CLARIFICATION_REQUIRED` (§0).
  - *Identity ambiguous* — `company_identity_status = AMBIGUOUS` (§2).
  - *Screening review required* — any screening row at `MATCH_REQUIRES_REVIEW` (§7).
  - *Findings requiring review* — any finding at `review_status = OPEN` (§6).
  - *Completed* — `investigation_state = COMPLETED` (§1).
- Active filter chips (combinable), current sort.

**Behaviour rules.**
- **Filters are derived views only.** A chip filters the existing list by canonical
  state; it never introduces a new state name, never persists a status on an
  investigation, and never mutates data.
- **No metric surface.** No charts, aggregate KPI tiles, trend lines, or a
  numeric/graded risk score above or within the list (still rejected, §6 of this
  update; `INFORMATION-ARCHITECTURE.md` §7).

**States.**
- Default (list, no filter or with filters applied).
- Loading — skeleton rows (§21).
- Empty — no cases, or none match the active chips: explains and offers
  "Investigate" or "Clear filters" (§22); an empty *filtered* result names the
  active filter rather than implying no cases exist.
- Error — list failed to load + retry (§24).

**Accessibility.**
- Built on the Quiet data table (§12): `aria-sort` headers, keyboard sort, state
  cells as label-led Status pills (§4).
- Filter chips are a labelled group of toggle controls (`aria-pressed`),
  keyboard-operable, each stating its derived meaning in text; the chip's active
  state is not conveyed by colour alone; the result count is announced.

**Variants.** None (single column set, per IA §7; chip set frozen to the derived
views above).

---

## 36. Structured export action

**Purpose.** A **secondary** action that produces a structured **evidence &
findings register** as CSV or XLSX for downstream review — secondary to the Final
Report (§18), which remains the primary management surface. It is a licensing-aware
extract of what is already in the case, not a new analysis.

**Where used.** Case workspace and the Final Report (screen 9) as a secondary
action beside the management report; never the primary output.

**Key inputs.** (one row per material finding / evidence line)
- `investigation ref`, `resolved entity` (the `CONFIRMED` `legal_name`, e.g.
  *Vantar Energy Trading FZE*; raw `company_label` retained where not confirmed),
  `person/contact` (per PersonCandidate, §28), `claim`, `finding type`,
  `finding status`, `source class`, `source ref/URL where licensing permits`,
  `retrieved date`, `analyst decision`, `required action`.
- Format choice (CSV | XLSX).

**Behaviour rules.**
- **Licensing-aware.** Emits **no vendor payloads and no restricted source
  content** — where a source's licence forbids redistribution, the register omits
  the excerpt/URL and records the source **class** and reference only (or a
  "restricted — not exportable" note), never the licensed body text
  (`CLAIMS-EVIDENCE-MODEL.md` §3; `SECURITY-BOUNDARIES.md`).
- **Secondary to the report.** It supplements, never replaces, the management
  report (§18); it applies the same truth boundary in its columns (claim vs
  finding vs source) and carries provenance as the three named classes, never a
  numeric confidence (§0.3).
- Writes an audit event for the export action (`CLAIMS-EVIDENCE-MODEL.md` §2.7).

**States.**
- Default (actionable where the case has exportable rows).
- Disabled — nothing exportable yet, or actor lacks the action: reason stated
  (§24).
- In-progress — assembling the register; control locked.
- Empty — no material findings/evidence to export: stated, not a zero-row file
  offered silently (§22).
- Error — generation failed: what failed + retry (§24).

**Accessibility.**
- A clearly labelled secondary button (visually subordinate to the report action);
  keyboard-operable; the licensing behaviour and format are stated in text, not
  implied.
- Column semantics preserve the truth boundary in words; provenance as named
  classes.

**Variants.** *CSV* vs *XLSX* — same columns and licensing rules; format only.

---

## 37. Grouped adverse-media event row

**Purpose.** Where the screening provider **supplies event grouping**, render one
**event** (e.g. a single reported matter) carrying an **article/source count**
that expands to the underlying articles — instead of one flat row per article — so
an analyst reads distinct events, not duplicated headlines. It is **provider-aware**:
if the provider supplies no grouping, results fall back to individual rows.
Screening still **never auto-decides** (`SCREEN-STATES.md` §7).

**Where used.** Screen 6 (SCREENING), within the Screening match row / list (§14);
built on the Quiet data table (§12).

**Key inputs.**
- Per event: event summary/title, **article/source count** (text, e.g. "1 event ·
  4 articles"), the event's match state → Status pill (§4 screening variants), a
  **match-basis line** (§32), and an inline provenance chip (§31).
- Expand-on-demand control revealing the **underlying articles** for that event
  only, each linking to its Evidence (§13).
- Provider grouping flag (grouped vs ungrouped) driving which rendering applies.

**Behaviour rules.**
- **Provider-aware fallback.** With no provider grouping, each article renders as
  an individual §14 row; the grouped rendering is used only where the provider
  actually supplies event grouping (no synthetic grouping is invented).
- The article count is always shown in text so collapsed articles are never
  hidden; expanding never changes the event's match state.

**States.**
- Default (collapsed event with count).
- Expanded (underlying articles listed).
- Loading — skeleton rows (§21).
- Empty — "No adverse-media events located" with why (§22), corresponding to
  `NO_MATERIAL_MATCH` at case level.
- Partial — ready articles shown with a "pending" note where retrieval is still
  running (§25).
- Error / Source unavailable — the provider failed: named, with completeness
  impact (§24, §25); an unreachable source is never read as a clean negative.

**Accessibility.**
- Semantic table rows; the expand/collapse control uses `aria-expanded` and is
  keyboard-operable; the article count is real text (not a colour/badge alone).
- Match state via label-led Status pill; grouping is conveyed in words ("event",
  "N articles"), never by layout or colour alone.

**Variants.** *Grouped event* (provider supplies grouping) vs *individual rows*
(fallback, the §14 row). Same match state, basis, and provenance semantics.

---

## Appendix A — component × screen matrix

Legend: ● primary use · ○ present/embedded.

Columns follow the case screens; the five tab screens are in tab-bar order
(SUMMARY · FINDINGS · COMPANY · PERSON · SCREENING). **Evidence is not a tab** —
its column is the in-context drawer (§13) plus the secondary All-sources browse
(§13a), reached from any fact/finding. **Bulk Import** is the secondary bulk-entry
surface off Investigate (§34), not a tenth case screen.

| Component | Investigate | Bulk Import | Cases | Summary | Findings | Company | Person | Screening | Evidence (drawer) | Final Report |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| App shell / global nav | ● | ○ | ● | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| Case header (persistent) | | | | ● | ● | ● | ● | ● | ○ | ○ |
| Case tab bar (§3, 5-tab) | | | | ● | ● | ● | ● | ● | | |
| Status pill | | ○ | ● | ● | ● | ● | ● | ● | ● | ● |
| Intake form + Investigate | ● | | | | | | | | | |
| Identity resolution chooser | | | | ○ | | ○ | | | | |
| Verified / Unknown lists | | | | ● | | ○ | ○ | | | |
| Finding panel | | | | ○ | ● | | | ○ | | ○ |
| Finding action bar | | | | | ● | | | ○ | | |
| Severity marker | | | | ○ | ● | | | | | ○ |
| Truth-boundary renderer | | | | ● | ● | ● | ● | ● | ● | ● |
| Quiet data table | | | ○ | | | ● | ● | ● | ● | |
| Evidence drawer (§13, primary) | | | | ○ | ○ | ○ | ○ | ○ | ● | ○ |
| All-sources browse view (§13a, secondary) | | | | | | | | | ● | |
| Screening match row / list | | | | ○ | ○ | | | ● | | ○ |
| Cases list table | | | ● | | | | | | | |
| Alert / banner | | | | ● | ● | ● | ● | ● | ○ | ○ |
| Audit / history timeline | | | | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| Confirmation dialog | | | | ○ | ● | | | ○ | | ● |
| Note composer | | | | | ● | ○ | ○ | ○ | ○ | |
| Intake clarification panel (§26) | ● | | | ○ | | | | | | |
| Raw-label vs resolved-identity renderer (§27) | | | ○ | ● | | ● | | | | ● |
| PersonCandidate list (§28) | | | | ○ | | | ● | | | ○ |
| case_context (non-evidentiary) panel (§29) | | | | ● | | | | | | ○ |
| Linked-investigations indicator (§30) | | | ○ | ○ | | ○ | | | | |
| Inline provenance chip (§31) | | | | ● | ● | ● | ● | ● | ○ | ● |
| Match-basis line (§32) | | | | ○ | | ○ | ● | ● | | ○ |
| Related-parties list (§33) | | | | | | ● | ● | | | |
| Bulk import panel (§34) | ○ | ● | | | | | | | | |
| Analyst worklist (§35) | | | ● | | | | | | | |
| Structured export action (§36) | | | | ○ | | | | | | ● |
| Grouped adverse-media event row (§37) | | | | | | | | ● | | ○ |
| Final report layout blocks | | | | | | | | | | ● |
| Loading / Empty / Error / Disabled / Source-unavailable | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |

> The **Intake Clarification** surface is not a tenth screen: it is the Intake
> clarification panel (§26) shown over Investigate (screen 1) and, while
> `intake_state = CLARIFICATION_REQUIRED` holds, over SUMMARY (screen 3) — no
> discovery has run, so no full case workspace exists yet. It is distinct from the
> Identity Resolution gate (§6), which is an `AMBIGUOUS` gate over SUMMARY/COMPANY
> *after* discovery ran.

---

## Appendix B — canonical enum → component map

Where each `SCREEN-STATES.md` enum is surfaced.

| Enum group | Rendered by | Primary location |
|---|---|---|
| Intake quality (§0) | Status pill (§4 intake-quality group); Intake clarification panel (§26); Analyst worklist *Clarification required* chip (§35, derived view); Bulk import panel per-row status (§34) | Case header, Investigate, Bulk Import, Cases (worklist), Summary |
| Investigation lifecycle (§1) | Status pill (§4); Analyst worklist column + *Completed* chip (§35, derived view) | Case header, Cases (worklist §35) |
| Legal entity (§2) | Status pill; Identity chooser (§6) gate + match-basis line (§32); Raw-label vs resolved-identity renderer (§27); Analyst worklist *Identity ambiguous* chip (§35, derived view) | Case header, Company, Cases (worklist) |
| Person evidence (§3) | Status pill, per PersonCandidate (§28) + match-basis line (§32) | Person, Summary |
| Relationship (§4) | Status pill, per PersonCandidate (§28); Related-parties list (§33) | Person, Summary, Company |
| Research completeness (§5) | Status pill; Research Completeness **checked-vs-not-established checklist** block (§18) | Case header, Final Report |
| Finding type (§6) | Type pill on Finding panel (§8) | Findings |
| Finding review status (§6) | Status pill on Finding panel (§8); Analyst worklist *Findings requiring review* chip (§35, derived view) | Findings, Cases (worklist) |
| Severity (§6) | Severity marker (§10) | Findings, Summary |
| Screening (§7) | Status pill; Screening row (§14) + match-basis line (§32); Grouped adverse-media event row (§37, provider-aware); Analyst worklist *Screening review required* chip (§35, derived view) | Screening, Cases (worklist) |
| Universal states (§8) | §21–25 | All data-bearing components (incl. Bulk import §34) |
| Source class / provenance (`CLAIMS-EVIDENCE-MODEL.md` §2.2–§3) | Inline provenance chip (§31); Evidence drawer (§13) / All-sources browse (§13a); Structured export register (§36, licensing-aware — class/ref only where redistribution is restricted) | All fact/finding rows, Summary, Findings, Company, Person, Screening, Final Report, exported register |

> **Analyst worklist chips are derived views, not new persisted states** (§35):
> each chip filters the list by an existing canonical enum and writes nothing new.
> The *Needs action* chip is an umbrella union of *Clarification required*,
> *Identity ambiguous*, *Screening review required*, and *Findings requiring
> review*. **No risk-score, graph, or dashboard component is introduced** (still
> rejected).
