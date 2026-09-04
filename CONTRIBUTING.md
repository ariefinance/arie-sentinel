# Contributing to ARIE Sentinel

Thank you for contributing to `ariefinance/arie-sentinel`. Please read this
guide in full before opening a pull request. It applies to human contributors
and to AI assistants (including Claude) working in this repository.

---

## 1. This is currently a specification repository

There is **no application code in this repository yet, and none may be added
until the specification is reviewed and approved.** During the specification
phase, contributions are limited to:

- specification and design documents under `docs/`;
- repository support files (this file, `README.md`, `.gitignore`,
  `.env.example`);
- corrections that keep documents internally consistent.

Do **not** add application code, dependencies, build tooling, CI that builds an
application, or framework scaffolding until [`docs/BUILD-PLAN.md`](docs/BUILD-PLAN.md)
records that the spec is approved and the build has started. Framework and
vendor choices are deliberately deferred (see
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §9 and §17 of the Technical
Challenge Log); do not pre-empt them.

## 2. The Technical Challenge Protocol

Sentinel is a compliance-grade system. Silently implementing a questionable
technical choice is not acceptable — surfacing it is. **Contributors and AI
assistants must raise a TECHNICAL CHALLENGE** rather than quietly proceeding
whenever a proposed approach seems wrong, risky, or better done another way.

Raise a challenge using this structure (in the PR description, an issue, or the
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) Technical Challenge Log):

- **Proposed approach** — what is currently specified or requested.
- **Concern** — what is wrong, risky, or unclear about it.
- **Better approach** — the alternative you recommend.
- **Why** — the reasoning and evidence.
- **Impact** — `LOW`, `MEDIUM`, or `HIGH`.

Act on the impact level:

- **LOW** — fix it and record the change (a note in the PR or the challenge log).
  No approval needed.
- **MEDIUM** — apply the better approach **only if it does not alter approved
  behaviour**; document the change and its rationale. If it would alter approved
  behaviour, treat it as HIGH.
- **HIGH** — **stop and request a decision.** Do not implement either path until
  the owner signs off. HIGH covers anything that changes approved behaviour,
  scope, the data model, security boundaries, or the truth boundary.

The verdict vocabulary is **ACCEPT / MODIFY / DEFER / REJECT**, matching the
Technical Challenge Log in `docs/ARCHITECTURE.md`. Record material verdicts
there.

## 3. Commit and branch conventions

- **Branches:** short, descriptive, kebab-case, prefixed by type —
  `docs/…`, `spec/…`, `fix/…`, `chore/…` (e.g. `docs/clarify-identity-gate`).
  Never commit directly to the default branch; open a pull request.
- **Commits:** imperative mood, concise subject (≤ 72 chars), with a body
  explaining *why* when the change is non-trivial. Conventional-Commits-style
  prefixes (`docs:`, `fix:`, `chore:`, `spec:`) are encouraged.
- **Pull requests:** describe the change, link the relevant `docs/` sections,
  and include any Technical Challenge raised. Keep PRs focused.
- One logical change per PR; do not mix documentation edits with unrelated
  reformatting.

## 4. Terminology must stay consistent

[`docs/SCREEN-STATES.md`](docs/SCREEN-STATES.md) holds the **canonical enums**
for screen and case states. All other documents, copy, and (later) code must use
those exact terms. If you need a term that does not exist, propose it in
`SCREEN-STATES.md` first via a Technical Challenge — do not introduce a synonym
or a local variant elsewhere. Terminology drift is treated as a defect.

## 5. Public-repository secret hygiene (hard rules)

This repository is **public**. Everything committed is world-readable and
permanent. Never commit:

- secrets of any kind — API keys, passwords, tokens, vendor credentials,
  production URLs, internal hostnames;
- real or confidential data — internal ARIE case data, KYC, passports, bank
  details, confidential compliance rules;
- proprietary vendor response payloads.

Controls every contributor must follow:

- `.env.example` contains **placeholders only**; the real `.env` is git-ignored
  and must never be committed.
- **All sample data is fictional** — use `.test`/`.example` domains and invented
  names in every doc, fixture, and test.
- Run a **pre-commit secret scan** (e.g. `gitleaks` or `detect-secrets`) before
  pushing, and keep **GitHub secret scanning enabled** on the repository.
- Do not commit configuration that reveals internal topology.

If a secret is ever committed, treat it as compromised: rotate it immediately
and report it — removing it from history is not sufficient.

## 6. Evidence-based language (required everywhere)

Sentinel reports evidence, not verdicts. In code, documents, identifiers,
comments, and user-facing copy you must **never** state or imply that a company
or person is *safe*, *fraudulent*, *genuine*, *fake*, *suspicious*, *verified
credibility*, or any subjective character judgment.

Report what sources show, what the counterparty claims, where they diverge, and
what to do next.

| Not allowed | Allowed |
|---|---|
| "Suspicious website." | "Domain registration substantially post-dates legal entity formation." |
| "Person probably fake." | "No reliable evidence located linking the named person to the legal entity." |
| "Genuine company." | "Legal entity confirmed against [registry]; status: active." |

The truth boundary — **source fact** vs **counterparty claim** vs **system
assessment** — must never be blurred, and AI/LLM output is never evidence by
itself (see [`docs/PHASE-1-SCOPE.md`](docs/PHASE-1-SCOPE.md) §6–§7 and
[`docs/CLAIMS-EVIDENCE-MODEL.md`](docs/CLAIMS-EVIDENCE-MODEL.md)).

## 7. Accessibility

All UI specifications and (later) implementations target **WCAG 2.2 AA**.
Contributions to design and UI documents must keep this intent: sufficient
contrast, keyboard operability, meaningful focus states, accessible names, and
no reliance on colour alone to convey provenance or state.

## 8. No Phase 2 scope

No Phase 2 functionality may be introduced — in code, schema, navigation, report
sections, or copy. The exclusion list in
[`docs/PHASE-1-SCOPE.md`](docs/PHASE-1-SCOPE.md) §5 is authoritative. "Helpful"
scope creep will be rejected on sight; if something seems necessary, raise a
Technical Challenge rather than building it.
