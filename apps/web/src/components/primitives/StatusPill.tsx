/*
 * StatusPill — label-led status indicator.
 *
 * DESIGN-SYSTEM.md §4: "Colour never conveys state alone." The word is the
 * message; the muted colour and the shape glyph are reinforcement only. Each
 * tone uses a DIFFERENT shape so the pill remains distinguishable in greyscale
 * and for colour-blind readers. An optional dimension label (e.g. "Identity")
 * names what the state describes for assistive tech.
 */

export type PillTone = 'positive' | 'attention' | 'caution' | 'info' | 'neutral';

const SHAPE: Record<PillTone, string> = {
  positive: '●', // filled circle
  attention: '▲', // triangle
  caution: '◆', // diamond
  info: '■', // square
  neutral: '○', // open circle
};

const TONE_WORD: Record<PillTone, string> = {
  positive: 'confirmed',
  attention: 'needs attention',
  caution: 'caution',
  info: 'in progress',
  neutral: 'neutral',
};

export interface StatusPillProps {
  /** Canonical state word — the primary message. */
  label: string;
  tone?: PillTone;
  /** Optional dimension this state describes, e.g. "Intake" or "Identity". */
  dimension?: string;
}

export function StatusPill({ label, tone = 'neutral', dimension }: StatusPillProps) {
  const accessibleText = dimension
    ? `${dimension}: ${label} (${TONE_WORD[tone]})`
    : `${label} (${TONE_WORD[tone]})`;

  return (
    <span className={`status-pill status-pill--${tone}`} role="status" aria-label={accessibleText}>
      <span className="status-pill__glyph" aria-hidden="true">
        {SHAPE[tone]}
      </span>
      {dimension ? (
        <span className="status-pill__dimension" aria-hidden="true">
          {dimension}
        </span>
      ) : null}
      <span className="status-pill__label" aria-hidden="true">
        {label}
      </span>
    </span>
  );
}
