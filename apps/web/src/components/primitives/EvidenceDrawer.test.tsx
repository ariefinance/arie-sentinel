import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EvidenceDrawer } from './EvidenceDrawer';
import { Button } from './Button';

function Harness() {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <Button onClick={() => setOpen(true)}>Open evidence</Button>
      <EvidenceDrawer open={open} onClose={() => setOpen(false)} title="Evidence">
        <p>Placeholder source record.</p>
      </EvidenceDrawer>
    </div>
  );
}

describe('EvidenceDrawer', () => {
  it('is closed until opened, then shows its dialog content', async () => {
    const user = userEvent.setup();
    render(<Harness />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Open evidence' }));

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByText('Placeholder source record.')).toBeInTheDocument();
  });

  it('moves focus to the Close control on open', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: 'Open evidence' }));
    expect(screen.getByRole('button', { name: 'Close evidence' })).toHaveFocus();
  });

  it('closes via the Close button', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: 'Open evidence' }));
    await user.click(screen.getByRole('button', { name: 'Close evidence' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('closes when Escape is pressed (keyboard-dismissible)', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: 'Open evidence' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
