# Acceptance Criteria

**Status:** Frozen. These are the measurable conditions Phase 1 must satisfy.
They bind product, engineering, and UX.

---

## 1. Integrity & correctness

| # | Criterion | Measured by |
|---|---|---|
| C1 | **0** silently resolved ambiguous entities | No code path resolves `AMBIGUOUS` without explicit analyst action; verified by tests + audit log. |
| C2 | **0** unsupported material facts in final reports | Every material fact in a report links to evidence or is marked unresolved; report assembler enforces. |
| C3 | **100%** of material claims linked to evidence **or** explicitly unresolved | Data-model constraint + report validation. |
| C4 | **0** known critical identity misses in controlled tests | A fixed controlled test set of counterparties; no critical miss. |
| C5 | **0** prompt-injection influence over policy/workflow | Adversarial fixtures; model output cannot alter gating/state/RBAC. |

## 2. Analyst value

| # | Criterion | Measured by |
|---|---|---|
| C6 | **≥80%** analyst relevance for high-severity findings | Analyst rating of high-severity findings over a review sample. |
| C7 | **≥30%** analyst-time improvement | Time-to-position vs baseline manual process on comparable cases. |
| C8 | Completed report understandable within **~2 minutes** | Timed comprehension test with analysts/management. |

## 3. UX-specific acceptance criteria

| # | Criterion | Measured by |
|---|---|---|
| U1 | No critical workflow requires more than necessary input | Investigate screen = 2 fields; discriminators requested only when required. |
| U2 | Primary findings visible without excessive scrolling | High-severity findings above the fold on Summary at target desktop width. |
| U3 | Evidence accessible within **max two interactions** from a finding | Click-path audit from any finding to its source. |
| U4 | Ambiguous identity cannot be accidentally bypassed | Gate blocks report; no default selection; tested. |
| U5 | System limitations clearly visible | Completeness state + limitations shown on Summary and Report. |
| U6 | Colour never conveys risk/state alone | Every state has a text label + icon; greyscale audit passes. |
| U7 | Analyst can always distinguish source fact, counterparty claim, and system assessment | Truth-boundary treatment present on every relevant surface. |

## 4. Language & safety criteria

| # | Criterion |
|---|---|
| L1 | No UI/report text implies "safe/fraudulent/genuine company", "fake person", "safe transaction", or "verified credibility". |
| L2 | No subjective character labels ("suspicious", "probably fake"). |
| L3 | All status/finding language is evidence-based (per `PHASE-1-SCOPE.md` §6). |
| L4 | No vague numeric AI-confidence statements in the UI; provenance classes used instead. |

## 5. Scope-integrity criteria

| # | Criterion |
|---|---|
| S1 | No excluded Phase 2 concept appears in schema, navigation, report sections, or UI copy (transactions, mandates, vessels, payments, capacity scoring, forgery claims, continuous monitoring). |
| S2 | Adapter interfaces exist for external dependencies; no more than one real implementation per interface is built in Phase 1. |
| S3 | No graph database, no microservices, no autonomous privileged browser. |

## 6. Accessibility criteria

| # | Criterion |
|---|---|
| A1 | WCAG 2.2 AA contrast for text and UI components where practical. |
| A2 | Full keyboard operability with visible focus. |
| A3 | Status not conveyed by colour alone (== U6). |
| A4 | Form fields have programmatic labels and associated error messaging. |

## 7. Security criteria

| # | Criterion |
|---|---|
| SEC1 | No secrets, real case data, KYC, or vendor payloads in the repository (public-repo rules). |
| SEC2 | Every mutating action authorized server-side and audited. |
| SEC3 | Sources immutable, versioned, hash-verified. |
| SEC4 | Material finding dismissals require a recorded rationale. |

## 8. Intake, identity & context criteria (revision 2)

Driven by management's real client/counterparty list. All must map to
deterministic tests.

| # | Criterion |
|---|---|
| I1 | Intake insufficiency (`CLARIFICATION_REQUIRED`) and identity ambiguity (`AMBIGUOUS`) are **separate states** and are never merged in state, API, or UI. |
| I2 | A `CLARIFICATION_REQUIRED` intake launches **no** broad web/AI discovery and creates **no** counterparty (no manufactured entity). |
| I3 | Raw labels (`company_label`, `contact_label`) are immutable and remain recoverable after resolution; resolution never overwrites them. |
| I4 | The same organisation across multiple management records **links to one** counterparty (dedup on authoritative `identity_key`); no duplicate counterparty is created, and no silent label-based merge occurs. |
| I5 | A `contact_label` with initials / first-name-only / multiple people resolves to **0..N PersonCandidates**, each with independent evidence and relationship state. |
| I6 | `case_context` (incl. internal tier) never becomes a Source/Claim/Evidence, never influences findings, and internal tiers never render as risk ratings. |
| I7 | Phase 2 commercial fields (product/quantity/Incoterm/port/price/terms) imported as context are **not analysed** and never appear in Phase 1 findings or reports as conclusions. |

### Required test cases (must all pass)

| # | Input | Required behaviour |
|---|---|---|
| T1 | `company_label = "TBD"`, first-name-only contact | `CLARIFICATION_REQUIRED`; no invented entity; no discovery launched. |
| T2 | `company_label = "Unnamed Refinery"` (generic) | `CLARIFICATION_REQUIRED`; asks for minimum discriminator. |
| T3 | `company_label = "Vantar - Castellan"` (combined) | Discovery runs; raw label preserved verbatim even if resolved counterparty differs. |
| T4 | Same counterparty in multiple management records | Second investigation **links** to the existing `counterparty_id`; no duplicate; no silent merge of distinct entities. |
| T5 | Multiple contacts in one field (`"NOVEXA - Amara - via Delta Trading"`) | ≥1 PersonCandidate derived per person; each assessed independently; raw label intact. |
| T6 | Initial-only contact (`"JR"`) | One PersonCandidate; likely `LIMITED_EVIDENCE`/`IDENTITY_AMBIGUOUS`; never invents a person. |
| T7 | Internal management tier present (T1/T2) | Retained in `case_context`; never used as evidence; never shown as a Sentinel risk/integrity rating. |
| T8 | Phase 2 commercial fields imported (product, quantity, Incoterm, port) | Retained as `case_context`; ignored by Phase 1 analysis; absent from findings/report conclusions. |

**Aggregate required behaviours:** no invented legal entity; no silent merging;
no duplicate counterparty where identity is already established; raw source
labels remain recoverable; context never becomes external evidence; Phase 2
fields do not leak into Phase 1 findings.

## 9. Competitive-audit UX criteria (revision 3)

From `COMPETITIVE-UX-PATTERN-AUDIT.md` (changes C1–C7). All must map to a test or
a defined manual check.

| # | Criterion |
|---|---|
| X1 | Case navigation is the five-tab set `SUMMARY · FINDINGS · COMPANY · PERSON · SCREENING`; Evidence is not a primary tab. |
| X2 | Evidence opens as an in-context drawer from any fact/finding and closes back to the same context — reaching a source never forces a page round-trip (satisfies U3 and "return to context"). |
| X3 | A secondary "All sources" browse lists everything captured (the browse need is met without a primary Evidence tab). |
| X4 | Every material fact/finding row shows an inline provenance chip (source class + retrieved date); the chip opens the full source record. |
| X5 | Identity candidates, screening matches, and PersonCandidates each show a plain-language `match_basis` ("why matched") plus the identifiers that drove the match; resolution stays visible and reversible. |
| X6 | Company/Person show a bounded Related-parties list (type + state + source, expand-on-demand) rendered as a list — never a force-directed graph or a graph database. |
| X7 | The Final Report makes all eight management questions immediately obvious, each in its own section: legal entity resolved; named person(s); person–company relationship; screening concerns; material inconsistencies; what could not be established; required actions; material source limitations. |
| X8 | The report contains an explicit **Named Person(s)** section and an explicit **Screening** section; "No material match located" is stated plainly where applicable. |
| X9 | Research completeness is shown as an explicit **checked-vs-not-established** checklist, not only a state label. |
| X10 | The report has **no** generic AI executive summary; every material statement is click-through traceable to its evidence. |

> Each criterion above should map to at least one automated test or a defined
> manual verification procedure when implementation begins (`BUILD-PLAN.md`).

## 10. Bulk intake / worklist / adverse-media / export criteria (revision 4)

Driven by management working from a spreadsheet of many client/counterparty rows
rather than one intake at a time. Each criterion below must map to a deterministic
test or a defined manual check when implementation begins (`BUILD-PLAN.md`).

### Bulk intake

| # | Criterion | Measured by |
|---|---|---|
| B1 | One malformed row does not corrupt, block, or alter the processing of other rows in the same import. | Import a batch where one row is malformed (e.g. missing `company_label`); the malformed row is isolated as its own failed/`CLARIFICATION_REQUIRED` outcome and every other row still produces its own investigation; deterministic test. |
| B2 | Every row independently passes through the **Intake Quality Gate** (§8) — bulk import applies no weaker or bypassed intake path. | Each per-row investigation carries an `intake_state` set by the same gate as single intake; a bulk `TBD` / `Unnamed Refinery` row yields `CLARIFICATION_REQUIRED` exactly as T1/T2; deterministic test. |
| B3 | Ambiguous rows remain ambiguous — bulk processing performs **no** auto-resolution of `AMBIGUOUS` identity or of ambiguous intake. | A row resolving to `AMBIGUOUS` (e.g. the `Vantar Energy Trading` FZE/Ltd/LLC siblings) stays `AMBIGUOUS` after import; no default counterparty selected (reinforces C1/U4); deterministic test. |
| B4 | Duplicate resolved counterparties across rows link to the **shared** Counterparty (dedup on authoritative `identity_key`), never a duplicate. | Two rows resolving to the same registry identity (e.g. `Castellan Trading FZE` twice) link to one `counterparty_id`; no duplicate counterparty; no silent label-based merge (reinforces I4); deterministic test. |
| B5 | Raw spreadsheet labels remain immutable and recoverable after resolution — the imported `company_label` / `contact_label` are never overwritten. | Import `Vantar - Castellan`; raw label preserved verbatim on the investigation even where the resolved counterparty differs (reinforces I3); deterministic test. |
| B6 | Re-importing the same file cannot silently create uncontrolled duplicate investigations — import is idempotent on `import_row_hash`. | Import the same file twice; the second import creates no duplicate investigation for an unchanged row (matched on `import_row_hash`); deterministic test. |

### Worklist

| # | Criterion | Measured by |
|---|---|---|
| W1 | An analyst can identify which cases require action without opening every investigation. | A worklist view surfaces cases whose canonical state needs analyst action (e.g. `CLARIFICATION_REQUIRED`, `AMBIGUOUS`, `MATCH_REQUIRES_REVIEW`, findings `OPEN`) without opening each case; deterministic test over seeded states. |
| W2 | Worklist state derives from canonical workflow states, not duplicated UI-only logic; it is **not** a dashboard (no charts, vanity stats, or risk score). | Each worklist row's actionability maps 1:1 to canonical `intake_state` / `investigation_state` / `screening_state` / `review_status`; a review/test asserts no chart, aggregate metric tile, or risk score is present (reinforces S1, U6). |

### Adverse media

| # | Criterion | Measured by |
|---|---|---|
| AM1 | Duplicate articles are not represented as multiple independent adverse events where provider grouping is available (provider-aware); no clustering engine is built. | Given a `ScreeningProvider`/adverse-media fixture where the provider groups duplicate articles, the grouped duplicates surface as one adverse event, not several; a test asserts grouping consumes provider-supplied grouping only and no clustering engine exists; where no provider grouping is available, duplicates remain separate (measured before any lightweight dedup). |

### Export

| # | Criterion | Measured by |
|---|---|---|
| E1 | Exported facts remain traceable — every material fact in an export links back to its stored evidence or is marked unresolved (as in the report). | Export a case; each material fact carries its provenance/evidence reference or an explicit unresolved marker (reinforces C2/C3/X10); deterministic test. |
| E2 | Restricted vendor content / source content is not exported where licensing prohibits it. | Export a case containing a source whose adapter-declared `license_class` prohibits redistribution; that content is withheld from the export (a licensing guard), while the traceable reference remains; deterministic test. Export is **secondary** to the management report (§7/M11), not a replacement for it. |
