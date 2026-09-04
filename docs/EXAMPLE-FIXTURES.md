# Example Fixtures (canonical, fictional)

**Status:** Canonical. This is the **single** set of example data used across all
Sentinel documentation, wireframes, and (later) tests.

**Hard rule (public repo).** Every example in this repository is **fictional and
invented**. No real ARIE client, counterparty, prospect, contact, or
management-derived label may appear in any document, fixture, or test. "No
secrets" is **not** the same as "no real operational data" — real
management-derived labels are operational data and are prohibited here
(`SECURITY-BOUNDARIES.md`). Any resemblance to a real organisation or person is
coincidental. Use only `.test` / `.example` domains.

If you need a new example, extend this set rather than inventing ad-hoc names, so
the documentation stays coherent and auditable.

---

## Counterparties (resolved legal entities)

| Fixture | Detail |
|---|---|
| **Vantar Energy Trading FZE** | Primary. UAE Free Zone · Reg 12345 · incorporated 14 Feb 2025 · status Active. Domain `vantar-energy.test`. |
| **Vantar Energy Trading Ltd** | Ambiguity sibling. UK · Companies House 09876543 · Active. |
| **Vantar Energy Trading LLC** | Ambiguity sibling. USA (Delaware) · Active. |
| **Castellan Trading FZE** | Second counterparty (used for dedup/link and related-parties examples). |

## Raw labels (as management might record them — messy, pre-resolution)

| Fixture | Illustrates |
|---|---|
| `Vantar - Castellan` | Combined "brand - brand" company label that still resolves to one legal entity. |
| `?? Halcyon Oil` | A tentative/uncertain company label. |
| `NORDIC-HALCYON` | A composite prospect label. |
| `TBD` | Too-generic company label → `CLARIFICATION_REQUIRED`. |
| `Unnamed Refinery` | Generic descriptor, not a legal name → `CLARIFICATION_REQUIRED`. |

## Contacts

| Fixture | Illustrates |
|---|---|
| **Jordan Rivera** | A clean full contact name. |
| `NOVEXA - Amara - via Delta Trading` | A messy contact label: several parties + an intermediary in one field. |
| `Amara` | First-name-only contact. |
| `JR` | Initials-only contact. |

## Domain

| Fixture | Detail |
|---|---|
| `vantar-energy.test` | The primary counterparty's claimed domain. |

## Non-evidentiary `case_context` (imported commercial/management context)

All illustrative only, and never evidence (`CLAIMS-EVIDENCE-MODEL.md` §2.10):

| Key | Example value |
|---|---|
| `management_reference` | `REF-207` |
| `buyer_seller` | `buyer` |
| `internal_tier` | `T2` (an ARIE internal reference — **never** a Sentinel risk rating) |
| `product` | `Product-A` (generic placeholder; commercial terms are not analysed in Phase 1) |
| `incoterm` | `CIF` (a standard trade term, not identifying) |
| `port` | `Port A` |
| `commercial_comments` | free text (retained, not analysed) |

> A composite management row therefore looks like:
> `REF-207 / Castellan Trading / Amara / Product-A` — a reference, a counterparty
> label, a contact label, and a generic product placeholder — all retained as
> non-evidentiary `case_context`, never as evidence.
