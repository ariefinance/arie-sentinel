# Competitive UX / Product-Pattern Audit — Phase 1

**Status:** Audit complete. Drives a **bounded** set of UX corrections (§9, §12).
**Scope:** interaction & workflow patterns only. No branding or visual design was
copied. No Phase 2 scope introduced.

**Objective.** Prove that Sentinel's analyst workflow and UI/UX are as good as —
or better than — mature financial-crime / KYC investigation products, adopt
proven patterns where clearly superior, remove friction those tools carry, and
keep Sentinel's evidence-led differentiation. This is a pattern audit, **not** a
redesign.

**Framing (important).** ARIE Sentinel is an **internal** tool. It is **not** for
sale, **not** competing with the products reviewed, and **not** a
sales-enablement / lead-generation system. "Differentiation" here means only
*where Sentinel is deliberately stricter for correctness* (evidence-led,
could-not-establish states, no scores) — not market positioning. The governing
product principle (this applies to every Phase 1 decision):

> Where a mature, proven interaction or workflow pattern already solves a
> problem well, **imitate it** unless ARIE has a concrete reason not to. Improve
> only where mature products create measurable analyst friction, weak evidence
> traceability, ambiguity, or unnecessary complexity. Do not pursue novelty.
> Target: **familiar institutional investigation software, made simpler, faster,
> and more evidence-transparent for ARIE.**

There is nothing wrong with copying what already works; the rejects in §10 are
rejected for correctness/complexity reasons, not to be different.

---

## 0. Method & honesty caveat (read first)

Research was conducted against **public** material only (vendor product pages,
brochures, fact sheets, help centres, developer docs, demo/marketing pages, and
third-party review/analyst sites such as G2, Capterra, Gartner Peer Insights,
Chartis).

**Constraint:** in this environment, full-page fetch (`WebFetch`) to external
domains was **blocked by the network egress proxy**. Findings therefore rest on
**search-engine summaries/excerpts** of the cited public pages, not on pages we
rendered or screenshotted ourselves. Confidence is graded accordingly:

- **HIGH** — stated plainly in official docs/brochures/help-centres and/or
  corroborated across multiple sources.
- **MED** — single credible public source, or review/secondary sites.
- **LOW** — inferred or thinly evidenced.

**Least-certain dimension:** exact UI *layout* (split-pane vs drawer vs tab), since
no screenshots were viewable — treated as **MED at best**. **Best-substantiated:**
entity-resolution/confidence UX, source provenance, audit trails, report
structure, and recurring weaknesses. No claim here is fabricated; where a
dimension could not be substantiated it is marked LOW or omitted.

---

## 1. Products reviewed

| # | Product | Category |
|---|---|---|
| 1 | LSEG World-Check / World-Check One | Watchlist/PEP/adverse-media screening + Case Manager |
| 2 | ComplyAdvantage (Mesh) | AML screening + monitoring + case management |
| 3 | Moody's — Orbis / Compliance Catalyst / Grid | Entity data + risk screening + reporting |
| 4 | Sayari (Graph / Map) | Entity resolution + ownership/trade network intelligence |
| 5 | Quantexa | Contextual decision intelligence + investigations |
| 6 | Encompass (EC360 / Corporate Digital Identity) | KYC automation / data orchestration |
| 7 | Exiger (DDIQ / Insight 3PM) | AI due-diligence + third-party risk |
| 8 | Sigma360 | Risk intelligence + adverse media + monitoring |

## 2. Sources reviewed (retrieved via WebSearch; direct fetch egress-blocked)

Representative, not exhaustive; full lists retained in research notes.

- **LSEG World-Check One:** product brochure & API fact sheet (lseg.com), KYC
  verification page, "best sanctions screening software 2026", Refinitiv training
  (batch screening & reports), Maxsight/StackGo help.
- **ComplyAdvantage:** AML case-management insight, negative-news/adverse-media
  pages, adverse-media risk-categorisation, "What is Fuzziness?" KB, developer
  docs (docs.complyadvantage.com), Mambu connector flows, G2 / Capterra /
  SoftwareReviews.
- **Moody's:** Compliance Catalyst product page + brochure, Grid product page +
  brochure, UBO screening, Maxsight "Introduction to Grid", Businesswire
  Grid-into-Catalyst.
- **Sayari:** platform/graph, analysts, map pages; documentation.sayari.com
  (entity resolution, resolution API, risk factors); release notes; learn.sayari;
  Capterra.
- **Quantexa:** entity-resolution, graph-analytics, visualisation-exploration,
  intelligence-led-investigations, knowledge-graph & scoring blogs, AML case
  management guide, community KB, Gartner Peer Insights.
- **Encompass:** EC360, platform, digital-audit-trail, data-attribution-lineage,
  CDI profiles, KYC data sources, UBO verification, KYC remediation; fintech.global.
- **Exiger:** DDIQ pages, Insight 3PM, company/personnel vetting, TPRM;
  OpenCorporates case study; Software Advice; G2; The Wealth Mosaic.
- **Sigma360:** home, AI360, AML investigations, EDD, adverse-media screening,
  News Event Resolution, adverse-media agent; PR Newswire; Chartis.

## 3. Strongest proven patterns (worth adopting or retaining)

Ranked by materiality to Sentinel. "Sentinel today" states whether we already
have it.

1. **First-class match-status taxonomy with a persistent "possible/unresolved"
   state** — *World-Check* (Resolved/Positive/Possible/False/Unspecified),
   *ComplyAdvantage* (matchStatus + whitelist + risk level), *Sayari* (identity vs
   "Possibly Same As"). **HIGH.** *Sentinel today:* **already strong** — screening
   4-state, identity CONFIRMED/AMBIGUOUS/NOT_VERIFIED, person-evidence 4-state,
   relationship 5-state. **Retain.**
2. **A dedicated entity-resolution gate before evidence review** — *Moody's*
   resolves the subject to the correct Orbis entity *before* screening. **HIGH.**
   *Sentinel today:* **already strong** — intake gate + identity-resolution gate;
   report blocked until CONFIRMED. **Retain.**
3. **Provenance as a first-class, drill-to-source affordance on every datum** —
   *Sayari* (per-edge/per-risk citation), *Encompass* (attribute lineage to source
   docs), *Moody's Grid* (category/stage/date/source per entry), *Quantexa*
   (score→data→source lineage). **HIGH.** *Sentinel today:* evidence drill-down
   exists. **Retain + strengthen:** show an inline **provenance chip** on every
   fact/finding row so the source class + timestamp is visible *without* opening
   the drawer.
4. **Completeness by explicit gap exposure** — *Encompass* measures the profile
   against a policy attribute checklist and surfaces what's missing; *Moody's*
   dashboards separate in-progress / resolved / unresolved. **HIGH.** *Sentinel
   today:* completeness state + Unknown/Unresolved list. **Retain + strengthen:**
   the report should state **what was checked vs. what could not be established**
   as an explicit checklist, not just a completeness label.
5. **Plain-language "why matched" + the identifiers that drove it** — *Sayari*
   `match_strength` + human-readable `explanation`; *World-Check* secondary
   identifiers. **HIGH.** *Sentinel today:* candidates shown with discriminators.
   **Adopt (low-cost):** attach a short `match_basis` string to each identity
   candidate, screening match, and PersonCandidate ("same registration number" vs
   "name only — weak"), keeping resolution visible and reversible.
6. **Enforced, timestamped rationale with the audit trail visible on the case
   surface** — *ComplyAdvantage* (mandatory notes before a case decision; audit
   log on the case screen), *Sigma360* (accept/dismiss/**overwrite**, all logged),
   *Encompass* (keystroke-level exportable trail). **HIGH.** *Sentinel today:*
   audit log + rationale required on material dismissal. **Retain;** ensure audit
   history is reachable from the case surface (not buried).
7. **Relevance-scoped relationship display instead of a full graph** — *Quantexa*
   auto-compiles only the connections relevant to *this* decision and ships a
   simplified view for non-experts; *Sayari* is profile-first with graph-on-demand.
   **HIGH** (Quantexa publicly acknowledges its full network UI overwhelms
   non-experts). *Sentinel today:* directors/ownership are Phase-1 deliverables but
   have no dedicated presentation. **Adopt (lightweight, no graph DB):** a bounded
   **Related parties** list (directors/officers/owners/linked parties) — each row
   with relationship type, state, and source, expand-on-demand — **not** a
   force-directed graph.

## 4. Weaknesses worth avoiding (substantiated)

1. **Alert-fatigue / unfiltered match dumping** — *ComplyAdvantage* users report
   high false positives and inconsistent notifications. **MED.** → Sentinel biases
   to graded states and low-emphasis "no material match"; never a raw match dump.
2. **Data density that outpaces comprehension** — *World-Check* called "complex";
   *Moody's* relies on faceting to tame 3B-article volume; *Orbis* profiles are
   dense. **MED.** → Sentinel keeps Summary as linked shortlists; relevance
   filtering is the default, not an option.
3. **Graph-first canvas that overwhelms** — *Quantexa* (self-acknowledged),
   *Sayari* multi-edge crowding. **HIGH/MED.** → validates Sentinel's no-graph
   stance; do not make a graph a landing surface.
4. **Numeric risk score / tier as the headline conclusion** — *ComplyAdvantage*
   riskLevel, *Exiger* H/M/L, *Sigma360* scores. **MED.** → Sentinel uses
   evidence-based findings + per-finding severity, never a counterparty "risk
   rating"; ARIE internal tiers stay non-evidentiary (`case_context`).
5. **Opaque AI summary / heavy auto-clear that hides the evidence** — *Sigma360*
   90–95% auto-clear; AI-summary tools generally. **MED.** → Sentinel keeps the
   four-part CLAIM/EVIDENCE/ASSESSMENT/ACTION finding and human adjudication; AI is
   never evidence by itself.
6. **No explicit "could-not-establish" state** — *Exiger DDIQ* & *Sigma360*
   concentrate on found risk; neither publicly signals unverifiable/absent data.
   **LOW/MED.** → this is a **Sentinel differentiator**; keep and make it louder in
   the report.
7. **Export that is a data dump, not a traceable narrative** — *Sigma360* export
   skews to CSV metrics/decisioning logs; *DDIQ* "amazing amount of information"
   hints at bloat. **MED.** → Sentinel's report stays concise with every statement
   click-through to evidence.
8. **Disambiguation that offloads matching onto the analyst** — *World-Check* asks
   analysts to add DOB/nationality manually; *Moody's* resolution gate adds
   friction on thin subjects. **MED.** → Sentinel proposes candidates and asks only
   for the **minimum** discriminator; the system does the matching work.
9. **Workflow-plumbing audit gaps** — *Exiger* reviewers cite a missing
   "return to search results" and weak audit on questionnaire dispatch. **MED.** →
   Sentinel audits state changes and preserves context (see interaction budget).

## 5. Market-vs-Sentinel comparison matrix

| UX / Workflow area | Best observed market pattern | Current Sentinel approach | Verdict |
|---|---|---|---|
| **Intake** | Minimal subject entry; secondary identifiers to cut false positives; policy-driven auto-search (Encompass) | Two raw-label fields; intake **quality gate**; no manufactured entity | **KEEP** |
| **Identity resolution** | Dedicated resolution gate + tiered confidence + "why matched" (Moody's, Sayari) | Resolution gate; AMBIGUOUS blocks report; minimum discriminator | **MODIFY** — add `match_basis` "why matched" + driving identifiers |
| **Summary** | Faceted overview; risk-ranked queue (Moody's, Exiger) | Five-question linked shortlists; no scores; no data dump | **KEEP** |
| **Company** | Provenanced profile + ownership hierarchy (Encompass, Moody's, Sayari) | Fact blocks w/ provenance; directors/ownership; domain timing | **MODIFY** — add inline provenance chips + lightweight **Related parties** list |
| **Person** | Single entity record; RCA/associates (World-Check) | 0..N PersonCandidates, per-candidate states | **KEEP** (add provenance chips) |
| **Screening** | Match-status taxonomy + adjudication; adverse-media event grouping (all) | 4-state screening; human adjudication; never auto-decide | **KEEP** (add `match_basis`) |
| **Evidence** | Drill-to-source in context; evidence package export (Sayari, Quantexa) | Evidence as its **own primary tab** + inline links | **MODIFY** — make Evidence a **drawer in context** (+ secondary "All sources" browse); drop from primary tab bar |
| **Findings** | Risk-event structured, traceable, one-click escalate (Exiger) | Four-part CLAIM/EVIDENCE/ASSESSMENT/ACTION; severity; audited actions | **KEEP** (promote in tab order — see §7) |
| **Final report** | Auto DD report, source-traceable, gap exposure (Encompass, Exiger); avoid CSV dump / opaque summary (Sigma360) | 8 fixed sections; traceable; gated on CONFIRMED | **MODIFY** — add explicit **Named Person** + **Screening** sections; make completeness a **checked-vs-not-established** checklist |

## 6. Interaction-budget assessment

| Target | Budget | Current | Proposed | Result |
|---|---|---|---|---|
| Start investigation | No field before search beyond the essentials | 2 raw-label fields only | unchanged | **PASS** |
| Identity clarification | Minimum discriminator only | Intake Clarification + Identity Resolution both ask minimum | unchanged | **PASS** |
| Material finding → evidence | ≤ 2 interactions | Finding → **Evidence tab** = context switch | Finding → **evidence drawer** = 1 interaction | **MODIFY → PASS** |
| Summary → material issue | ≤ 1 interaction | Summary lists high-severity findings; each links | unchanged | **PASS** |
| Analyst finding decision | ≤ 2 (excl. rationale) | Confirm/Dismiss = 1 | unchanged | **PASS** |
| Return to investigation context | Never navigate back through multiple pages | Evidence-as-tab risks a page round-trip | Drawer closes back to context in place | **MODIFY → PASS** |
| Final report | All critical unresolved visible without hunting across tabs | Unknown/Unresolved present; screening/person implicit | Add Screening + Named Person + completeness checklist | **MODIFY → PASS** |

The budget analysis independently produces the **same two structural changes**
(evidence-in-context drawer; report completeness/screening/person) as the pattern
research — they are convergent, not additive wish-list items.

## 7. Navigation / IA verdict

**Challenge outcome (six-tab workspace):**

- **Evidence as a primary tab → MODIFY.** The market norm is drill-to-source **in
  context** (profile-first with evidence reached from a fact/finding), not a
  separate evidence destination. A dedicated Evidence tab forces a context switch
  that violates the "return to context" and "finding → evidence" budgets. **Make
  Evidence a drawer/side-panel** opened from any fact/finding (1 interaction,
  closes back), and keep a **secondary "All sources" browse** for the legitimate
  "review everything captured" need. This overturns the earlier
  `INFORMATION-ARCHITECTURE.md` §6 rejection of drawer-only evidence, now that the
  interaction budget and market norm both favour it — the "browse all" need is met
  by the secondary view rather than a primary tab.
- **Findings ordering → MODIFY (modest).** Mature tools lead the analyst with the
  "what needs my attention" queue. Promote **FINDINGS to position 2** (adjacent to
  Summary) to tighten the read-position → act loop. Interaction count is unchanged;
  discoverability improves.
- **Screening placement → KEEP separate.** Every screening product gives
  sanctions/PEP/adverse-media its own adjudication surface; folding it into
  Company/Person would bury formal concerns. Confirmed matches still surface as
  findings.
- **Single-view vs tabs → KEEP tabs (trimmed).** A single monolithic scroll would
  reintroduce the data-density weakness. Tabs + an in-context evidence drawer give
  progressive disclosure without a page round-trip.

**Resulting case navigation (6 → 5 tabs):**

```
SUMMARY · FINDINGS · COMPANY · PERSON · SCREENING      (+ Evidence drawer, everywhere)
```

Evidence is reachable from any fact/finding as a drawer; an "All sources" browse
is a secondary view (e.g. opened from the drawer or a header affordance).

## 8. Final-report verdict

**MODIFY.** The report is strong (traceable, no opaque AI summary, explicit
unknowns) but does not make all eight management questions *immediately* obvious.
Restructure the fixed sections to map 1:1 to the questions, adding the two missing
ones and strengthening completeness:

| # | Management question | Report section |
|---|---|---|
| 1 | Did we resolve the correct legal entity? | **Legal Identity** (keep) |
| 2 | What do we know about the named person? | **Named Person(s)** — *new* (per candidate) |
| 3 | Can we establish the person–company relationship? | **Contact Relationship** (keep) |
| 4 | Any formal screening concerns? | **Screening** — *new* (per screening state) |
| 5 | What material inconsistencies exist? | **Material Findings** (keep) |
| 6 | What could not be established? | **Unknown / Unresolved** (keep) |
| 7 | What action is required? | **Required Actions** (keep) |
| 8 | Material source limitations? | **Research Completeness** → *strengthen* to an explicit **checked-vs-not-established** checklist |

Plus **Verified Facts** (supporting) and **Evidence drill-down** on every material
statement. **No generic AI executive summary.** Every statement stays traceable.

## 9. Specific changes recommended (bounded)

Each change is traceable to a demonstrated workflow improvement, an interaction
reduction, clearer evidence handling, stronger ambiguity handling, or
analyst/management usability. Nothing below adds Phase 2 scope.

- **C1 — Evidence in context (drawer).** Evidence becomes an in-context drawer
  opened from any fact/finding; drop it from the primary tab bar; keep a secondary
  "All sources" browse. *(interaction reduction; return-to-context)*
- **C2 — Tab order.** Case tabs become `SUMMARY · FINDINGS · COMPANY · PERSON ·
  SCREENING`. *(triage-first; usability)*
- **C3 — Inline provenance chips.** Every fact/finding row shows source class +
  retrieved date inline; the drawer gives the full record. *(clearer evidence)*
- **C4 — `match_basis` "why matched".** Identity candidates, screening matches,
  and PersonCandidates carry a short human-readable basis + the identifiers that
  drove the match. *(stronger, reversible ambiguity handling)*
- **C5 — Lightweight Related-parties list.** Company/Person show a bounded
  directors/officers/owners/linked-parties list (type + state + source,
  expand-on-demand); **no graph**. *(presents existing Phase-1 data better)*
- **C6 — Report restructure.** Sections mapped 1:1 to the eight management
  questions; add **Named Person(s)** and **Screening**; make completeness a
  **checked-vs-not-established** checklist. *(management comprehension)*
- **C7 — Audit reachable on the case surface.** Confirm the audit/history is
  accessible from the case surface, not buried. *(auditability)*

Affected documents: `INFORMATION-ARCHITECTURE.md`, `UI-UX-SPEC.md`,
`COMPONENT-INVENTORY.md`, `USER-FLOWS.md`, `SCREEN-STATES.md`,
`CLAIMS-EVIDENCE-MODEL.md` (additive `match_basis`), `ACCEPTANCE-CRITERIA.md`.
`PHASE-1-SCOPE.md`, `ARCHITECTURE.md`, `SECURITY-BOUNDARIES.md`,
`DESIGN-SYSTEM.md`, `BUILD-PLAN.md` are **unaffected** (no scope, backend, or
data-flow change) beyond incidental references.

## 10. Patterns explicitly rejected

- **Interactive network/graph canvas** (Sayari/Quantexa) — overwhelm + no graph
  DB. Replaced by the lightweight Related-parties list (C5).
- **Numeric risk scores / risk tiers as a conclusion** (ComplyAdvantage, Exiger,
  Sigma360) — conflicts with evidence-led, no-score design.
- **Opaque AI executive summary & heavy auto-clear** (Sigma360, AI-summary tools)
  — conflicts with the traceable four-part finding and human adjudication.
- **CSV/metrics data-dump as the deliverable** (Sigma360) — report stays a concise
  traceable narrative.
- **Dashboard/metric-tile landing** (portfolio dashboards) — Sentinel is a
  case workspace, not an analytics dashboard.
- **Analyst-offloaded disambiguation** (World-Check manual identifiers) — Sentinel
  proposes candidates and asks only for the minimum discriminator.
- **Policy-configured auto-search intake** (Encompass) — heavier than Phase 1
  needs; Sentinel's two-field intake + gate is simpler and sufficient.

## 11. Final conclusion

**`BOUNDED UX CORRECTION REQUIRED`.**

Sentinel's core is validated by the market and, on its differentiators
(explicit could-not-establish states, structural truth boundary, traceable
findings, no opaque AI summary, no risk-score reduction), is **ahead** of the
reviewed products. The corrections in §9 are bounded and convergent (pattern
research and the interaction budget independently point to the same few changes):
evidence in context, a tighter tab set, inline provenance, "why matched" basis, a
lightweight related-parties list, and a report restructured to the eight
management questions. No Phase 2 scope, no dashboards, no graphs, no scores, no
application code.
