import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/primitives/Button';
import { StatusPill } from '../components/primitives/StatusPill';
import { Table } from '../components/primitives/Table';
import type { Column } from '../components/primitives/Table';
import { EmptyState, ErrorState, LoadingState } from '../components/primitives/StateBlocks';
import { useWorklist } from '../lib/queries';
import { identityTone, investigationTone, screeningTone, SCREENING_NOT_RUN } from '../lib/status';
import type { WorklistFilter, WorklistItem } from '../lib/types';

interface FilterDef {
  value: WorklistFilter;
  label: string;
  /** Neutral empty-state copy per filter (never implies "safe"). */
  empty: string;
}

// Every filter is a view over a canonical state; the worklist coins none of its
// own (UI-UX-SPEC.md §1b).
const FILTERS: FilterDef[] = [
  { value: 'mine', label: 'Assigned to me', empty: 'Nothing is assigned to you right now.' },
  { value: 'needs_action', label: 'Needs action', empty: 'Nothing needs action right now.' },
  {
    value: 'clarification_required',
    label: 'Clarification required',
    empty: 'No investigations are awaiting intake clarification.',
  },
  {
    value: 'identity_ambiguous',
    label: 'Identity ambiguous',
    empty: 'No investigations have an ambiguous legal entity.',
  },
  {
    value: 'screening_review',
    label: 'Screening review',
    empty: 'No screening matches are awaiting review.',
  },
  { value: 'completed', label: 'Completed', empty: 'No completed investigations yet.' },
  { value: 'all', label: 'All', empty: 'No investigations have been created yet.' },
];

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

export function Cases() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<WorklistFilter>('mine');
  const worklist = useWorklist(filter);
  const activeDef = FILTERS.find((f) => f.value === filter) ?? FILTERS[0];

  const columns: Column<WorklistItem>[] = [
    {
      key: 'company_label',
      header: 'Raw label',
      isRowHeader: true,
      render: (row) => <span className="cell-strong">{row.company_label}</span>,
    },
    {
      key: 'contact_label',
      header: 'Contact (raw)',
      render: (row) => <span className="cell-muted">{row.contact_label}</span>,
    },
    {
      key: 'investigation_state',
      header: 'Investigation',
      render: (row) => (
        <StatusPill label={row.investigation_state} tone={investigationTone(row.investigation_state)} />
      ),
    },
    {
      key: 'company_identity_status',
      header: 'Legal entity',
      render: (row) => (
        <StatusPill
          label={row.company_identity_status ?? 'NOT_RESOLVED'}
          tone={identityTone(row.company_identity_status)}
        />
      ),
    },
    {
      key: 'screening_state',
      header: 'Screening',
      render: (row) => (
        <StatusPill
          label={row.screening_state ?? SCREENING_NOT_RUN}
          tone={screeningTone(row.screening_state)}
        />
      ),
    },
    {
      key: 'needs_action',
      header: 'Needs',
      render: (row) =>
        row.needs_action ? (
          <span className="cell-needs">Action required</span>
        ) : (
          <span className="cell-muted">—</span>
        ),
    },
    {
      key: 'updated_at',
      header: 'Last activity',
      align: 'end',
      render: (row) => <span className="mono cell-muted">{formatWhen(row.updated_at)}</span>,
    },
  ];

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Analyst Worklist</h1>
          <p className="page__subtitle">What needs my attention now? A quiet triage view — no scores, no charts.</p>
        </div>
        <div className="page__header-actions">
          <Link to="/" className="btn btn--primary">
            New investigation
          </Link>
        </div>
      </div>

      <div className="chips" role="group" aria-label="Filter investigations">
        {FILTERS.map((def) => {
          const isActive = def.value === filter;
          return (
            <button
              key={def.value}
              type="button"
              className={`chip${isActive ? ' chip--active' : ''}`}
              aria-pressed={isActive}
              onClick={() => setFilter(def.value)}
            >
              {def.label}
            </button>
          );
        })}
      </div>

      <section className="page__body" aria-live="polite">
        {worklist.isPending ? (
          <LoadingState label="Loading worklist…" rows={5} />
        ) : worklist.isError ? (
          <ErrorState
            title="Could not load the worklist"
            message={
              worklist.error instanceof Error
                ? worklist.error.message
                : 'The worklist is unavailable.'
            }
            onRetry={() => void worklist.refetch()}
          />
        ) : worklist.data.length === 0 ? (
          <EmptyState title={activeDef.empty} />
        ) : (
          <>
            <p className="page__count">
              {worklist.data.length} {worklist.data.length === 1 ? 'investigation' : 'investigations'}
            </p>
            <Table
              caption={`Investigations — ${activeDef.label}`}
              columns={columns}
              rows={worklist.data}
              rowKey={(row) => row.investigation_id}
              rowActionHeader="Open"
              rowAction={(row) => (
                <Button
                  variant="ghost"
                  onClick={() => navigate(`/investigations/${row.investigation_id}`)}
                  aria-label={`Open investigation for ${row.company_label}`}
                >
                  Open →
                </Button>
              )}
            />
          </>
        )}
      </section>
    </div>
  );
}
