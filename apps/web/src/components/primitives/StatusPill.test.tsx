import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusPill } from './StatusPill';

describe('StatusPill', () => {
  it('renders its label as text, not colour alone', () => {
    render(<StatusPill label="CONFIRMED" tone="positive" />);
    // The canonical state word is present in the DOM as text.
    expect(screen.getByText('CONFIRMED')).toBeInTheDocument();
  });

  it('exposes an accessible status with the tone described in words', () => {
    render(<StatusPill label="AMBIGUOUS" tone="caution" dimension="Legal entity" />);
    const pill = screen.getByRole('status');
    expect(pill).toHaveAccessibleName('Legal entity: AMBIGUOUS (caution)');
  });

  it('renders a shape glyph so status survives greyscale', () => {
    const { container } = render(<StatusPill label="FAILED" tone="attention" />);
    const glyph = container.querySelector('.status-pill__glyph');
    expect(glyph).not.toBeNull();
    // The triangle marks the "attention" tone independent of colour.
    expect(glyph?.textContent).toBe('▲');
  });
});
