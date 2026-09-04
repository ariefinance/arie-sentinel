# Design System Foundation

**Status:** Foundational. Defines the minimal design language before any UI is
built. Implementation-neutral: describes intent, tokens, and rules — not React
components.

**North star:** institutional, controlled, evidence-led, calm, high-trust. This
is professional financial-services investigation software, **not** an analytics
dashboard. When in doubt, choose the quieter option.

---

## 1. Design principles

1. **Evidence over ornament.** No decorative metrics, no giant charts, no
   dashboard card grids. Screen real estate goes to text, evidence, and state.
2. **Calm by default.** Restrained palette; colour reserved for meaning, used
   sparingly. No wall of red.
3. **Legibility first.** Generous typographic hierarchy and whitespace beat
   density. An analyst reads; the type must support sustained reading.
4. **State is always explicit.** Every status is a word, not just a colour
   (`SCREEN-STATES.md`).
5. **Truth boundary is visible.** Source fact, counterparty claim, and system
   assessment are visually distinct everywhere (see §6).
6. **Desktop-first, responsibly responsive.** Optimised for analyst desktop;
   remains usable and readable at smaller widths.
7. **Accessible.** Target WCAG 2.2 AA where practical (contrast, focus, keyboard,
   non-colour status, target sizes).

## 2. Typography hierarchy

A single, highly-legible system stack (implementation may substitute a licensed
face later). Roles, not pixel dogma:

| Role | Use | Weight | Relative scale |
|---|---|---|---|
| Display | Report title, case name | 600 | ~28–32px |
| H1 | Screen title | 600 | ~22–24px |
| H2 | Section heading | 600 | ~18px |
| H3 | Sub-section / finding title | 600 | ~15–16px |
| Body | Primary reading text, evidence excerpts | 400 | ~14–15px, line-height ≥1.5 |
| Label | Field labels, table headers | 500, slight tracking | ~12–13px |
| Mono | IDs, registry numbers, hashes, timestamps | 400 | ~13px |

Rules: max ~80 characters per line for body; never justify; never rely on
italics alone to convey meaning.

## 3. Spacing system

4px base unit. Allowed steps: **4, 8, 12, 16, 24, 32, 48, 64**. Section rhythm
uses 24/32; intra-component uses 8/12/16. Consistency over cleverness.

## 4. Colour & status treatment

Neutral, institutional base; semantic colours are muted and always paired with
a label + icon. **Colour never conveys state alone** (acceptance criterion).

Token roles (exact hex chosen at build; these are semantic slots):

- **Neutrals:** `surface`, `surface-raised`, `border`, `text-primary`,
  `text-secondary`, `text-muted`. A near-white/warm-grey ground, dark slate
  text. This carries ~90% of every screen.
- **Semantic (muted, label-paired):**
  - `attention` — findings needing attention / contradictions.
  - `caution` — inconsistencies / limitations / partial.
  - `positive` — verified/confirmed facts (used sparingly; not "safe").
  - `info` — neutral system notes.
- **Focus/interactive:** a single restrained accent for links, primary
  actions, and focus rings.

Each semantic colour must meet ≥3:1 against its background for non-text UI and
≥4.5:1 for text, and must remain distinguishable in greyscale (rely on
label+icon+shape). Status is expressed as a **status pill**: `● LABEL` where the
dot is reinforcement, the word is the message.

Positive/verified states must never be rendered as reassurance ("safe",
"genuine"). They state the evidentiary fact only ("Legal entity confirmed").

## 5. Core components (visual contracts)

Defined in detail in `COMPONENT-INVENTORY.md`; the design system fixes their
character:

- **Status pill** — label-led, icon + muted colour, greyscale-safe.
- **Tables** — quiet: light row separation, no zebra noise, right-aligned
  numerics, monospace for IDs, sortable headers, sticky header on scroll.
- **Evidence card / drawer** — source title, class, reference, retrieved
  timestamp, excerpt, supports/contradicts, limitations, analyst validation.
- **Finding panel** — four fixed labelled regions: **CLAIM / EVIDENCE /
  ASSESSMENT / ACTION** (§6).
- **Forms** — labels above inputs, clear required/optional, inline validation,
  no placeholder-as-label.
- **Buttons** — one primary per view; destructive/irreversible actions are
  visually distinct and confirmed.
- **Tabs** — case workspace navigation; current tab unmistakable (not colour
  alone: weight + underline + `aria-current`).
- **Alerts / banners** — for case-level state (source unavailable, ambiguous
  identity gate); labelled, dismissible only where safe.

## 6. Truth-boundary treatment (mandatory)

Three visually distinct presentations, used consistently across all screens and
the report:

| Kind | Visual treatment | Example label |
|---|---|---|
| **Source fact** | Solid left rule, neutral/positive, source chip attached | "Registry — authoritative" |
| **Counterparty claim** | Quoted style, distinct claim marker, muted | "Counterparty claim" |
| **System assessment** | Distinct "assessment" marker, clearly labelled as Sentinel's reasoning | "Sentinel assessment" |

An analyst must be able to tell these apart at a glance, without reading the
whole sentence, and without relying on colour alone.

## 7. Finding panel anatomy

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

The four regions are always present and always labelled; never collapsed into
a one-line verdict.

## 8. State presentations

Skeletons for loading; explanatory empty states; partial dividers; recoverable
error blocks; reasoned disabled states — all specified in `SCREEN-STATES.md` §8.
No spinners-without-context; no dead ends.

## 9. Audit / history presentation

A quiet, chronological, read-only timeline: actor, action, timestamp, and
rationale where present. Uses `Label` + `Mono` type roles. Not a feature to
show off — a record to trust.

## 10. Branding

Use ARIE branding restrainedly (wordmark, one accent). **Do not** invent flashy
branding, gradients, glass effects, or animation flourishes. Credibility comes
from restraint and clarity.

## 11. Accessibility checklist (WCAG 2.2 AA targets)

- Contrast: text ≥4.5:1, large text/UI ≥3:1.
- Full keyboard operability; visible focus ring on every interactive element.
- Status conveyed by text/icon/shape, never colour alone.
- Target size ≥24×24px; forms have programmatic labels and error association.
- Respects reduced-motion; no essential info in motion.
- Landmark structure and heading order match visual hierarchy.
