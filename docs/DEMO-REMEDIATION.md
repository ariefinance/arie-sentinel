# Management-demo remediation (pre-demo)

Bounded remediation of the blockers and majors from the independent adversarial
review, before the management demo. No architecture change, no live-provider /
OIDC work, no Phase 2.

## Findings addressed

| ID | Finding | Fix |
| -- | ------- | --- |
| B1 | Fixture data could leak to unsupported near-match names (loose token matching). | `demo_dataset.DEMO_CASES` is now the single source of truth; corporate discovery, case-type classification and seeding all resolve by **exact normalised alias**. No token/substring/fuzzy matching. Unsupported near-matches raise `DemoDatasetUnsupported` → "Not available in the management-demo dataset". |
| B2 | Frontend auto-authored analyst rationale on one click. | Resolution and disposition rationale fields start empty and are analyst-authored. High-impact actions (entity selection, `CONFIRMED_MATCH`, `FALSE_POSITIVE`, finding confirm/dismiss) require an explicit confirm step. Server-side minimum rationale length raised to 10 (`schemas.MIN_RATIONALE_LENGTH`). |
| M1 | Curated fixture/public summaries were labelled as live web captures. | Curated demo summaries are flagged (`RetrievedPage.curated`) and stored as `captured_by="fixture:curated_summary"` with a non-live limitation; fictional URLs say "no live page was retrieved". The ARIE public registry citation is `captured_by="fixture:public_registry_citation"`; fixture-mode registry candidates are labelled `fixture:corporate_registry`. |
| M2 | PDF dropped source limitations and the resolution rationale, and carried no case-type marker. | The report now shows the case type, a concise non-live marker (`MANAGEMENT DEMO · … · NON-LIVE`), a **Limitations** column in the Sources table, and the analyst `RESOLVE_IDENTITY` actor / timestamp / rationale (distinct from the provider match basis). |
| M3 (demo portion) | Worker could die silently on a transient error; terminal failures left investigations stuck. | The worker loop survives cycle errors (log + rollback + bounded backoff + continue). Terminal job failure sets the investigation to `FAILED` and records an audit event. Malformed provider responses (`ProviderInvalidResponse`) map to the existing source-unavailable/limited semantics instead of crashing. |

## §7 fixture screening wording

A clean fixture result never reads as a real clearance. For a `FICTIONAL_TEST_CASE`,
UI and PDF read "Fictional screening scenario completed with no material fixture
matches." Public-validation cases keep "Live sanctions/PEP screening was not
performed. No screening conclusion should be inferred."

## ARIE public-fact spot check (§27)

Primary sources (ariefinance.com, fscmauritius.org, companies.govmu.org) are
blocked by this environment's network egress proxy, so they could not be opened
directly. Third-party search corroboration only:

- **Legal name / regulation**: "ARIE Finance" is a real Mauritius (Ebene)
  FSC-regulated financial firm — corroborated by multiple third-party
  aggregators. Treated as reasonable public corroboration, not primary proof.
- **Company number `C221997`**: NOT independently verified from any accessible
  primary source. The existing limitation is retained ("Current status not
  established from cited source").
- **Licence `GB25205028`**: appears in company-controlled / aggregator content as
  a Payment Intermediary Services licence. **Classification: company-controlled**
  — not upgraded to regulator-confirmed, because the live FSC register could not
  be opened. The fixture already frames it as "a company-controlled public
  statement, not independent regulator confirmation".

Per §27/§28, because no stronger primary source was reachable, the current
official source (govmu registration list) and its explicit limitation are kept;
no unverified third-party corporate directory is cited.

## Automated Basic Auth safety check (§26)

`apps/api/deploy/check_basic_auth.py` verifies the deployed demo Basic Auth is
NOT the CI fixture (`sentinel-demo` / `test`) via a behavioural probe and/or a
Railway config read, printing only `PASS/FAIL` (never the credential/hash). With
`--rotate` and Railway access it generates a strong nginx-compatible credential,
updates the Railway variable, and writes the new plaintext to a local file.

## Deferred to the live pilot (NOT in this pass)

These pilot-only review findings are intentionally out of scope here and precede
real counterparties:

- M4 production dev-auth fail-open hardening; nginx `X-Dev-Role` stripping.
- M5 httpx token/PII logging (set httpx logger to WARNING).
- M6 former-officer handling; `CORROBORATED` vs `VERIFIED`.
- Frontend OIDC client (`configureTokenProvider`) and IdP app registration.
- **Worker as its own Railway service with a restart policy.** For the demo the
  API+worker co-process is acceptable now that the loop is resilient; a separate
  supervised worker service is a pilot task (`compose.pilot.yml` already has the
  shape).
- Non-owner production DB role; production backups; JWKS caching; live provider
  credentials and approvals.
