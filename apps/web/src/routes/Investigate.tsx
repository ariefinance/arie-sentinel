import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/primitives/Button';
import { TextField } from '../components/primitives/TextField';
import { ErrorState } from '../components/primitives/StateBlocks';
import { useCreateInvestigation } from '../lib/queries';
import { ApiError } from '../lib/api';

/**
 * Investigate (UI-UX-SPEC.md §1): capture the two raw management labels and
 * launch. Centred, single column, uncluttered. The single investigation is the
 * dominant action; the bulk-intake affordance stays a subdued secondary link.
 */
export function Investigate() {
  const navigate = useNavigate();
  const create = useCreateInvestigation();

  const [company, setCompany] = useState('');
  const [contact, setContact] = useState('');
  const [touched, setTouched] = useState(false);

  const companyError = touched && company.trim() === '' ? 'Enter the company label.' : undefined;
  const contactError = touched && contact.trim() === '' ? 'Enter the contact person label.' : undefined;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    if (company.trim() === '' || contact.trim() === '') return;

    create.mutate(
      { company_label: company.trim(), contact_label: contact.trim() },
      {
        onSuccess: (data) => {
          navigate(`/investigations/${data.investigation_id}`);
        },
      },
    );
  }

  const submitError =
    create.isError && create.error instanceof ApiError
      ? create.error.message
      : create.isError
        ? 'The investigation could not be created. Please try again.'
        : null;

  return (
    <div className="investigate">
      <div className="investigate__panel">
        <p className="investigate__eyebrow">Counterparty Integrity</p>
        <h1 className="investigate__title">Investigate</h1>
        <p className="investigate__lede">
          Record the counterparty exactly as management holds it. These are raw labels — not
          established identities — and are never overwritten.
        </p>

        <form className="investigate__form" onSubmit={handleSubmit} noValidate>
          <TextField
            label="Company"
            hint="as management recorded it"
            placeholder="e.g. Vantar - Castellan"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            required
            error={companyError}
            autoComplete="off"
          />
          <TextField
            label="Contact person"
            hint="as management recorded it"
            placeholder="e.g. Jordan Rivera"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            required
            error={contactError}
            autoComplete="off"
          />

          {submitError ? <ErrorState title="Could not start" message={submitError} /> : null}

          <div className="investigate__actions">
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? 'Starting…' : 'Investigate'}
            </Button>
          </div>
        </form>

        <div className="investigate__secondary">
          <span className="investigate__secondary-link" aria-disabled="true" title="Not in Stage 1">
            Import list →
          </span>
          <span className="investigate__secondary-note">bulk intake (later stage)</span>
        </div>
      </div>
    </div>
  );
}
