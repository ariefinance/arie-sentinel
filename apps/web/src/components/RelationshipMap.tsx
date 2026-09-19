import { useMemo, useState } from 'react';
import type { GraphEdgeOut, GraphNodeOut, RelationshipGraphOut } from '../lib/types';
import { humanizeState } from '../lib/status';

/**
 * Relationship map: a restrained, institutional view of the entities Sentinel
 * connected. Every edge carries its basis and provenance; nothing is invented.
 * A textual relationship list accompanies the diagram so meaning never depends on
 * colour or shape alone (WCAG). Selecting a node or edge shows its provenance.
 */
export function RelationshipMap({
  graph,
  onOpenSources,
}: {
  graph: RelationshipGraphOut;
  onOpenSources?: (ids: string[], label: string) => void;
}) {
  const { nodes, edges } = graph;
  const [selected, setSelected] = useState<{ kind: 'node' | 'edge'; index: number } | null>(null);

  const positions = useMemo(() => layout(nodes), [nodes]);
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const width = 520;
  const height = 360;

  const detail = describeSelection(selected, nodes, edges);

  return (
    <section className="panel" aria-label="Relationship map">
      <h2 className="panel__title">Relationship map</h2>
      {nodes.length <= 1 ? (
        <p>No related entities were established from the retained evidence.</p>
      ) : (
        <>
          <svg
            className="relmap"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Diagram of relationships between the company and connected entities"
          >
            <title>Relationship map</title>
            {edges.map((edge, index) => {
              const a = positions.get(edge.source);
              const b = positions.get(edge.target);
              if (!a || !b) return null;
              return (
                <line
                  key={`e-${index}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  className="relmap__edge"
                  onClick={() => setSelected({ kind: 'edge', index })}
                />
              );
            })}
            {nodes.map((node, index) => {
              const p = positions.get(node.id);
              if (!p) return null;
              return (
                <g
                  key={node.id}
                  transform={`translate(${p.x}, ${p.y})`}
                  className="relmap__node"
                  onClick={() => setSelected({ kind: 'node', index })}
                  tabIndex={0}
                  role="button"
                  aria-label={`${node.type}: ${node.label}`}
                >
                  <rect x={-54} y={-16} rx={4} width={108} height={32} />
                  <text textAnchor="middle" dy={-2} className="relmap__type">
                    {node.type}
                  </text>
                  <text textAnchor="middle" dy={11} className="relmap__label">
                    {truncate(node.label)}
                  </text>
                </g>
              );
            })}
          </svg>

          {detail ? (
            <p className="banner" role="status">
              <strong>{detail.heading}</strong>
              <br />
              {detail.body}
            </p>
          ) : (
            <p className="cell-muted">Select a node or relationship to see its basis and provenance.</p>
          )}

          <ul className="relmap__list" aria-label="Relationships">
            {edges.map((edge, index) => {
              const fromLabel = byId.get(edge.source)?.label ?? edge.source;
              const toLabel = byId.get(edge.target)?.label ?? edge.target;
              const hasSources = edge.source_ids.length > 0;
              return (
                <li key={`l-${index}`}>
                  <strong>{fromLabel}</strong>{' '}
                  <span className="relmap__reltype">{humanizeState(edge.type)}</span>{' '}
                  <strong>{toLabel}</strong>
                  {' — '}
                  <span className="cell-muted">
                    {humanizeState(edge.state)}: {edge.basis}
                  </span>{' '}
                  {hasSources && onOpenSources ? (
                    <button
                      type="button"
                      className="linklike"
                      aria-label={`View ${edge.source_ids.length} source(s) for ${fromLabel} to ${toLabel}`}
                      onClick={() => onOpenSources(edge.source_ids, `${fromLabel} → ${toLabel}`)}
                    >
                      {`(${edge.source_ids.length} source${edge.source_ids.length === 1 ? '' : 's'})`}
                    </button>
                  ) : (
                    <span className="cell-muted">(intake claim — no independent source)</span>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}

interface Point {
  x: number;
  y: number;
}

function layout(nodes: GraphNodeOut[]): Map<string, Point> {
  const positions = new Map<string, Point>();
  const cx = 260;
  const cy = 180;
  const subject = nodes.find((n) => n.id === 'company:subject') ?? nodes[0];
  if (subject) positions.set(subject.id, { x: cx, y: cy });
  const others = nodes.filter((n) => n.id !== subject?.id);
  const radius = 130;
  others.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(others.length, 1) - Math.PI / 2;
    positions.set(node.id, { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) });
  });
  return positions;
}

function truncate(value: string): string {
  return value.length > 16 ? `${value.slice(0, 15)}…` : value;
}

function describeSelection(
  selected: { kind: 'node' | 'edge'; index: number } | null,
  nodes: GraphNodeOut[],
  edges: GraphEdgeOut[],
): { heading: string; body: string } | null {
  if (!selected) return null;
  if (selected.kind === 'node') {
    const node = nodes[selected.index];
    if (!node) return null;
    return { heading: `${node.type}: ${node.label}`, body: node.detail || 'No further detail.' };
  }
  const edge = edges[selected.index];
  if (!edge) return null;
  return {
    heading: `${humanizeState(edge.type)} (${humanizeState(edge.state)})`,
    body: edge.basis,
  };
}
