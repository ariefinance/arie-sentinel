import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Button } from '../components/primitives/Button';
import { StatusPill } from '../components/primitives/StatusPill';
import { EvidenceDrawer } from '../components/primitives/EvidenceDrawer';
import { ErrorState, LoadingState } from '../components/primitives/StateBlocks';
import { useAudit, useInvestigation } from '../lib/queries';
import {
  humanizeState,
  identityTone,
  intakeTone,
  investigationTone,
  screeningTone,
  IDENTITY_NOT_RESOLVED_DISPLAY,
  SCREENING_NOT_RUN_DISPLAY,
} from '../lib/status';
import type { ReactNode } from 'react';
import type { AuditEventOut, InvestigationOut, PersonCandidate } from '../lib/types';

const TABS = ['SUMMARY', 'FINDINGS', 'COMPANY', 'PERSON', 'SCREENING'] as const;

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function Investigation() {
  const { id = '' } = useParams();
  const investigation = useInvestigation(id);
  const audit = useAudit(id);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerSubject, setDrawerSubject] = useState('Source record');

  function openEvidence(subject: string) {
    setDrawerSubject(subject);
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
            investigation.error instanceof Error
              ? investigation.error.message
              : 'The investigation is unavailable.'
          }
          onRetry={() => void investigation.refetch()}
        />
        <p className="page__backlink">
          <Link to="/cases">← Back to worklist</Link>
        </p>
      </div>
    );
  }

  const data = investigation.data;

  return (
    <div className="case">
      <CaseHeader data={data} />

      <nav className="tabs" aria-label="Case sections">
        {TABS.map((tab) => {
          const isCurrent = tab === 'SUMMARY';
          if (isCurrent) {
            return (
              <span key={tab} className="tab tab--current" aria-current="page">
                {tab}
              </span>
            );
          }
          return (
            <span key={tab} className="tab tab--disabled" aria-disabled="true">
              {tab}
            </span>
          );
        })}
      </nav>

      <div className="case__body">
        <SummaryPanel data={data} onOpenEvidence={openEvidence} />
        <AuditPanel
          isPending={audit.isPending}
          isError={audit.isError}
          error={audit.error}
          events={audit.data}
          onRetry={() => void audit.refetch()}
        />
      </div>

      <EvidenceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Evidence"
      >
        <p className="drawer-panel__empty">No evidence is available for {drawerSubject} yet.</p>
      </EvidenceDrawer>
    </div>
  );
}

function CaseHeader({ data }: { data: InvestigationOut }) {
  const resolved = data.counterparty;
  const identityConfirmed = data.company_identity_status === 'CONFIRMED';
  // Two independent gates: the legal entity must be confirmed (identity gate),
  // and the report workflow must exist (availability gate). The report is not
  // available yet, so the control stays disabled and never does nothing.
  const reportReason = identityConfirmed
    ? 'Final Report is not yet available.'
    : 'Final Report opens once the legal entity is confirmed.';

  return (
    <header className="case-header">
      <div className="case-header__identity">
        <div className="labelled">
          <span className="labelled__label">Raw label</span>
          <span className="labelled__value">{data.company_label}</span>
        </div>
        <div className="labelled">
          <span className="labelled__label">Resolved entity</span>
          {resolved ? (
            <span className="labelled__value">
              {resolved.legal_name}
              <span className="labelled__detail mono">
                {[resolved.jurisdiction, resolved.registry_class, resolved.registry_id]
                  .filter(Boolean)
                  .join(' · ') || '—'}
              </span>
            </span>
          ) : (
            <span className="labelled__value cell-muted">Not yet resolved</span>
          )}
        </div>
        <div className="labelled">
          <span className="labelled__label">Contact (raw label)</span>
          <span className="labelled__value">{data.contact_label}</span>
        </div>
      </div>

      <div className="case-header__states">
        <StatusPill
          dimension="Intake"
          label={humanizeState(data.intake_state)}
          tone={intakeTone(data.intake_state)}
        />
        <StatusPill
          dimension="Investigation"
          label={humanizeState(data.investigation_state)}
          tone={investigationTone(data.investigation_state)}
        />
        <StatusPill
          dimension="Legal entity"
          label={
            data.company_identity_status
              ? humanizeState(data.company_identity_status)
              : IDENTITY_NOT_RESOLVED_DISPLAY
          }
          tone={identityTone(data.company_identity_status)}
        />
        <StatusPill
          dimension="Screening"
          label={data.screening_state ? humanizeState(data.screening_state) : SCREENING_NOT_RUN_DISPLAY}
          tone={screeningTone(data.screening_state)}
        />
      </div>

      <div className="case-header__actions">
        <Button variant="primary" disabled aria-disabled title={reportReason}>
          Final Report →
        </Button>
        <span className="case-header__gate-reason">{reportReason}</span>
      </div>
    </header>
  );
}

function SummaryPanel({
  data,
  onOpenEvidence,
}: {
  data: InvestigationOut;
  onOpenEvidence: (subject: string) => void;
}) {
  return (
    <section className="panel" aria-labelledby="summary-heading">
      <h2 className="panel__title" id="summary-heading">
        Summary
      </h2>

      {data.intake_state === 'CLARIFICATION_REQUIRED' && data.clarification_reason ? (
        <div className="banner banner--caution" role="note">
          <span className="banner__glyph" aria-hidden="true">
            ◆
          </span>
          <div>
            <p className="banner__title">Clarification required — discovery not started</p>
            <p className="banner__body">{data.clarification_reason}</p>
          </div>
        </div>
      ) : null}

      <div className="summary-grid">
        <SummaryRow label="Intake">
          <StatusPill label={humanizeState(data.intake_state)} tone={intakeTone(data.intake_state)} />
        </SummaryRow>
        <SummaryRow label="Investigation">
          <StatusPill
            label={humanizeState(data.investigation_state)}
            tone={investigationTone(data.investigation_state)}
          />
        </SummaryRow>
        <SummaryRow label="Legal entity">
          {data.company_identity_status ? (
            <StatusPill
              label={humanizeState(data.company_identity_status)}
              tone={identityTone(data.company_identity_status)}
            />
          ) : (
            <span className="cell-muted">{IDENTITY_NOT_RESOLVED_DISPLAY}</span>
          )}
          {data.company_match_basis ? (
            <span className="summary-row__note">Why matched: {data.company_match_basis}</span>
          ) : null}
        </SummaryRow>
        <SummaryRow label="Completeness">
          <span>{data.completeness_state ? humanizeState(data.completeness_state) : '—'}</span>
        </SummaryRow>
        <SummaryRow label="Screening">
          {data.screening_state ? (
            <StatusPill
              label={humanizeState(data.screening_state)}
              tone={screeningTone(data.screening_state)}
            />
          ) : (
            <span className="cell-muted">{SCREENING_NOT_RUN_DISPLAY}</span>
          )}
        </SummaryRow>
      </div>

      <h3 className="panel__subhead">
        Person candidates
        <span className="panel__subhead-count">
          {data.candidates.length} derived — each assessed independently
        </span>
      </h3>
      {data.candidates.length === 0 ? (
        <p className="cell-muted">No person candidate could be derived from the contact label.</p>
      ) : (
        <ul className="candidate-list">
          {data.candidates.map((candidate) => (
            <CandidateCard
              key={candidate.candidate_id}
              candidate={candidate}
              onOpenEvidence={onOpenEvidence}
            />
          ))}
        </ul>
      )}

      <div className="panel__actions">
        <Button variant="secondary" onClick={() => onOpenEvidence('All sources')}>
          Open evidence drawer
        </Button>
      </div>
    </section>
  );
}

function SummaryRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="summary-row">
      <span className="summary-row__label">{label}</span>
      <span className="summary-row__value">{children}</span>
    </div>
  );
}

function CandidateCard({
  candidate,
  onOpenEvidence,
}: {
  candidate: PersonCandidate;
  onOpenEvidence: (subject: string) => void;
}) {
  return (
    <li className="candidate">
      <div className="candidate__head">
        <span className="candidate__fragment">
          from “{candidate.label_fragment}”
        </span>
      </div>
      {candidate.match_basis ? (
        <p className="candidate__basis">Why matched: {candidate.match_basis}</p>
      ) : null}
      <div className="candidate__states">
        <span className="candidate__state-group">
          <span className="candidate__state-label">Person evidence</span>
          <span>{humanizeState(candidate.person_evidence_status)}</span>
        </span>
        <span className="candidate__state-group">
          <span className="candidate__state-label">Relationship</span>
          <span>{humanizeState(candidate.relationship_state)}</span>
        </span>
      </div>
      <button
        type="button"
        className="link-button"
        onClick={() => onOpenEvidence(`Candidate “${candidate.label_fragment}”`)}
      >
        Evidence ▸
      </button>
    </li>
  );
}

function AuditPanel({
  isPending,
  isError,
  error,
  events,
  onRetry,
}: {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  events: AuditEventOut[] | undefined;
  onRetry: () => void;
}) {
  return (
    <section className="panel panel--aside" aria-labelledby="audit-heading">
      <h2 className="panel__title" id="audit-heading">
        Audit &amp; history
      </h2>
      {isPending ? (
        <LoadingState label="Loading history…" rows={3} />
      ) : isError ? (
        <ErrorState
          title="Could not load history"
          message={error instanceof Error ? error.message : 'History is unavailable.'}
          onRetry={onRetry}
        />
      ) : !events || events.length === 0 ? (
        <p className="cell-muted">No recorded events yet.</p>
      ) : (
        <ol className="timeline">
          {events.map((event) => (
            <li key={event.event_id} className="timeline__item">
              <div className="timeline__meta">
                <span className="timeline__action">{event.action}</span>
                <time className="mono timeline__time">{formatWhen(event.created_at)}</time>
              </div>
              <p className="timeline__detail">
                <span className="timeline__actor">{event.actor}</span>
                <span className="cell-muted"> · {event.object_type}</span>
                {event.target_ref ? <span className="mono"> · {event.target_ref}</span> : null}
              </p>
              {event.rationale ? <p className="timeline__rationale">{event.rationale}</p> : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
