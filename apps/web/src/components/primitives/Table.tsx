import type { ReactNode } from 'react';

export interface Column<Row> {
  key: string;
  header: ReactNode;
  /** Cell renderer. */
  render: (row: Row) => ReactNode;
  /** Right-align numeric columns (DESIGN-SYSTEM.md §5). */
  align?: 'start' | 'end';
  /** Mark the column whose cells act as row headers for AT. */
  isRowHeader?: boolean;
}

export interface TableProps<Row> {
  caption: string;
  columns: Column<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  /** Optional per-row action rendered in a trailing cell. */
  rowAction?: (row: Row) => ReactNode;
  rowActionHeader?: string;
}

/**
 * A quiet table: light row separation, no zebra noise, sticky header on scroll,
 * scoped headers. Scrolls horizontally within its own container so the page
 * body never scrolls sideways.
 */
export function Table<Row>({
  caption,
  columns,
  rows,
  rowKey,
  rowAction,
  rowActionHeader = 'Action',
}: TableProps<Row>) {
  return (
    <div className="table-scroll">
      <table className="table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={col.align === 'end' ? 'table__cell--end' : undefined}
              >
                {col.header}
              </th>
            ))}
            {rowAction ? (
              <th scope="col" className="table__cell--end">
                {rowActionHeader}
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((col) => {
                const className = col.align === 'end' ? 'table__cell--end' : undefined;
                if (col.isRowHeader) {
                  return (
                    <th key={col.key} scope="row" className={className}>
                      {col.render(row)}
                    </th>
                  );
                }
                return (
                  <td key={col.key} className={className}>
                    {col.render(row)}
                  </td>
                );
              })}
              {rowAction ? <td className="table__cell--end">{rowAction(row)}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
