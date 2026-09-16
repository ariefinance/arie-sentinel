import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/primitives/Button';
import { TextField } from '../components/primitives/TextField';
import { ErrorState } from '../components/primitives/StateBlocks';
import { useCreateInvestigation } from '../lib/queries';
import { ApiError } from '../lib/api';

const EXAMPLES = [
  { label: 'Try public example — ARIE Finance', company: 'ARIE Finance', contact: '' },
  { label: 'Try ambiguous seller', company: 'Orion Petro Trading', contact: 'Karim Mansour' },
  {
    label: 'Try supported contact',
    company: 'Pacific Energy Procurement Ltd',
    contact: 'Daniel Kim',
  },
  {
    label: 'Try unverified intermediary',
    company: 'Atlas Global Fuels',
    contact: 'Michael Grant',
  },
  {
    label: 'Try potential screening match',
    company: 'Northstar Petroleum Trading',
    contact: 'Victor Lane',
  },
  {
    label: 'Try clean screening',
    company: 'Meridian Energy Supplies Ltd',
    contact: 'Amira Hassan',
  },
] as const;

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
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    if (company.trim() === '') return;

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
          Investigate the company before proceeding with a transaction or relationship. Add a named
          contact when you also need their relationship assessed.
        </p>

        <form className="investigate__form" onSubmit={handleSubmit} noValidate>
          <TextField
            label="Company name"
            hint="as received"
            placeholder="e.g. Orion Petro Trading"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            required
            error={companyError}
            autoComplete="off"
          />
          <TextField
            label="Contact person"
            hint="A company name is enough to start. Add a contact if you also want Sentinel to assess their relationship with the company."
            placeholder="e.g. Karim Mansour"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            autoComplete="off"
          />

          {submitError ? <ErrorState title="Could not start" message={submitError} /> : null}

          <div className="investigate__actions">
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {create.isPending ? 'Starting…' : 'Start Investigation'}
            </Button>
          </div>
        </form>

        <div className="investigate__examples" aria-label="Management demo examples">
          <p className="investigate__examples-label">Management demo examples</p>
          <div className="chips">
            {EXAMPLES.map((example) => (
              <button
                key={example.label}
                type="button"
                className="chip"
                onClick={() => {
                  setCompany(example.company);
                  setContact(example.contact);
                  setTouched(false);
                }}
              >
                {example.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
