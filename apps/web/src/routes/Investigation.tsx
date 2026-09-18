import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Button } from '../components/primitives/Button';
import { EvidenceDrawer } from '../components/primitives/EvidenceDrawer';
import { InvestigationBoard } from '../components/InvestigationBoard';
import { RelationshipMap } from '../components/RelationshipMap';
import { ErrorState, LoadingState } from '../components/primitives/StateBlocks';
import { StatusPill } from '../components/primitives/StatusPill';
import { api } from '../lib/api';
import {
  queryKeys,
  useBoard,
  useFindings,
  useGraph,
  useInvestigation,
  useResolveEntity,
  useReviewFinding,
  useReviewScreening,
  useScreening,
  useSources,
} from '../lib/queries';
import { humanizeState, identityTone, investigationTone, screeningTone } from '../lib/status';

const TABS = ['BOARD', 'MAP', 'FINDINGS', 'COMPANY', 'PERSON', 'SCREENING'] as const;
type Tab = (typeof TABS)[number];
const when = (value: string) => new Date(value).toLocaleString();
// Minimum analyst-authored rationale length; mirrors the server-side minimum so
// the UI never submits a decision the API would reject.
const MIN_RATIONALE = 10;
const caseTypeLabel = (value: string | null): string | null => {
  if (value === 'PUBLIC_VALIDATION_CASE') return 'Public Validation Case';
  if (value === 'FICTIONAL_TEST_CASE') return 'Fictional Test Case';
  return null;
};
const nonLiveNote = (value: string | null): string | null => {
  if (value === 'FICTIONAL_TEST_CASE')
    return 'Non-live management demo: fictional fixture data, not a live screening result.';
  if (value === 'PUBLIC_VALIDATION_CASE')
    return 'Non-live management demo: public-source validation only; live screening was not performed.';
  return null;
};

export function Investigation() {
  const { id = '' } = useParams();
  const investigation = useInvestigation(id);
  const sources = useSources(id);
  const screening = useScreening(id);
  const findings = useFindings(id);
  const resolve = useResolveEntity(id);
  const reviewScreening = useReviewScreening(id);
  const reviewFinding = useReviewFinding(id);
  const [tab, setTab] = useState<Tab>('BOARD');
  const board = useBoard(id, tab === 'BOARD');
  const graph = useGraph(id, tab === 'MAP');
  const [drawerOpen, setDrawerOpen] = useState(false);
  // Row-specific evidence drill-down: which source ids + which check opened the drawer.
  const [drawerSelection, setDrawerSelection] = useState<{ ids: string[]; label: string } | null>(
    null,
  );
  // Resolution rationale starts EMPTY and must be analyst-authored (B2).
  const [rationale, setRationale] = useState('');
  const [pendingCandidate, setPendingCandidate] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirmFinalise, setConfirmFinalise] = useState(false);
  const isManager = api.getCurrentRole() === 'manager';

  // Progressive investigation: useInvestigation polls while the state is non-terminal;
  // when the worker advances it, refetch the derived views so completed evidence,
  // board rows, graph, findings and screening appear without a manual refresh.
  const queryClient = useQueryClient();
  const investigationState = investigation.data?.investigation_state;
  useEffect(() => {
    if (!id) return;
    void queryClient.invalidateQueries({ queryKey: queryKeys.board(id) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.graph(id) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.findings(id) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.screening(id) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.sources(id) });
  }, [id, investigationState, queryClient]);

  function openSources(ids: string[], label: string) {
    setDrawerSelection(ids.length > 0 ? { ids, label } : null);
    setDrawerOpen(true);
  }

  if (investigation.isPending) {
    return (
      <div className="page">
        <LoadingState label="Loading investigation…" rows={4} />
      </div>
    );
  }
  if (investigation.isError) {
    return (
      <div className="page">
        <ErrorState
          title="Could not load the investigation"
          message={
            investigation.error instanceof Error ? investigation.error.message : 'Unavailable'
          }
          onRetry={() => void investigation.refetch()}
        />
      </div>
    );
  }
  const data = investigation.data;
  const liveScreeningNotPerformed =
    data.case_type === 'PUBLIC_VALIDATION_CASE' && data.screening_state === null;
  const demoNote = nonLiveNote(data.case_type);

  function requestSelect(candidateId: string) {
    setActionError(null);
    if (rationale.trim().length < MIN_RATIONALE) {
      setActionError(
        `Enter a resolution rationale of at least ${MIN_RATIONALE} characters before selecting an entity.`,
      );
      return;
    }
    setPendingCandidate(candidateId);
  }

  function confirmSelect(candidateId: string) {
    resolve.mutate(
      { candidateId, rationale: rationale.trim() },
      { onSettled: () => setPendingCandidate(null) },
    );
  }

  async function downloadReport() {
    setActionError(null);
    try {
      const blob = await api.createReport(id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `sentinel-${id}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Report generation failed.');
    }
  }

  return (
    <div className="case">
      <header className="case-header">
        <div className="case-header__identity">
          <Fact label="Raw label" value={data.company_label} />
          {caseTypeLabel(data.case_type) ? (
            <Fact label="Case type" value={caseTypeLabel(data.case_type) ?? ''} />
          ) : null}
          {data.investigation_context ? (
            <Fact label="Context" value={data.investigation_context} />
          ) : null}
          <Fact
            label="Resolved entity"
            value={data.counterparty?.legal_name ?? 'Not yet resolved'}
          />
          <Fact label="Contact" value={data.contact_label.trim() || 'No contact supplied'} />
          <Link className="linklike" to="/cases">
            ← Back to worklist
          </Link>
        </div>
        {demoNote ? (
          <p className="banner" role="note">
            {demoNote}
          </p>
        ) : null}
        <div className="case-header__states">
          <StatusPill
            dimension="Investigation"
            label={humanizeState(data.investigation_state)}
            tone={investigationTone(data.investigation_state)}
          />
          <StatusPill
            dimension="Legal entity"
            label={
              data.investigation_state === 'SOURCE_UNAVAILABLE' && data.clarification_reason
                ? 'Not searched'
                : humanizeState(data.company_identity_status ?? 'NOT_VERIFIED')
            }
            tone={identityTone(data.company_identity_status)}
          />
          <StatusPill
            dimension="Screening"
            label={
              liveScreeningNotPerformed
                ? 'Live screening not performed'
                : humanizeState(data.screening_state ?? 'NOT_STARTED')
            }
            tone={screeningTone(data.screening_state)}
          />
        </div>
        <div className="case-header__actions">
          {isManager ? (
            <>
              <label>
                <input
                  type="checkbox"
                  checked={confirmFinalise}
                  onChange={(event) => setConfirmFinalise(event.target.checked)}
                />{' '}
                Confirm final report
              </label>
              <Button
                variant="primary"
                disabled={data.company_identity_status !== 'CONFIRMED' || !confirmFinalise}
                onClick={() => void downloadReport()}
              >
                Final Report →
              </Button>
            </>
          ) : (
            <span>Manager finalisation required</span>
          )}
          <Button onClick={() => openSources([], 'All sources')}>View sources</Button>
        </div>
        {actionError ? <p className="banner banner--error">{actionError}</p> : null}
        {data.investigation_state === 'SOURCE_UNAVAILABLE' && data.clarification_reason ? (
          <div className="banner" role="status">
            <strong>Not available in the management-demo dataset</strong>
            <span>{data.clarification_reason}</span>
          </div>
        ) : null}
      </header>

      <nav className="tabs" aria-label="Case sections">
        {TABS.map((item) => (
          <button
            key={item}
            className={`tab ${tab === item ? 'tab--current' : ''}`}
            aria-current={tab === item ? 'page' : undefined}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </nav>

      <div className="case__body">
        {tab === 'BOARD' ? (
          board.isError ? (
            <ErrorState
              title="Investigation Board unavailable"
              message="The board could not be loaded. This is a technical failure, not an absence of findings."
              onRetry={() => void board.refetch()}
            />
          ) : board.isPending ? (
            <LoadingState label="Building the investigation board…" rows={6} />
          ) : (
            <InvestigationBoard rows={board.data?.rows ?? []} onOpenSources={openSources} />
          )
        ) : null}

        {tab === 'MAP' ? (
          graph.isError ? (
            <ErrorState
              title="Relationship data unavailable"
              message="The relationship map could not be loaded. This is a technical failure, not an absence of relationships."
              onRetry={() => void graph.refetch()}
            />
          ) : graph.isPending ? (
            <LoadingState label="Building the relationship map…" rows={4} />
          ) : (
            <RelationshipMap graph={graph.data ?? { investigation_id: id, nodes: [], edges: [] }} />
          )
        ) : null}

        {tab === 'COMPANY' ? (
          <section className="panel">
            <h2 className="panel__title">Company</h2>
            {data.counterparty ? (
              <dl>
                <dt>Legal name</dt>
                <dd>{data.counterparty.legal_name}</dd>
                <dt>Jurisdiction / registry</dt>
                <dd>
                  {[data.counterparty.jurisdiction, data.counterparty.registry_id]
                    .filter(Boolean)
                    .join(' · ')}
                </dd>
                <dt>Status</dt>
                <dd>{data.counterparty.status ?? 'Not available'}</dd>
              </dl>
            ) : (
              <>
                <p>
                  Choose a registry candidate only after checking its identifiers and jurisdiction.
                  A name match alone is not confirmation.
                </p>
                <label>
                  Resolution rationale
                  <textarea
                    value={rationale}
                    placeholder="Explain, in your own words, why this candidate is the correct legal entity."
                    onChange={(event) => setRationale(event.target.value)}
                  />
                </label>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Legal entity</th>
                        <th>Registry details</th>
                        <th>Source / retrieved</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.entity_candidates.map((candidate) => (
                        <tr key={candidate.entity_candidate_id}>
                          <td>
                            {candidate.legal_name}
                            <br />
                            <span className="cell-muted">
                              {candidate.registered_address ?? 'Address unavailable'}
                            </span>
                          </td>
                          <td>
                            {candidate.jurisdiction ?? '—'} ·{' '}
                            {candidate.registry_id ?? 'no identifier'}
                            <br />
                            {candidate.legal_status ?? 'status unavailable'}
                            <br />
                            {candidate.match_basis}
                          </td>
                          <td>
                            {candidate.provider}
                            <br />
                            {when(candidate.retrieved_at)}
                          </td>
                          <td>
                            {pendingCandidate === candidate.entity_candidate_id ? (
                              <>
                                <p className="cell-muted">
                                  Confirm you authored the rationale above for this selection.
                                </p>
                                <Button
                                  variant="primary"
                                  disabled={
                                    !candidate.registry_id ||
                                    !candidate.jurisdiction ||
                                    resolve.isPending ||
                                    rationale.trim().length < MIN_RATIONALE
                                  }
                                  onClick={() => confirmSelect(candidate.entity_candidate_id)}
                                >
                                  Confirm selection
                                </Button>{' '}
                                <Button onClick={() => setPendingCandidate(null)}>Cancel</Button>
                              </>
                            ) : (
                              <Button
                                disabled={
                                  !candidate.registry_id ||
                                  !candidate.jurisdiction ||
                                  resolve.isPending
                                }
                                onClick={() => requestSelect(candidate.entity_candidate_id)}
                              >
                                Select entity
                              </Button>
                            )}
                          </td>
                        </tr>
                      ))}
                      {data.entity_candidates.length === 0 ? (
                        <tr>
                          <td colSpan={4}>
                            {data.clarification_reason ?? 'No registry candidates were found.'}
                          </td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
        ) : null}

        {tab === 'PERSON' ? (
          <section className="panel">
            <h2 className="panel__title">Person</h2>
            {data.candidates.map((candidate) => (
              <article key={candidate.candidate_id}>
                <h3>{candidate.label_fragment}</h3>
                <p>{humanizeState(candidate.relationship_state ?? 'UNVERIFIED')}</p>
                <p>{candidate.match_basis ?? 'No authoritative relationship evidence retained.'}</p>
                {candidate.relationship_state === 'VERIFIED' ? (
                  <p>
                    Registry evidence verifies a company relationship for a person with this name;
                    it does not conclusively verify the submitted individual&apos;s physical
                    identity.
                  </p>
                ) : null}
              </article>
            ))}
            {data.candidates.length === 0 ? (
              <p>
                <strong>Named contact:</strong> Not supplied
                <br />
                <strong>Person relationship:</strong> Not assessed
              </p>
            ) : null}
          </section>
        ) : null}

        {tab === 'SCREENING' ? (
          <section className="panel">
            <h2 className="panel__title">Screening</h2>
            {screening.data?.map((item) => (
              <article key={item.screening_result_id}>
                <h3>
                  {item.subject_label} — {item.matched_profile_id ?? 'Result'}
                </h3>
                <p>
                  {item.match_basis}{' '}
                  {item.match_score === null ? '' : `(score ${item.match_score})`}
                </p>
                <p>Lists: {item.list_or_source}</p>
                <p>Disposition: {item.analyst_disposition ?? 'Pending review'}</p>
                <DispositionForm
                  subject={item.subject_label}
                  options={[
                    { value: 'FALSE_POSITIVE', label: 'false positive' },
                    { value: 'CONFIRMED_MATCH', label: 'confirmed match' },
                  ]}
                  disabled={reviewScreening.isPending}
                  onSubmit={(disposition, ownRationale) =>
                    reviewScreening.mutate({
                      resultId: item.screening_result_id,
                      disposition,
                      rationale: ownRationale,
                    })
                  }
                />
              </article>
            ))}
            {screening.data?.length === 0 ? (
              liveScreeningNotPerformed ? (
                <div>
                  <h3>Live screening not performed</h3>
                  <p>
                    Sanctions/PEP providers are disabled in this management environment. No live
                    screening conclusion is available.
                  </p>
                </div>
              ) : (
                <p>
                  {data.screening_state === 'NO_MATERIAL_MATCH'
                    ? data.case_type === 'FICTIONAL_TEST_CASE'
                      ? 'Fictional screening scenario completed with no material fixture matches.'
                      : 'Screening completed with no material matches.'
                    : data.completeness_state === 'MATERIAL_SOURCE_UNAVAILABLE'
                      ? 'Screening was not completed because the provider was unavailable.'
                      : 'Screening has not completed yet.'}
                </p>
              )
            ) : null}
          </section>
        ) : null}

        {tab === 'FINDINGS' ? (
          <section className="panel">
            <h2 className="panel__title">Findings</h2>
            {findings.data?.map((item) => (
              <article key={item.finding_id}>
                <h3>
                  {item.title}{' '}
                  <span className="badge" role="note">
                    {humanizeState(item.finding_type)}
                  </span>
                </h3>
                <p>
                  <strong>Claim:</strong> {item.claim_text}
                </p>
                <p>{item.assessment_text}</p>
                <p>
                  <strong>Evidence:</strong> {item.evidence_text}
                </p>
                <p>
                  <strong>Action:</strong> {item.action_text}
                </p>
                <p>Review: {item.review_status}</p>
                <DispositionForm
                  subject={item.title}
                  options={[
                    { value: 'CONFIRMED', label: 'confirm' },
                    { value: 'DISMISSED', label: 'dismiss' },
                  ]}
                  disabled={reviewFinding.isPending}
                  onSubmit={(disposition, ownRationale) =>
                    reviewFinding.mutate({
                      findingId: item.finding_id,
                      disposition,
                      rationale: ownRationale,
                    })
                  }
                />
              </article>
            ))}
          </section>
        ) : null}
      </div>

      <EvidenceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={
          drawerSelection ? `Sources: ${drawerSelection.label}` : 'Sources and provenance'
        }
      >
        {sources.isError ? (
          <ErrorState
            title="Sources unavailable"
            message="Provenance could not be loaded — this is a technical failure, not an absence of sources."
            onRetry={() => void sources.refetch()}
          />
        ) : sources.isPending ? (
          <LoadingState label="Loading sources…" rows={3} />
        ) : (
          (() => {
            const all = sources.data ?? [];
            const shown = drawerSelection
              ? all.filter((s) => drawerSelection.ids.includes(s.source_id))
              : all;
            return (
              <>
                {drawerSelection ? (
                  <p>
                    <button
                      type="button"
                      className="linklike"
                      onClick={() => setDrawerSelection(null)}
                    >
                      Show all investigation sources
                    </button>
                  </p>
                ) : null}
                {shown.map((source) => (
                  <article key={source.source_id}>
                    <h3>{source.title}</h3>
                    <p>
                      {source.source_class} · retrieved {when(source.retrieved_at)} · captured by{' '}
                      {source.captured_by}
                    </p>
                    {source.origin_ref ? (
                      <p>
                        <a href={source.origin_ref} target="_blank" rel="noreferrer">
                          Open source
                        </a>
                      </p>
                    ) : null}
                    <p>{source.limitations}</p>
                  </article>
                ))}
                {shown.length === 0 ? (
                  <p>
                    {drawerSelection
                      ? 'This check has no independently retained source.'
                      : 'No sources retained yet.'}
                  </p>
                ) : null}
              </>
            );
          })()
        )}
      </EvidenceDrawer>
    </div>
  );
}

interface DispositionOption {
  value: string;
  label: string;
}

// A two-step, analyst-authored disposition: choose a disposition, type your own
// rationale, then explicitly confirm. Nothing is submitted on a single click and
// no rationale text is pre-filled (B2).
function DispositionForm({
  subject,
  options,
  disabled,
  onSubmit,
}: {
  subject: string;
  options: DispositionOption[];
  disabled: boolean;
  onSubmit: (disposition: string, rationale: string) => void;
}) {
  const [pending, setPending] = useState<DispositionOption | null>(null);
  const [rationale, setRationale] = useState('');
  const tooShort = rationale.trim().length < MIN_RATIONALE;

  if (!pending) {
    return (
      <div className="disposition">
        {options.map((option) => (
          <Button
            key={option.value}
            disabled={disabled}
            onClick={() => {
              setRationale('');
              setPending(option);
            }}
          >
            {`Mark ${option.label}`}
          </Button>
        ))}
      </div>
    );
  }

  return (
    <div className="disposition">
      <label>
        {`Rationale for “${subject}” — ${pending.label}`}
        <textarea
          aria-label={`Rationale for ${subject}`}
          value={rationale}
          placeholder="Enter your own rationale (min 10 characters). This is recorded as the audit rationale."
          onChange={(event) => setRationale(event.target.value)}
        />
      </label>
      <Button
        variant="primary"
        disabled={disabled || tooShort}
        onClick={() => onSubmit(pending.value, rationale.trim())}
      >
        {`Confirm ${pending.label}`}
      </Button>{' '}
      <Button
        onClick={() => {
          setPending(null);
          setRationale('');
        }}
      >
        Cancel
      </Button>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="labelled">
      <span className="labelled__label">{label}</span>
      <span className="labelled__value">{value}</span>
    </div>
  );
}
