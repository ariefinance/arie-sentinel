import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Button } from '../components/primitives/Button';
import { EvidenceDrawer } from '../components/primitives/EvidenceDrawer';
import { ErrorState, LoadingState } from '../components/primitives/StateBlocks';
import { StatusPill } from '../components/primitives/StatusPill';
import { api } from '../lib/api';
import {
  useFindings,
  useInvestigation,
  useResolveEntity,
  useReviewFinding,
  useReviewScreening,
  useScreening,
  useSources,
} from '../lib/queries';
import { humanizeState, identityTone, investigationTone, screeningTone } from '../lib/status';

const TABS = ['SUMMARY', 'FINDINGS', 'COMPANY', 'PERSON', 'SCREENING'] as const;
type Tab = (typeof TABS)[number];
const when = (value: string) => new Date(value).toLocaleString();
const caseTypeLabel = (value: string | null): string | null => {
  if (value === 'PUBLIC_VALIDATION_CASE') return 'Public Validation Case';
  if (value === 'FICTIONAL_TEST_CASE') return 'Fictional Test Case';
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
  const [tab, setTab] = useState<Tab>('SUMMARY');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [rationale, setRationale] = useState(
    'Selected after reviewing registry identifiers and jurisdiction.',
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirmFinalise, setConfirmFinalise] = useState(false);
  const isManager = api.getCurrentRole() === 'manager';

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
          <Fact
            label="Resolved entity"
            value={data.counterparty?.legal_name ?? 'Not yet resolved'}
          />
          <Fact label="Contact" value={data.contact_label.trim() || 'No contact supplied'} />
        </div>
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
          <Button onClick={() => setDrawerOpen(true)}>View sources</Button>
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
        {tab === 'SUMMARY' ? (
          <section className="panel">
            <h2 className="panel__title">Summary</h2>
            <p>
              Identity:{' '}
              {data.investigation_state === 'SOURCE_UNAVAILABLE' && data.clarification_reason
                ? 'Not searched'
                : humanizeState(data.company_identity_status ?? 'NOT_VERIFIED')}
            </p>
            <p>Completeness: {humanizeState(data.completeness_state ?? 'NOT ASSESSED')}</p>
            <p>
              {data.clarification_reason ??
                data.company_match_basis ??
                'No authoritative resolution has been recorded.'}
            </p>
            <p>
              <Link to="/cases">← Back to worklist</Link>
            </p>
          </section>
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
                            <Button
                              disabled={
                                !candidate.registry_id ||
                                !candidate.jurisdiction ||
                                resolve.isPending
                              }
                              onClick={() =>
                                resolve.mutate({
                                  candidateId: candidate.entity_candidate_id,
                                  rationale,
                                })
                              }
                            >
                              Select entity
                            </Button>
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
                <Button
                  onClick={() =>
                    reviewScreening.mutate({
                      resultId: item.screening_result_id,
                      disposition: 'FALSE_POSITIVE',
                      rationale:
                        'Analyst reviewed the identifiers and determined this is not the subject.',
                    })
                  }
                >
                  Mark false positive
                </Button>{' '}
                <Button
                  onClick={() =>
                    reviewScreening.mutate({
                      resultId: item.screening_result_id,
                      disposition: 'CONFIRMED_MATCH',
                      rationale:
                        'Analyst corroborated the matched identifiers against retained evidence.',
                    })
                  }
                >
                  Confirm match
                </Button>
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
                    ? 'Screening completed with no material matches.'
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
                <h3>{item.title}</h3>
                <p>{item.assessment_text}</p>
                <p>
                  <strong>Evidence:</strong> {item.evidence_text}
                </p>
                <p>
                  <strong>Action:</strong> {item.action_text}
                </p>
                <p>Review: {item.review_status}</p>
                <Button
                  onClick={() =>
                    reviewFinding.mutate({
                      findingId: item.finding_id,
                      disposition: 'CONFIRMED',
                      rationale: 'Analyst reviewed the linked evidence and confirms this finding.',
                    })
                  }
                >
                  Confirm
                </Button>{' '}
                <Button
                  onClick={() =>
                    reviewFinding.mutate({
                      findingId: item.finding_id,
                      disposition: 'DISMISSED',
                      rationale: 'Analyst reviewed the linked evidence and dismisses this finding.',
                    })
                  }
                >
                  Dismiss
                </Button>
              </article>
            ))}
          </section>
        ) : null}
      </div>

      <EvidenceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Sources and provenance"
      >
        {sources.isPending ? (
          <LoadingState label="Loading sources…" rows={3} />
        ) : (
          sources.data?.map((source) => (
            <article key={source.source_id}>
              <h3>{source.title}</h3>
              <p>
                {source.source_class} · retrieved {when(source.retrieved_at)}
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
          ))
        )}
        {sources.data?.length === 0 ? <p>No sources retained yet.</p> : null}
      </EvidenceDrawer>
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
