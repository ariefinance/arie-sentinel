import type { BoardRowOut } from '../lib/types';
import { StatusPill } from './primitives/StatusPill';
import { boardTone, humanizeState } from '../lib/status';

/**
 * The Investigation Board: the primary at-a-glance view. Each row states, in
 * explicit evidence language, what Sentinel checked, what it established, and
 * whether analyst attention is needed. A row with backing sources is clickable
 * and opens the evidence drawer. State is text-first (never colour alone) and
 * "Action" is surfaced independently of colour for accessibility.
 */
export function InvestigationBoard({
  rows,
  onOpenSources,
}: {
  rows: BoardRowOut[];
  onOpenSources: (sourceIds: string[], label: string) => void;
}) {
  return (
    <section className="panel" aria-label="Investigation board">
      <h2 className="panel__title">Investigation board</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Check</th>
              <th scope="col">State</th>
              <th scope="col">Finding</th>
              <th scope="col">Attention</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const clickable = row.source_ids.length > 0;
              return (
                <tr key={row.key}>
                  <th scope="row">{row.label}</th>
                  <td>
                    <StatusPill label={humanizeState(row.state)} tone={boardTone(row.state)} />
                  </td>
                  <td>
                    {row.detail}
                    {clickable ? (
                      <>
                        {' '}
                        <button
                          type="button"
                          className="linklike"
                          onClick={() => onOpenSources(row.source_ids, row.label)}
                          aria-label={`View ${row.source_ids.length} source(s) for ${row.label}`}
                        >
                          ({row.source_ids.length} source
                          {row.source_ids.length === 1 ? '' : 's'})
                        </button>
                      </>
                    ) : null}
                  </td>
                  <td>
                    {row.action_required ? (
                      <span className="badge badge--action" role="status">
                        Action required
                      </span>
                    ) : (
                      <span className="cell-muted">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
