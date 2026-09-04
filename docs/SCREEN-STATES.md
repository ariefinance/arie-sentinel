# Screen / State Model

**Status:** Frozen. This is the canonical enumeration of every state in
Sentinel Phase 1. All other documents and all implementation must use these
exact names. Do not invent synonyms.

**Cross-cutting rule:** *colour never conveys status or risk on its own.* Every
state is communicated by an explicit **text label** (and where useful an icon
and position). Colour is a secondary reinforcement only, and must remain
distinguishable under greyscale and common colour-vision deficiencies (see
`DESIGN-SYSTEM.md`).

---

## 0. Intake quality (added revision)

Assessed by the **Intake Quality Gate** on the raw `company_label` +
`contact_label`, **before** any discovery runs.

| State | Meaning | Consequence |
|---|---|---|
| `SUFFICIENT_FOR_DISCOVERY` | Input is good enough to begin reliable company resolution. | Proceed to normalisation → candidate discovery → legal entity resolution. |
| `CLARIFICATION_REQUIRED` | Insufficient input to begin reliable discovery (e.g. `TBD`, `Unnamed Refinery`). | **Stop.** Ask for the minimum useful discriminator. **No** broad web/AI investigation, **no** manufactured entity, **no** counterparty created. |

> **`CLARIFICATION_REQUIRED` ≠ `AMBIGUOUS`.** They have different causes and
> must never be merged:
> - `CLARIFICATION_REQUIRED` — input too poor to *start* discovery.
> - `AMBIGUOUS` (§2) — discovery *ran* and returned several plausible entities.

## 1. Investigation lifecycle

| State | Meaning | Analyst-facing label | Treatment |
|---|---|---|---|
| `NOT_STARTED` | Case created, not yet run. | "Not started" | Neutral. |
| `RUNNING` | Jobs in progress. | "Investigation running" | Progress indicator + which steps. |
| `PARTIAL_RESULTS` | Some steps done, others pending/limited. | "Partial results" | Show what's ready; mark pending clearly. |
| `SOURCE_UNAVAILABLE` | A material source could not be reached. | "Source unavailable" | Name the source + impact on completeness. |
| `COMPLETED` | All steps concluded (with or without limitations). | "Completed" | Full workspace/report available (subject to gates). |
| `FAILED` | Investigation could not proceed. | "Investigation failed" | Reason + retry/next action. |

## 2. Legal entity

| State | Meaning | Consequence |
|---|---|---|
| `CONFIRMED` | Exactly one legal entity resolved against authoritative source. | **Required** to generate Final Report. |
| `AMBIGUOUS` | Multiple plausible entities. | **Blocks** Final Report. Triggers Identity Resolution gate. |
| `NOT_VERIFIED` | No authoritative registry confirmation obtained. | **Blocks** Final Report; drives required actions + limitations. |

## 3. Person evidence

| State | Meaning |
|---|---|
| `IDENTITY_EVIDENCE_FOUND` | Reliable evidence of the named person located. |
| `LIMITED_EVIDENCE` | Some evidence, insufficient to establish confidently. |
| `IDENTITY_AMBIGUOUS` | Multiple candidate persons; cannot disambiguate. |
| `NO_RELIABLE_EVIDENCE_LOCATED` | No reliable evidence located. |

> Note the wording: "NO RELIABLE EVIDENCE LOCATED" — never "fake person".

> **Per-candidate.** A raw `contact_label` may contain initials, a first name,
> or several people. It resolves through **0..N PersonCandidates**
> (`CLAIMS-EVIDENCE-MODEL.md` §2.9); this state — and the relationship state
> (§4) — apply **per candidate**, never collapsed into one person verdict.

## 4. Relationship (company ↔ person)

| State | Meaning |
|---|---|
| `VERIFIED` | Authoritative source establishes the relationship. |
| `CORROBORATED` | Multiple independent non-authoritative sources agree. |
| `SELF_ASSERTED` | Only the counterparty asserts it. |
| `UNVERIFIED` | No evidence either way. |
| `CONTRADICTED` | Evidence conflicts with the asserted relationship. |

## 5. Research completeness

| State | Meaning | Report effect |
|---|---|---|
| `COMPLETE` | All material lines of enquiry concluded. | Reported as complete. |
| `COMPLETE_WITH_LIMITATIONS` | Concluded, but with named caveats. | Limitations section populated. |
| `MATERIAL_SOURCE_UNAVAILABLE` | A material source was unavailable. | Prominent limitation; affects confidence in conclusions. |

## 6. Finding type

| Type | Meaning |
|---|---|
| `CONTRADICTION` | Claim and authoritative evidence directly conflict. |
| `INCONSISTENCY` | Claim and evidence are in tension but not strictly contradictory. |
| `UNVERIFIED_CLAIM` | Material claim with no supporting evidence located. |
| `ANOMALY` | Pattern warranting attention (e.g. timing mismatch). |
| `INSUFFICIENT_EVIDENCE` | Not enough evidence to assess a material question. |

Every finding also has a **review status**: `OPEN` · `CONFIRMED` ·
`DISMISSED` · `INFO_REQUESTED`, and a **severity**: `high` · `medium` · `low`.

## 7. Screening

| State | Meaning | Behaviour |
|---|---|---|
| `NO_MATERIAL_MATCH` | No material sanctions/PEP/adverse match. | Recorded; low emphasis. |
| `POTENTIAL_MATCH` | Possible match, weak/needs work. | Surfaced for analyst. |
| `MATCH_REQUIRES_REVIEW` | Plausible match requiring human adjudication. | Routed to review; never auto-decided. |
| `CONFIRMED_MATCH` | Match confirmed by an analyst. | High emphasis; drives actions. |

> Screening never auto-decides. The system proposes; a human adjudicates.

> **Match basis (all match states).** Each screening match — and each identity
> candidate and PersonCandidate — carries a short plain-language `match_basis`
> ("why matched") plus the identifiers that drove it (e.g. "registration number +
> jurisdiction" vs "name only — weak"). This is presentational metadata; it does
> **not** change these enums or let the system auto-decide
> (`CLAIMS-EVIDENCE-MODEL.md`; `COMPETITIVE-UX-PATTERN-AUDIT.md` C4).

## 7A. Bulk-import row outcome

When investigations are created from an uploaded spreadsheet, each row carries a
per-row **import result**, recorded once at import time:

| Outcome | Meaning |
|---|---|
| `ACCEPTED` | The row was well-formed and became one Investigation. |
| `MALFORMED_REJECTED` | The row could not be parsed into an Investigation and was rejected on its own. |

> **This is an import-time result, not a new investigation state.** It is
> **distinct** from the lifecycle enums above (`intake_state`,
> `investigation_state`, `company_identity_status`) and is **isolated per row** —
> one `MALFORMED_REJECTED` row does not affect the outcome of any other row in
> the batch (`CLAIMS-EVIDENCE-MODEL.md` §2.6 bulk-import invariants). An
> `ACCEPTED` row then follows the **normal** lifecycle: it passes the intake gate
> (§0) and takes on `intake_state`, `investigation_state`, and
> `company_identity_status` exactly like a single investigation. No new
> investigation state is introduced.

> **Worklist filters are derived.** The analyst worklist filters (Assigned to me;
> Needs action; Clarification required; Identity ambiguous; Screening review
> required; Findings requiring review; Completed) are **derived** from the
> canonical states above — they persist **no new state**.

---

## 8. Universal component states

Every screen/component must define behaviour for:

- **Loading** — skeleton/placeholder with what is being fetched; never a blank.
- **Empty** — explains why there's nothing and what would populate it (e.g.
  "No screening matches located"), never an ambiguous void.
- **Partial** — clearly separates ready data from still-pending sections.
- **Error** — states what failed, the impact, and the recovery action; no raw
  stack traces; no swallowed errors.
- **Disabled** — states *why* an action is unavailable (e.g. "Finalise
  disabled: legal entity is AMBIGUOUS").
- **Source unavailable** — names the source and its effect on completeness.

---

## 9. State → gate map (invariants)

- Intake gate: discovery (normalisation, candidate discovery, entity resolution)
  runs **iff** `intake_state = SUFFICIENT_FOR_DISCOVERY`. A
  `CLARIFICATION_REQUIRED` investigation launches no web/AI investigation and
  creates no counterparty.
- Final Report generation: allowed **iff** `company_identity_status = CONFIRMED`.
  A `CLARIFICATION_REQUIRED` intake or `AMBIGUOUS`/`NOT_VERIFIED` identity blocks
  it.
- Finalise action (`FINALISE_REPORT`): `manager` role, requires a confirmed
  entity, and requires an explicit non-accidental confirmation step.
- Material finding dismissal (`DISMISS_FINDING` on `severity = high`): requires
  a rationale (`CLAIMS-EVIDENCE-MODEL.md` audit event `rationale` not null).
- `AMBIGUOUS` legal entity: cannot be silently resolved by any code path.
- `CLARIFICATION_REQUIRED` intake: cannot be silently upgraded — only new input
  can move it to `SUFFICIENT_FOR_DISCOVERY`.
- Counterparty creation: matched/created on authoritative `identity_key`, never
  on label similarity; a repeated organisation links to the existing
  counterparty rather than duplicating it.
- Raw labels (`company_label`, `contact_label`) and `case_context` are
  non-evidentiary and never inputs to finding synthesis.
